import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk

from rank_bm25 import BM25Okapi


def tokenize_text(
    text: str,
) -> list[str]:

    if not text:
        return []

    tokens = re.findall(
        r"\b\w+\b",
        text.lower(),
    )

    return tokens


def keyword_search(
    query: str,
    db: Session,
    user_id: int,
    user_role: str,
    top_k: int = 5,
) -> list[dict]:

    if not query or not query.strip():

        raise ValueError(
            "Search query cannot be empty."
        )

    if top_k <= 0:

        raise ValueError(
            "top_k must be greater than 0."
        )

    if not user_role:

        raise ValueError(
            "user_role is required for "
            "document authorization."
        )

    # -----------------------------------------
    # DOCUMENT ACCESS FILTER
    # -----------------------------------------
    #
    # ADMIN:
    #   → All documents
    #
    # NORMAL USER:
    #   1. Own documents
    #   2. Company documents
    #   3. Documents shared with their role
    #
    # -----------------------------------------

    if user_role == "admin":

        chunks = (
            db.query(DocumentChunk)
            .join(
                Document,
                DocumentChunk.document_id
                == Document.id,
            )
            .order_by(
                DocumentChunk.document_id.asc(),
                DocumentChunk.chunk_index.asc(),
            )
            .all()
        )

        print(
            f"BM25 authorization: "
            f"admin user {user_id} → all documents"
        )

    else:

        access_condition = or_(
            # ---------------------------------
            # Own documents
            # ---------------------------------

            Document.uploaded_by == user_id,

            # ---------------------------------
            # Company-wide documents
            # ---------------------------------

            Document.access_scope == "company",

            # ---------------------------------
            # Role-based documents
            # ---------------------------------

            (
                (Document.access_scope == "role")
                &
                (Document.access_role == user_role)
            ),
        )

        chunks = (
            db.query(DocumentChunk)
            .join(
                Document,
                DocumentChunk.document_id
                == Document.id,
            )
            .filter(
                access_condition
            )
            .order_by(
                DocumentChunk.document_id.asc(),
                DocumentChunk.chunk_index.asc(),
            )
            .all()
        )

        print(
            f"BM25 authorization: "
            f"user {user_id}, "
            f"role={user_role} → filtered documents"
        )

    # -----------------------------------------
    # NO DOCUMENTS
    # -----------------------------------------

    if not chunks:

        return []

    # -----------------------------------------
    # TOKENIZE CORPUS
    # -----------------------------------------

    corpus = [
        tokenize_text(
            chunk.content
        )
        for chunk in chunks
    ]

    valid_items = []

    for index, tokens in enumerate(
        corpus
    ):

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

    # -----------------------------------------
    # BM25
    # -----------------------------------------

    bm25 = BM25Okapi(
        tokenized_corpus
    )

    query_tokens = tokenize_text(
        query
    )

    if not query_tokens:

        return []

    scores = bm25.get_scores(
        query_tokens
    )

    # -----------------------------------------
    # RANK RESULTS
    # -----------------------------------------

    ranked_results = sorted(
        zip(
            valid_indices,
            scores,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    results = []

    # -----------------------------------------
    # BUILD RESULTS
    # -----------------------------------------

    for original_index, score in ranked_results:

        if score <= 0:

            continue

        chunk = chunks[
            original_index
        ]

        document = chunk.document

        results.append(
            {
                "score": float(
                    score
                ),
                "document_id": (
                    chunk.document_id
                ),
                "filename": (
                    document.original_filename
                ),
                "chunk_index": (
                    chunk.chunk_index
                ),
                "page_number": (
                    chunk.page_number
                ),
                "content": (
                    chunk.content
                ),
                "access_scope": (
                    document.access_scope
                ),
                "access_role": (
                    document.access_role
                ),
                "retrieval_method": "bm25",
            }
        )

        if len(results) >= top_k:

            break

    return results