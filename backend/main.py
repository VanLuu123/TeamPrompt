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

from models import(
    QueryResponse,
    QueryRequest,
    UploadResponse,
)

document_processor, vector_store, embeddings = None, None, None



@asynccontextmanager
async def lifespan(app:FastAPI):
    global document_processor, vector_store, embeddings
    print("Initializing RAG Components...")
    document_processor = DocumentProcessor(chunk_size=500, overlap=50)
    embeddings = Embeddings(model_name='all-MiniLM-L6-v2')
    index_name = os.getenv("PINECONE_INDEX_NAME", "rag-documents")
    dimension = embeddings.demension()
    
    try:
        vector_store = PineconeVectorStorage (
            index_name=index_name,
            dimension=dimension,
            metric="cosine",
        )
        print(f"Vector Storage Initialized with {dimension} Dimensions.")
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
    }
    
    all_healthy = all(status.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "components": status,
        "embedding_dimension": embeddings.dimension() if embeddings else None
    }

@app.post("/upload-document", response_model=UploadResponse)
async def upload_document(file: UploadFile=File(...)):
    allowed_extensions={'.pdf','.html','docx','.txt','.csv'}
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
        chunks = document_processor(tmp_path)
        embedded_docs = embeddings.embed_documents(chunks)
        vector_store.upsert_documents(embedded_docs)
        
        return UploadResponse(
            message="Document successfully uploaded and processed",
            file_name=file.filename,
            chunks_created=len(chunks)
        )
    finally:
        if os.path.exits(tmp_path):
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)