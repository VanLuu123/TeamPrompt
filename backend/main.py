from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.document_processor import DocumentProcessor
from core.embedding import Embeddings
from core.vector import PineconeVectorStorage
from pathlib import Path
import uvicorn
import os
import tempfile
import shutil
import requests
import json

from models import(
    QueryResponse,
    QueryRequest,
    UploadResponse,
    ChatResponse,
    ChatRequest,
)

document_processor, vector_store, embeddings = None, None, None

@asynccontextmanager
async def lifespan(app:FastAPI):
    global document_processor, vector_store, embeddings
    print("Initializing RAG Components...")
    document_processor = DocumentProcessor(chunk_size=500, overlap=50)
    embeddings = Embeddings(model_name='all-MiniLM-L6-v2')
    index_name = os.getenv("PINECONE_INDEX_NAME", "rag-documents")
    dimension = embeddings.dimension()
    
    try:
        vector_store = PineconeVectorStorage (
            index_name=index_name,
            dimension=dimension,
            metric="cosine",
        )
        if vector_store.test_connection():  
            print("Ready to go!")
            print(f"Vector Storage Initialized with {dimension} Dimensions.")
        else:
            print("Fix your connection first")
    except Exception as e:
        print(f"Failed to Initialize Vector Storage")
        raise e
    print("Rag System is Ready!")
    yield 
    print("System is Shutting Down")
        
app = FastAPI(
    title="TeamPrompt",
    description="A RAG system for document processing and querying",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message":"TeamPrompt Backend is running",
        "status":"healthy",
        "endpoints": {
            "upload":"/upload-document",
            "query":"/query",
            "chat":"/chat",
            "health":"/health",
        }
    }

@app.get("/health")
async def health_check():
    global vector_store, document_processor, embeddings
    
    status = {
        "document_processor": document_processor is not None,
        "vector_store": vector_store is not None,
        "embeddings": embeddings is not None, 
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY") is not None,
    }
    
    all_healthy = all(status.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "components": status,
        "embedding_dimension": embeddings.dimension() if embeddings else None
    }

@app.post("/upload-document", response_model=UploadResponse)
async def upload_document(file: UploadFile=File(...)):
    allowed_extensions={'.pdf','.html','.docx','.txt','.csv'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}"
        )
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
        
    try:
        chunks = document_processor.process(tmp_path)
        embedded_docs = embeddings.embed_documents(chunks)
        vector_store.upsert_documents(embedded_docs)
        
        return UploadResponse(
            message="Document successfully uploaded and processed",
            file_name=file.filename,
            chunks_created=len(chunks)
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path) 
            
@app.post("/query", response_model=QueryResponse)
async def query_documents(request:QueryRequest):
    try:
        query_embedding = embeddings.embed_query(request.query)
        results = vector_store.query(query_embedding, top_k=request.top_k)
        
        sorted_results = []
        for result in results:
            sorted_results.append({
                "score":float(result.get('score', 0)),
                "content":result.get('metadata',{}).get('content',''),
                "metadata": {
                    "file_name":result.get('metadata',{}).get('file_name',''),
                    "file_type": result.get('metadata',{}).get('file_type',''),
                    "chunk_index":result.get('metadata',{}).get('chunk_index',0),
                    "page_number":result.get('metadata',{}).get('page_number'),
                }
            })
        return QueryResponse(results=sorted_results, query=request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query documents: {str(e)}")
    
@app.post("/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    try:
        # Get OpenRouter API key from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable."
            )
        
        # Create messages for the chat completion
        system_message = """You are a helpful AI assistant that answers questions based on the provided document context. 
        Use the context to provide accurate, detailed answers. If the context doesn't contain enough information to answer the question, 
        say so clearly. Always cite which documents you're referencing when possible."""
        
        user_message = f"""Context from documents:
        {request.context}
        
        User question: {request.query}
        
        Please provide a helpful answer based on the context above."""
        
        # Prepare headers for OpenRouter
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("YOUR_SITE_URL", "http://localhost:8000"),  # Optional
            "X-Title": os.getenv("YOUR_APP_NAME", "TeamPrompt RAG System"),  # Optional
        }
        
        # Prepare the request payload for OpenRouter
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",  # Using free Mistral model
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }
        
        # Make the API call to OpenRouter
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30  # 30 second timeout
        )
        
        if response.status_code != 200:
            error_detail = f"OpenRouter API error: {response.status_code}"
            try:
                error_data = response.json()
                error_detail += f" - {error_data.get('error', {}).get('message', 'Unknown error')}"
            except:
                error_detail += f" - {response.text[:100]}"
            raise HTTPException(status_code=500, detail=error_detail)
            
        response_data = response.json()
        
        # Extract the AI response
        if "choices" in response_data and len(response_data["choices"]) > 0:
            ai_response = response_data["choices"][0]["message"]["content"]
        else:
            raise HTTPException(status_code=500, detail="No response generated from AI model")
        
        return ChatResponse(
            response=ai_response,
            query=request.query,
            sources=[]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=500, detail="Request to AI service timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to AI service: {str(e)}")
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)