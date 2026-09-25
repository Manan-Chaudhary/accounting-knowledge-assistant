from app.config import settings


def test_environment_configuration():
    "Verify that required environment variables are loaded."

    # Validate LLM credentials (either LiteLLM proxy config or direct provider keys)
    has_llm_config = bool(
        (settings.LITELLM_API_BASE and settings.LITELLM_API_KEY)
        or settings.LITELLM_API_KEY
        or settings.GROQ_API_KEY
        or settings.GEMINI_API_KEY
        or settings.OPENAI_API_KEY
    )
    assert has_llm_config, (
        "LLM configuration missing: provide LITELLM_API_BASE/LITELLM_API_KEY or direct provider keys (GROQ_API_KEY / GEMINI_API_KEY)"
    )

    assert settings.HF_TOKEN, "HF_TOKEN is missing"
    assert settings.SUPABASE_DB_URL, "SUPABASE_DB_URL is missing"
    assert settings.LITELLM_MODEL, "LITELLM_MODEL is missing"

    print("✓ Environment configuration loaded successfully")