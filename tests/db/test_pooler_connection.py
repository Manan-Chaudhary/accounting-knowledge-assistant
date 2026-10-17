import os
from sqlalchemy import create_engine, text


def test_pooler_connection():
    """Verify that the database connection via the Supabase pooler succeeds."""
    pooler_url = os.getenv(
        "SUPABASE_POOLER_URL", "")
    assert pooler_url, "Pooler URL is not specified"

    engine = create_engine(pooler_url, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1, f"Expected 1, got {result}"

