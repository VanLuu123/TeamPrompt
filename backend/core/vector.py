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
        
    def upsert_documents(self, embedded_documents: List[Dict[str,Any]], document_id: str = None):
        """
        Upsert documents with proper content storage and unique IDs
        """
        vectors = []
        
        for i, doc in enumerate(embedded_documents):
            # Create a unique ID for each chunk
            if document_id:
                vector_id = f"{document_id}_chunk_{i}"
            else:
                vector_id = f"{doc['metadata']['file_name']}_chunk_{doc['metadata']['chunk_index']}"
            
            # Ensure content is stored in metadata
            metadata = doc["metadata"].copy()
            metadata["content"] = doc["content"]  # Critical: store content in metadata
            
            # Ensure all metadata values are JSON serializable
            clean_metadata = {}
            for key, value in metadata.items():
                if value is not None:
                    if isinstance(value, (str, int, float, bool)):
                        clean_metadata[key] = value
                    else:
                        clean_metadata[key] = str(value)
            
            vectors.append((
                vector_id,
                doc["embedding"].tolist(),
                clean_metadata
            ))
            
            print(f"Prepared vector {i+1}: ID='{vector_id}', content_length={len(doc['content'])}")
        
        # Upsert in batches to avoid size limits
        batch_size = 100
        total_batches = (len(vectors) - 1) // batch_size + 1
        
        for batch_idx in range(0, len(vectors), batch_size):
            batch = vectors[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            
            try:
                response = self.index.upsert(batch)
                print(f"✅ Upserted batch {batch_num}/{total_batches} ({len(batch)} vectors)")
                print(f"   Response: {response}")
            except Exception as e:
                print(f"❌ Failed to upsert batch {batch_num}: {e}")
                raise
        
        print(f"🎉 Successfully upserted {len(vectors)} vectors total")
        
    def query(self, embedding: np.ndarray, top_k: int = 5):
        """
        Query the vector store and return matches with content
        """
        try:
            results = self.index.query(
                vector=embedding.tolist(),
                top_k=top_k,
                include_metadata=True,
                include_values=False,
            )
            
            matches = results.get('matches', [])
            print(f"Query returned {len(matches)} matches")
            
            # Debug: Check what we got back
            for i, match in enumerate(matches):
                metadata = match.get('metadata', {})
                has_content = 'content' in metadata and bool(metadata['content'])
                print(f"Match {i+1}: score={match.get('score', 0):.4f}, has_content={has_content}")
                if not has_content:
                    print(f"  Metadata keys: {list(metadata.keys())}")
            
            return matches
            
        except Exception as e:
            print(f"Query error: {e}")
            raise
    
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