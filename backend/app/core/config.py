import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Resume-JD-Aligner"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-super-secret-key-change-it-in-prod"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # Environment
    ENVIRONMENT: str = "development" # development, staging, production

    # Comma-separated emails allowed to read the feedback inbox (admins).
    ADMIN_EMAILS: str = ""

    @property
    def admin_email_set(self) -> set:
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

    # --- Email verification (OTP at signup) ---------------------------------
    # The single switch: when False, signup/login behave as before. Keep the
    # frontend flag NEXT_PUBLIC_EMAIL_VERIFICATION_ENABLED in step with this.
    EMAIL_VERIFICATION_ENABLED: bool = False
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    # SMTP to actually send the code. Leave SMTP_HOST empty to instead log the
    # code to the server console (development — no email account needed).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True

    # PostgreSQL
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "resume_jd_aligner"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> any:
        if isinstance(v, str):
            return v
        return f"postgresql+asyncpg://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

    # Redis (Caching & Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS: bool = False # Fallback to in-memory if False
    
    # AI Engine
    # Defaults to a free-tier provider; parsing falls back to the deterministic
    # heuristic extractor whenever no key is configured.
    AI_PROVIDER: str = "gemini" # openai, groq, gemini

    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    LLM_MODEL: str = "gpt-4o-mini"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Which features may spend a model call.
    #
    # Free tiers are metered per day (Gemini reports a limit of 20/day for this
    # project), so the budget goes where rules genuinely cannot compete. The
    # heuristic extractors already parse this project's resumes at confidence
    # 1.0 with correct companies and dates; rewriting prose is the one thing
    # they cannot do at all.
    LLM_FOR_RESUME_EXTRACTION: bool = False
    LLM_FOR_JD_EXTRACTION: bool = False
    LLM_FOR_ALIGNMENT: bool = False
    LLM_FOR_BULLET_REWRITING: bool = True

    # After a quota rejection, stop attempting calls for this long rather than
    # burning latency on requests that are certain to fail.
    LLM_QUOTA_COOLDOWN_SECONDS: int = 900

    def llm_enabled_for(self, feature: str) -> bool:
        """Whether `feature` may use a model, given the per-feature switches."""
        return bool(getattr(self, f"LLM_FOR_{feature.upper()}", False))

    @property
    def ai_api_key(self) -> Optional[str]:
        return {
            "openai": self.OPENAI_API_KEY,
            "groq": self.GROQ_API_KEY,
            "gemini": self.GEMINI_API_KEY,
        }.get(self.AI_PROVIDER.lower())

    @property
    def has_ai_credentials(self) -> bool:
        """Whether the selected provider has a usable key.

        Placeholder values such as "sk-..." are treated as missing so the app
        degrades to heuristic parsing instead of failing on an auth error.
        """
        key = (self.ai_api_key or "").strip()
        return len(key) > 12 and not key.endswith("...")


    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DIMENSION: int = 1536
    
    # Storage
    STORAGE_TYPE: str = "local" # local, cloudinary, firebase
    UPLOAD_DIR: str = "uploads"
    
    # Cloudinary (Optional)
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    
    # Firebase (Optional)
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_STORAGE_BUCKET: Optional[str] = None

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
