from sentence_transformers import SentenceTransformer
import numpy as np

class Embeddings:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, documents: list[str]):
        texts = [doc["content"] for doc in documents]
        embeddings = self.model.encode(texts,convert_to_numpy=True, normalize_embeddings=True)
        results = []
        for i, doc in enumerate(documents):
            results.append({
                "embedding": embeddings[i],
                "content": doc["content"],
                "metadata": doc["metadata"]
            })

        return results



