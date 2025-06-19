import os
import numpy as np
from typing import List, Dict, Any
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()


class VectorStore:
    def __init__(self, index_name: str, dimension: int):
        self.index_name = index_name
        
        # Initialize Pinecone
        pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
        
        # Create index if it doesn't exist
        if index_name not in [idx.name for idx in pc.list_indexes()]:
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
        
        self.index = pc.Index(index_name)

    def upsert(self, embeddings: List[Dict[str, Any]], doc_id: str):
        """Simple upsert with automatic ID generation"""
        vectors = []
        for i, item in enumerate(embeddings):
            vector_id = f"{doc_id}_chunk_{i}"
            metadata = item["metadata"].copy()
            metadata["content"] = item["content"]  # Store content in metadata
            
            vectors.append((
                vector_id,
                item["embedding"].tolist(),
                metadata
            ))
        
        # Batch upsert
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(batch)

    def query(self, embedding: np.ndarray, top_k: int = 5):
        """Simple query returning matches"""
        results = self.index.query(
            vector=embedding.tolist(),
            top_k=top_k,
            include_metadata=True
        )
        return results.matches