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
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")
            
        pc = Pinecone(api_key=api_key)
        
        # Create index if it doesn't exist
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing_indexes:
            try:
                pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
            except Exception as e:
                print(f"Warning: Could not create index {index_name}: {e}")
        
        self.index = pc.Index(index_name)

    def upsert(self, embeddings: List[Dict[str, Any]], doc_id: str):
        """Simple upsert with automatic ID generation"""
        if not embeddings:
            return
            
        vectors = []
        for i, item in enumerate(embeddings):
            vector_id = f"{doc_id}_chunk_{i}"
            metadata = item["metadata"].copy()
            
            # Limit metadata size (Pinecone has limits)
            content = item["content"]
            if len(content) > 40000:  # Pinecone metadata limit
                content = content[:40000] + "..."
            metadata["content"] = content
            
            # Convert numpy array to list for Pinecone
            embedding = item["embedding"]
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            vectors.append((vector_id, embedding, metadata))
        
        # Batch upsert
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            try:
                self.index.upsert(batch)
            except Exception as e:
                print(f"Error upserting batch {i//batch_size + 1}: {e}")
                # Continue with other batches

    def query(self, embedding: np.ndarray, top_k: int = 5):
        """Simple query returning matches"""
        try:
            # Convert numpy array to list for Pinecone
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
                
            results = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True
            )
            return results.matches
        except Exception as e:
            print(f"Error querying vector store: {e}")
            return []
