from typing import List
import numpy as np
from openai import AsyncOpenAI
from app.core.config import settings

class EmbeddingPipeline:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generates OpenAI embedding for the given text.
        """
        response = await self.client.embeddings.create(
            input=[text.replace("\n", " ")],
            model=self.model
        )
        return response.data[0].embedding

    @staticmethod
    def normalize_vector(vector: List[float]) -> List[float]:
        """
        Normalizes vector for cosine similarity (though OpenAI vectors are already normalized).
        """
        arr = np.array(vector)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return vector
        return (arr / norm).tolist()
