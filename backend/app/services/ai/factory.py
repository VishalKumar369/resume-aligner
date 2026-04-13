from abc import ABC, abstractmethod
from typing import List, Optional
from openai import AsyncOpenAI
from groq import AsyncGroq
import google.generativeai as genai
from app.core.config import settings

class AIProvider(ABC):
    @abstractmethod
    async def chat_completion(self, messages: List[dict], temperature: float = 0.7) -> str:
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass

class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_completion(self, messages: List[dict], temperature: float = 0.7) -> str:
        response = await self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=[text.replace("\n", " ")],
            model=settings.EMBEDDING_MODEL
        )
        return response.data[0].embedding

class GroqProvider(AIProvider):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def chat_completion(self, messages: List[dict], temperature: float = 0.7) -> str:
        response = await self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

    async def generate_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("Groq does not support embeddings yet.")

class GeminiProvider(AIProvider):
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def chat_completion(self, messages: List[dict], temperature: float = 0.7) -> str:
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [msg["content"]]})
        
        response = await self.model.generate_content_async(contents)
        return response.text

    async def generate_embedding(self, text: str) -> List[float]:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result["embedding"]

class AIFactory:
    @staticmethod
    def get_provider() -> AIProvider:
        provider = settings.AI_PROVIDER.lower()
        if provider == "openai":
            return OpenAIProvider()
        elif provider == "groq":
            return GroqProvider()
        elif provider == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
