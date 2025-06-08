from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any

class Embeddings:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    # converts documents into embedding
    def embed_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        texts = [doc["content"] for doc in documents]
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True, 
            normalize_embeddings=True,
        )
        results = []
        for i, doc in enumerate(documents):
            results.append({
                "embedding": embeddings[i],
                "content": doc["content"],
                "metadata": doc["metadata"]
            })

        return results
    
    # converts user query to embedding
    def embed_query(self, query: str) -> np.ndarray:
        embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embedding
    
    # converts texts without metadata to embeddings
    def embed_text(self, texts: List[str]) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings
    
    # returns embedding dimension
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
    



