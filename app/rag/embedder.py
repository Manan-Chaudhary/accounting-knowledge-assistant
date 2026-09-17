from huggingface_hub import InferenceClient
from app.config import settings


MODEL_NAME = "BAAI/bge-m3"


def get_embedding_client() -> InferenceClient:
    if not settings.HF_TOKEN:
        raise ValueError("HF_TOKEN must be set.")

    return InferenceClient(
        provider="hf-inference",
        api_key=settings.HF_TOKEN,
    )


def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot generate an embedding for empty text.")

    client = get_embedding_client()

    embedding = client.feature_extraction(
        text,
        model=MODEL_NAME,
    )

    return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)