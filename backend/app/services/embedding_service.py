from sentence_transformers import SentenceTransformer

from app.core.config import settings


# =========================================================
# Load Embedding Model
# =========================================================

_model = None


def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model lazily.

    The model is loaded only when embeddings
    are actually required.
    """

    global _model

    if _model is None:

        print(
            f"Loading embedding model: "
            f"{settings.EMBEDDING_MODEL}"
        )

        _model = SentenceTransformer(
            settings.EMBEDDING_MODEL
        )

        print(
            "Embedding model loaded."
        )

    return _model


# =========================================================
# Generate Single Embedding
# =========================================================

def generate_embedding(
    text: str,
) -> list[float]:
    """
    Generate embedding for a single text.
    """

    if not text or not text.strip():
        raise ValueError(
            "Text cannot be empty."
        )

    model = get_embedding_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()


# =========================================================
# Generate Multiple Embeddings
# =========================================================

def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """
    Generate embeddings for multiple texts.
    """

    if not texts:
        return []

    cleaned_texts = [
        text.strip()
        for text in texts
        if text and text.strip()
    ]

    if not cleaned_texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        cleaned_texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return embeddings.tolist()