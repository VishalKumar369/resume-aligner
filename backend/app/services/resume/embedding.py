from typing import List
import numpy as np
from app.services.ai.factory import AIFactory

class EmbeddingPipeline:
    def __init__(self):
        self.provider = AIFactory.get_provider()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generates embedding using the configured provider.
        """
        return await self.provider.generate_embedding(text)

    @staticmethod
    def normalize_vector(vector: List[float]) -> List[float]:
        arr = np.array(vector)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return vector
        return (arr / norm).tolist()
