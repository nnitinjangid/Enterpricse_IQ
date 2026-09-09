import re

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk

from rank_bm25 import BM25Okapi


# =========================================================
# Tokenizer
# =========================================================

def tokenize_text(text: str) -> list[str]:
    """
    Convert text into lowercase tokens.

    Example:

    "GST Rate is 18%"
    
    becomes approximately:

    ["gst", "rate", "is", "18"]
    """

    if not text:
        return []

    tokens = re.findall(
        r"\b\w+\b",
        text.lower(),
    )

    return tokens


# =========================================================
# Keyword Search using BM25
# =========================================================

def keyword_search(
    query: str,
    db: Session,
    user_id: int,
    top_k: int = 5,
) -> list[dict]:
    """
    Perform BM25 keyword search over the chunks
    belonging to the current user's documents.
    """

    if not query or not query.strip():
        raise ValueError(
            "Search query cannot be empty."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    # =====================================================
    # Get only current user's document chunks
    # =====================================================

    chunks = (
        db.query(DocumentChunk)
        .join(
            Document,
            DocumentChunk.document_id == Document.id,
        )
        .filter(
            Document.uploaded_by == user_id
        )
        .order_by(
            DocumentChunk.document_id.asc(),
            DocumentChunk.chunk_index.asc(),
        )
        .all()
    )

    if not chunks:
        return []

    # =====================================================
    # Prepare Corpus
    # =====================================================

    corpus = [
        tokenize_text(chunk.content)
        for chunk in chunks
    ]

    # Remove empty documents
    valid_items = []

    for index, tokens in enumerate(corpus):

        if tokens:
            valid_items.append(
                (
                    index,
                    tokens,
                )
            )

    if not valid_items:
        return []

    valid_indices = [
        item[0]
        for item in valid_items
    ]

    tokenized_corpus = [
        item[1]
        for item in valid_items
    ]

    # =====================================================
    # Create BM25 Index
    # =====================================================

    bm25 = BM25Okapi(
        tokenized_corpus
    )

    # =====================================================
    # Tokenize Query
    # =====================================================

    query_tokens = tokenize_text(
        query
    )

    if not query_tokens:
        return []

    # =====================================================
    # Calculate BM25 Scores
    # =====================================================

    scores = bm25.get_scores(
        query_tokens
    )

    # =====================================================
    # Sort by BM25 Score
    # =====================================================

    ranked_results = sorted(
        zip(
            valid_indices,
            scores,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    # =====================================================
    # Build Results
    # =====================================================

    results = []

    for original_index, score in ranked_results:

        # Ignore completely irrelevant chunks
        if score <= 0:
            continue

        chunk = chunks[
            original_index
        ]

        document = chunk.document

        results.append(
            {
                "score": float(score),
                "document_id": chunk.document_id,
                "filename": document.original_filename,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "retrieval_method": "bm25",
            }
        )

        if len(results) >= top_k:
            break

    return results