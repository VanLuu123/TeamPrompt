from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.document_processor import DocumentProcessor
from core.embedding import Embeddings
from core.vector import PineconeVectorStorage
import uvicorn
import os

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
    return {"message":"TeamPrompt Backend is running"}

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



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)