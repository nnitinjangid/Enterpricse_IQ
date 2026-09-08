import re


# =========================================================
# Text Cleaning
# =========================================================

def clean_text(text: str) -> str:
    """
    Clean extracted document text.

    Operations:
    - Remove null/control characters
    - Normalize whitespace
    - Remove excessive blank lines
    - Preserve readable document structure
    """

    if not text:
        return ""

    # Remove null characters
    text = text.replace("\x00", "")

    # Normalize Windows line endings
    text = text.replace("\r\n", "\n")

    # Normalize tabs
    text = text.replace("\t", " ")

    # Remove spaces before/after lines
    lines = []

    for line in text.split("\n"):

        line = line.strip()

        if line:
            lines.append(line)

    text = "\n".join(lines)

    # Remove excessive spaces
    text = re.sub(
        r"[ ]{2,}",
        " ",
        text,
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


# =========================================================
# Split Text Into Chunks
# =========================================================

def split_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Split text into overlapping chunks.

    chunk_size:
        Maximum approximate number of characters
        in each chunk.

    chunk_overlap:
        Number of characters shared between
        consecutive chunks.
    """

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0."
        )

    if chunk_overlap < 0:
        raise ValueError(
            "chunk_overlap cannot be negative."
        )

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size."
        )

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - chunk_overlap

    return chunks


# =========================================================
# PDF Page Parser
# =========================================================

def parse_pages(text: str) -> list[dict]:
    """
    Parse extracted PDF text into individual pages.

    Expected format:

    [Page 1]
    page content...

    [Page 2]
    page content...
    """

    if not text:
        return []

    pattern = r"\[Page\s+(\d+)\]"

    matches = list(
        re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
    )

    # If no page markers exist,
    # treat the entire document as one page.
    if not matches:
        cleaned = clean_text(text)

        if not cleaned:
            return []

        return [
            {
                "page_number": None,
                "text": cleaned,
            }
        ]

    pages = []

    for index, match in enumerate(matches):

        page_number = int(
            match.group(1)
        )

        start = match.end()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        page_text = text[start:end]

        page_text = clean_text(
            page_text
        )

        if page_text:
            pages.append(
                {
                    "page_number": page_number,
                    "text": page_text,
                }
            )

    return pages


# =========================================================
# Create Document Chunks
# =========================================================

def create_document_chunks(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    """
    Clean and chunk document text while
    preserving page metadata.
    """

    pages = parse_pages(text)

    chunks = []

    chunk_index = 0

    for page in pages:

        page_number = page["page_number"]
        page_text = page["text"]

        page_chunks = split_text(
            page_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk in page_chunks:

            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "content": chunk,
                }
            )

            chunk_index += 1

    return chunks