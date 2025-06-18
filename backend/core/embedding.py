from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any

class Embeddings:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Embeds a list of document chunks.
        Each input dict must contain 'content' and 'metadata'.
        """
        texts = [doc["content"] for doc in documents]
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return [
            {
                "embedding": embeddings[i],
                "content": documents[i]["content"],
                "metadata": documents[i]["metadata"]
            }
            for i in range(len(documents))
        ]

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embeds a single user query string into a vector.
        """
        return self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    def embed_text(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a list of plain text strings.
        """
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    def dimension(self) -> int:
        """
        Returns the embedding dimensionality of the current model.
        """
        return self.model.get_sentence_embedding_dimension()
