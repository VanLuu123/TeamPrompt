import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Literal
from document_processor import DocumentProcessor
from embeddings import Embeddings
from pinecone_vector_store import PineconeVectorStore
from pinecone import Pinecone
from dotenv import load_dotenv

API_KEY = load_dotenv('PINECONE_API_KEY')

Pinecone.init(
    api_key=API_KEY,
    environment='gcp-starter'
)

class PineconeVectorStorage:
    def __init__(self, index_name:str, dimension: int, metric: str = "cosine"):
        self.index_name = index_name
        self.dimension = dimension 
        self.metric = metric
        
        if index_name not in metric:
            pinecone.create_index(index_name, dimension=dimension, metric=metric)
        self.index = pinecone.Index(index_name)
        
    def upsert_documents(self, embedded_documents: List[Dict[str,Any]]):
        vectors = [
            (
                f"{doc['metadata']['file_name']}-{doc['metadata']['chunk_index']}",
                doc["embedding"].tolist(),
                doc["metadata"]
            )
            for doc in embedded_documents
        ]   
        self.index.upsert(vectors)
        
    def query(self, embedding: np.ndarray, top_k: int = 5):
        result = self.index.query (
            vector = embedding.tolist(),
            top_k = top_k,
            include_metadata = True,
        )
        return result['matches']



