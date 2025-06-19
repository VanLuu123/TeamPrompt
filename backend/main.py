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
import hashlib
import time

from models import(
    QueryResponse,
    QueryRequest,
    UploadResponse,
    ChatResponse,
    ChatRequest,
)

document_processor, vector_store, embeddings = None, None, None

def generate_document_id(filename: str, content: str) -> str:
    """Generate a unique ID for a document based on filename and content hash"""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    clean_filename = Path(filename).stem  # Remove extension and temp prefixes
    timestamp = int(time.time())
    return f"{clean_filename}_{content_hash}_{timestamp}"

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
        print(f"Failed to Initialize Vector Storage: {e}")
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
    
    # Use original filename instead of temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
        
    try:
        print(f"Processing file: {file.filename}")
        
        # Extract text first to generate document ID
        text = document_processor.extract_text(tmp_path)
        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Document appears to be empty or unreadable")
        
        print(f"Extracted text length: {len(text)} characters")
        print(f"Text preview: {text[:200]}...")
        
        # Generate unique document ID
        doc_id = generate_document_id(file.filename, text)
        print(f"Generated document ID: {doc_id}")
        
        # Split text into chunks
        chunks = document_processor.split_text(text, file.filename, file_extension)
        print(f"Created {len(chunks)} chunks")
        
        # Debug: Show all chunks
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i}: {len(chunk['content'])} chars - {chunk['content'][:100]}...")
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks were created from the document")
        
        # Update chunk metadata with document ID
        for chunk in chunks:
            chunk['metadata']['document_id'] = doc_id
            chunk['metadata']['original_filename'] = file.filename
        
        # Generate embeddings
        embedded_docs = embeddings.embed_documents(chunks)
        print(f"Generated embeddings for {len(embedded_docs)} chunks")
        
        # Store in vector database
        vector_store.upsert_documents(embedded_docs, doc_id)
        print(f"Successfully uploaded {len(chunks)} chunks to vector store")
        
        return UploadResponse(
            message=f"Document '{file.filename}' successfully uploaded and processed",
            file_name=file.filename,
            chunks_created=len(chunks)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path) 
            
@app.post("/query", response_model=QueryResponse)
async def query_documents(request:QueryRequest):
    try:
        print(f"\n=== QUERY DEBUG ===")
        print(f"Query: '{request.query}'")
        print(f"Requested top_k: {request.top_k}")
        
        # Generate query embedding
        query_embedding = embeddings.embed_query(request.query)
        print(f"Query embedding shape: {query_embedding.shape}")
        
        # Search vector store
        results = vector_store.query(query_embedding, top_k=request.top_k)
        print(f"Raw results count: {len(results)}")
        
        # Process results
        sorted_results = []
        for i, result in enumerate(results):
            score = float(result.get('score', 0))
            metadata = result.get('metadata', {})
            content = metadata.get('content', '')
            
            print(f"\n--- Result {i+1} ---")
            print(f"ID: {result.get('id', 'N/A')}")
            print(f"Score: {score:.4f}")
            print(f"Metadata keys: {list(metadata.keys())}")
            print(f"Content length: {len(content)}")
            print(f"Has content: {'YES' if content else 'NO'}")
            
            if content:
                print(f"Content preview: '{content[:150]}...'")
            else:
                print("WARNING: No content found!")
            
            # Only include results with content and reasonable similarity
            if content and score > 0.1:  # Lower threshold for debugging
                sorted_results.append({
                    "score": score,
                    "content": content,
                    "metadata": {
                        "file_name": metadata.get('original_filename', metadata.get('file_name', '')),
                        "file_type": metadata.get('file_type', ''),
                        "chunk_index": metadata.get('chunk_index', 0),
                        "page_number": metadata.get('page_number'),
                        "document_id": metadata.get('document_id', ''),
                    }
                })
        
        print(f"\nFiltered results: {len(sorted_results)}")
        return QueryResponse(results=sorted_results, query=request.query)
        
    except Exception as e:
        print(f"Query error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to query documents: {str(e)}")

# Add endpoint to clear duplicates
@app.delete("/clear-index")
async def clear_index():
    """Clear all vectors from the index - use carefully!"""
    try:
        vector_store.index.delete(delete_all=True)
        return {"message": "Index cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear index: {str(e)}")

# Add endpoint to check index stats
@app.get("/index-stats")
async def get_index_stats():
    """Get statistics about the current index"""
    try:
        stats = vector_store.index.describe_index_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

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
        
        print(f"Chat request - Query: {request.query}")
        print(f"Context length: {len(request.context)}")
        
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
            "HTTP-Referer": os.getenv("YOUR_SITE_URL", "http://localhost:8000"),
            "X-Title": os.getenv("YOUR_APP_NAME", "TeamPrompt RAG System"),
        }
        
        # Prepare the request payload for OpenRouter
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
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
            timeout=30
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