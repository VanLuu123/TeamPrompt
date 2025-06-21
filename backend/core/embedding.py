import openai
import os
from typing import List, Dict, Any
import numpy as np


class Embeddings:
    def __init__(self):
        # Use OpenRouter as the base URL for OpenAI client
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = "text-embedding-3-small"
        self._dimension = 1536

    def embed_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Embed document chunks using OpenAI embeddings"""
        texts = [doc["content"] for doc in documents]
        
        # Handle empty texts
        if not texts:
            return []
        
        try:
            # Create embeddings in batches to avoid rate limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
            
            # Return documents with embeddings
            return [
                {
                    "embedding": np.array(all_embeddings[i]),
                    "content": documents[i]["content"],
                    "metadata": documents[i]["metadata"]
                }
                for i in range(len(documents))
            ]
            
        except Exception as e:
            raise Exception(f"Error creating embeddings: {str(e)}")

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a query string"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=query
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            raise Exception(f"Error embedding query: {str(e)}")

    def dimension(self) -> int:
        """Get embedding dimension"""
        return self._dimension
