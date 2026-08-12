import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai
from groq import AsyncGroq
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


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


# Substrings that identify a quota rejection across providers.
_QUOTA_MARKERS = ("resourceexhausted", "429", "quota", "rate limit", "too many requests")


class AIFactory:
    # Set when a provider reports quota exhaustion. Until it passes, calls are
    # skipped rather than retried: free tiers meter per day, so a rejection now
    # means the next request fails too.
    _cooldown_until: float = 0.0
    _last_reason: Optional[str] = None

    @staticmethod
    def is_available(feature: Optional[str] = None) -> bool:
        """Whether a model call can be made right now.

        `feature` additionally checks that feature's switch, so the daily budget
        is only spent where it was allocated.
        """
        if not settings.has_ai_credentials:
            return False
        if feature is not None and not settings.llm_enabled_for(feature):
            return False
        return not AIFactory.in_cooldown()

    @staticmethod
    def in_cooldown() -> bool:
        return time.monotonic() < AIFactory._cooldown_until

    @staticmethod
    def note_failure(exc: BaseException) -> bool:
        """Record a failed call. Returns True if it was a quota rejection.

        A quota rejection starts a cooldown so the rest of the session degrades
        to deterministic behaviour immediately instead of retrying.
        """
        text = f"{type(exc).__name__} {exc}".lower()
        if not any(marker in text for marker in _QUOTA_MARKERS):
            return False

        AIFactory._cooldown_until = time.monotonic() + settings.LLM_QUOTA_COOLDOWN_SECONDS
        AIFactory._last_reason = (
            "The daily quota for this model has been reached, so AI features are "
            "using their deterministic fallback."
        )
        logger.warning("AI provider quota exhausted; cooling down: %s", str(exc)[:200])
        return True

    @staticmethod
    def unavailable_reason(feature: Optional[str] = None) -> Optional[str]:
        """A user-facing explanation of why a model was not used, if it was not."""
        if not settings.has_ai_credentials:
            return "No AI provider key is configured, so deterministic parsing was used."
        if AIFactory.in_cooldown():
            return AIFactory._last_reason
        if feature is not None and not settings.llm_enabled_for(feature):
            return (
                f"AI is disabled for {feature.replace('_', ' ')} "
                f"(LLM_FOR_{feature.upper()}=false)."
            )
        return None

    @staticmethod
    def reset_quota_state() -> None:
        """Clear the cooldown. Used by tests and after a key change."""
        AIFactory._cooldown_until = 0.0
        AIFactory._last_reason = None

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
