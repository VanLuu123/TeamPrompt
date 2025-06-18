import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Literal
from .document_processor import DocumentProcessor
from .embedding import Embeddings
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

class PineconeVectorStorage:
    def __init__(self, index_name:str, dimension: int, metric: str = "cosine"):
        self.index_name = index_name
        self.dimension = dimension 
        self.metric = metric
        
        api_key = os.environ.get('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE API KEY is required")
        
        self.pc = Pinecone(api_key=api_key)
        
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if index_name not in existing_indexes:
            print(f"Creating new index: {index_name}")
            self.pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud='aws',  
                    region='us-east-1'  
                )
            )
        
        self.index = self.pc.Index(index_name)
        
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
        results = self.index.query (
            vector = embedding.tolist(),
            top_k = top_k,
            include_metadata = True,
            include_values = False,
        )
        return results['matches']
    
    def test_connection(self):
        """Test if Pinecone connection is working"""
        try:
            indexes = self.pc.list_indexes()
            print(f"✅ Connected to Pinecone! Available indexes: {[idx.name for idx in indexes]}")
            
            stats = self.index.describe_index_stats()
            print(f"✅ Index '{self.index_name}' stats: {stats}")
            
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False



