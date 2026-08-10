from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai
from groq import AsyncGroq
from openai import AsyncOpenAI

from app.core.config import settings


class AIProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        """Complete a chat exchange.

        `json_mode` asks the provider to constrain output to a JSON object.
        Callers still parse defensively, but it removes most prose-wrapping.
        """

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_completion(
        self, messages: List[dict], temperature: float = 0.7, json_mode: bool = False
    ) -> str:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        response = await self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=[text.replace("\n", " ")],
            model=settings.EMBEDDING_MODEL
        )
        return response.data[0].embedding


class GroqProvider(AIProvider):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def chat_completion(
        self, messages: List[dict], temperature: float = 0.7, json_mode: bool = False
    ) -> str:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        response = await self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def generate_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("Groq does not support embeddings yet.")


class GeminiProvider(AIProvider):
    """Gemini adapter.

    Gemini differs from the OpenAI-shaped APIs in two ways that matter: system
    prompts go in a dedicated `system_instruction` rather than the message list,
    and the assistant role is called "model". Sending a system message as a
    conversational turn makes the model treat its own instructions as something
    it already said.
    """

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL

    async def chat_completion(
        self, messages: List[dict], temperature: float = 0.7, json_mode: bool = False
    ) -> str:
        system_instruction, contents = self._split_messages(messages)

        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=system_instruction or None,
        )

        config: Dict[str, object] = {"temperature": temperature}
        if json_mode:
            config["response_mime_type"] = "application/json"

        response = await model.generate_content_async(
            contents,
            generation_config=genai.types.GenerationConfig(**config),
        )
        return self._read_text(response)

    def _split_messages(self, messages: List[dict]) -> Tuple[str, List[dict]]:
        """Separate system prompts from the conversation."""
        system_parts: List[str] = []
        contents: List[dict] = []

        for message in messages:
            role = (message.get("role") or "user").lower()
            content = message.get("content") or ""
            if not content:
                continue

            if role == "system":
                system_parts.append(content)
                continue

            contents.append({
                "role": "model" if role in ("assistant", "model") else "user",
                "parts": [content],
            })

        return "\n\n".join(system_parts), contents

    def _read_text(self, response) -> str:
        """Read the response text without raising on a blocked completion."""
        try:
            return response.text or ""
        except Exception:  # noqa: BLE001 - safety blocks and empty candidates
            for candidate in getattr(response, "candidates", None) or []:
                parts = getattr(getattr(candidate, "content", None), "parts", None) or []
                text = "".join(getattr(part, "text", "") or "" for part in parts)
                if text:
                    return text
            return ""

    async def generate_embedding(self, text: str) -> List[float]:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result["embedding"]


class AIUnavailableError(RuntimeError):
    """Raised when an LLM is requested but no usable API key is configured."""


class AIFactory:
    @staticmethod
    def is_available() -> bool:
        """Whether an LLM call can be made right now.

        Callers use this to choose the LLM path or fall back to deterministic
        parsing, instead of discovering the missing key as an auth failure.
        """
        return settings.has_ai_credentials

    @staticmethod
    def get_provider() -> AIProvider:
        provider = settings.AI_PROVIDER.lower()

        if not settings.has_ai_credentials:
            raise AIUnavailableError(
                f"No API key configured for AI_PROVIDER='{provider}'. "
                f"Set {provider.upper()}_API_KEY in backend/.env, or leave it blank "
                "to use the heuristic parser."
            )

        if provider == "openai":
            return OpenAIProvider()
        elif provider == "groq":
            return GroqProvider()
        elif provider == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
