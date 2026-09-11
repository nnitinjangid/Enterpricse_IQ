import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


# =========================================================
# Paths
# =========================================================

EVALUATION_DIR = Path(__file__).resolve().parent

CHUNKS_FILE = (
    EVALUATION_DIR
    / "available_chunks.json"
)

DATASET_FILE = (
    EVALUATION_DIR
    / "evaluation_dataset.json"
)


# =========================================================
# Get Document Chunks
# =========================================================

def get_all_document_chunks(
    db: Session,
) -> list[dict]:

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

    results = []

    for chunk in chunks:

        document = chunk.document

        results.append(
            {
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "chunk_id": [
                    chunk.document_id,
                    chunk.chunk_index,
                ],
                "filename": (
                    document.original_filename
                ),
                "page_number": (
                    chunk.page_number
                ),
                "content": chunk.content,
            }
        )

    return results


# =========================================================
# Save Available Chunks
# =========================================================

def save_available_chunks(
    chunks: list[dict],
) -> None:

    with open(
        CHUNKS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            chunks,
            file,
            indent=4,
            ensure_ascii=False,
        )


# =========================================================
# Create Empty Evaluation Dataset
# =========================================================

def create_empty_dataset() -> None:

    if DATASET_FILE.exists():

        print(
            "evaluation_dataset.json already exists."
        )

        return

    sample_structure = [
        {
            "question": "",
            "expected_answer": "",
            "relevant_documents": [],
            "relevant_chunks": [],
        }
    ]

    with open(
        DATASET_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            sample_structure,
            file,
            indent=4,
            ensure_ascii=False,
        )


# =========================================================
# Main
# =========================================================

def main():

    print("=" * 70)
    print("ENTERPRISEIQ EVALUATION DATASET BUILDER")
    print("=" * 70)

    db = SessionLocal()

    try:

        chunks = get_all_document_chunks(
            db
        )

        print()
        print(
            f"Total document chunks: {len(chunks)}"
        )

        if not chunks:

            print()
            print(
                "No document chunks found."
            )

            print(
                "Upload and process at least "
                "one document first."
            )

            return

        save_available_chunks(
            chunks
        )

        create_empty_dataset()

        print()
        print(
            f"Available chunks saved to:"
        )
        print(
            CHUNKS_FILE
        )

        print()
        print(
            "Evaluation dataset template:"
        )
        print(
            DATASET_FILE
        )

        print()
        print("-" * 70)
        print("AVAILABLE CHUNKS")
        print("-" * 70)

        for chunk in chunks:

            print()
            print(
                f"Document ID : "
                f"{chunk['document_id']}"
            )

            print(
                f"Chunk Index : "
                f"{chunk['chunk_index']}"
            )

            print(
                f"Filename    : "
                f"{chunk['filename']}"
            )

            print(
                f"Page        : "
                f"{chunk['page_number']}"
            )

            print(
                f"Content     : "
                f"{chunk['content'][:500]}"
            )

            print("-" * 70)

    finally:

        db.close()


if __name__ == "__main__":
    main()