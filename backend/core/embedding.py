from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any


class Embeddings:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Embed document chunks"""
        texts = [doc["content"] for doc in documents]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        
        return [
            {
                "embedding": embeddings[i],
                "content": documents[i]["content"],
                "metadata": documents[i]["metadata"]
            }
            for i in range(len(documents))
        ]

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a query string"""
        return self.model.encode(query, normalize_embeddings=True)

    def dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()
