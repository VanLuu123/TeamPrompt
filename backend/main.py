from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import tempfile
import shutil
import hashlib
import time
import os
import requests
from pathlib import Path

# Import your simplified components
from core.document_processor import DocumentProcessor
from core.embedding import Embeddings
from core.vector import VectorStore

# Simple models
from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class QueryResponse(BaseModel):
    results: List[dict]
    query: str

class ChatRequest(BaseModel):
    query: str
    context: str

class ChatResponse(BaseModel):
    response: str

# Global components
processor = None
embeddings = None
vector_store = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global processor, embeddings, vector_store
    
    print("🚀 Initializing RAG system...")
    
    # Initialize components
    processor = DocumentProcessor(chunk_size=800, overlap=100)
    embeddings = Embeddings()
    vector_store = VectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME", "rag-simple"),
        dimension=embeddings.dimension()
    )
    
    print("✅ RAG system ready!")
    yield
    print("🛑 Shutting down...")

app = FastAPI(title="Simple RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_doc_id(filename: str, content: str) -> str:
    """Generate unique document ID"""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    timestamp = int(time.time())
    clean_name = Path(filename).stem
    return f"{clean_name}_{content_hash}_{timestamp}"

@app.get("/")
async def root():
    return {"message": "Simple RAG API is running", "status": "ready"}

@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    # Check file type
    allowed_types = {'.pdf', '.docx', '.txt', '.csv', '.html'}
    if Path(file.filename).suffix.lower() not in allowed_types:
        raise HTTPException(400, "Unsupported file type")
    
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        # Extract text
        text = processor.extract_text(tmp_path)
        if len(text.strip()) < 10:
            raise HTTPException(400, "Document is empty or unreadable")
        
        # Generate document ID
        doc_id = generate_doc_id(file.filename, text)
        
        # Split into chunks
        chunks = processor.split_text(text, file.filename)
        if not chunks:
            raise HTTPException(400, "No chunks created from document")
        
        # Generate embeddings
        embedded_chunks = embeddings.embed_documents(chunks)
        
        # Store in vector database
        vector_store.upsert(embedded_chunks, doc_id)
        
        return {
            "message": f"Successfully uploaded {file.filename}",
            "doc_id": doc_id,
            "chunks": len(chunks)
        }
        
    finally:
        os.unlink(tmp_path)

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    # Generate query embedding
    query_embedding = embeddings.embed_query(request.query)
    
    # Search vector store
    matches = vector_store.query(query_embedding, request.top_k)
    
    # Format results
    results = []
    for match in matches:
        if match.score > 0.2:  # Simple relevance threshold
            results.append({
                "content": match.metadata.get("content", ""),
                "filename": match.metadata.get("filename", ""),
                "score": float(match.score)
            })
    
    return QueryResponse(results=results, query=request.query)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(500, "OpenRouter API key not configured")
    
    # Simple chat completion
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {
                "role": "system", 
                "content": "Answer questions based on the provided context. Be concise and accurate."
            },
            {
                "role": "user", 
                "content": f"Context: {request.context}\n\nQuestion: {request.query}"
            }
        ],
        "max_tokens": 500,
        "temperature": 0.3
    }
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    if response.status_code != 200:
        raise HTTPException(500, "Failed to get AI response")
    
    ai_response = response.json()["choices"][0]["message"]["content"]
    return ChatResponse(response=ai_response)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "processor": processor is not None,
            "embeddings": embeddings is not None,
            "vector_store": vector_store is not None
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
