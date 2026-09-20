import os
from dotenv import load_dotenv

load_dotenv()


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # LLM 1: Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # LLM 2: Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # supabase setting
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "documents")

    # FastAPI-owned session (signed cookie). Required for /api/auth/*.
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "")
    SESSION_MAX_AGE_SECONDS: int = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(8 * 60 * 60)))
    CORS_ORIGINS: list[str] = _csv_env("CORS_ORIGINS", "http://localhost:5173")
    # Required before Chainlit is private (AU-86). Not used by React login itself.
    CHAINLIT_AUTH_SECRET: str = os.getenv("CHAINLIT_AUTH_SECRET", "")


settings = Settings()
