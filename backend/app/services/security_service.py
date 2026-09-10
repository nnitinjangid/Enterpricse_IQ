import re


# ---------------------------------------------------------
# Prompt Injection Detection
# ---------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"forget\s+(all\s+)?prior\s+instructions",
    r"disregard\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior\s+instructions",
    r"override\s+(the\s+)?system\s+prompt",
    r"override\s+(all\s+)?instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"show\s+(me\s+)?the\s+system\s+prompt",
    r"print\s+(the\s+)?system\s+prompt",
    r"reveal\s+(your\s+)?hidden\s+instructions",
    r"show\s+(your\s+)?hidden\s+instructions",
    r"reveal\s+confidential\s+information",
    r"reveal\s+secret\s+information",
    r"reveal\s+private\s+information",
    r"bypass\s+(all\s+)?security",
    r"bypass\s+(the\s+)?security",
    r"disable\s+(all\s+)?security",
    r"disable\s+(the\s+)?security",
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
    r"you\s+are\s+now\s+unrestricted",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"enter\s+developer\s+mode",
    r"jailbreak",
]


def normalize_text(
    text: str,
) -> str:

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def detect_prompt_injection(
    text: str,
) -> dict:

    if not text or not text.strip():

        return {
            "is_injection": False,
            "risk_level": "low",
            "matched_patterns": [],
        }

    normalized_text = normalize_text(
        text
    )

    matched_patterns = []

    for pattern in INJECTION_PATTERNS:

        if re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        ):

            matched_patterns.append(
                pattern
            )

    if matched_patterns:

        return {
            "is_injection": True,
            "risk_level": "high",
            "matched_patterns": matched_patterns,
        }

    return {
        "is_injection": False,
        "risk_level": "low",
        "matched_patterns": [],
    }


def validate_user_query(
    question: str,
) -> None:

    if not question or not question.strip():

        raise ValueError(
            "Question cannot be empty."
        )

    result = detect_prompt_injection(
        question
    )

    if result["is_injection"]:

        raise PermissionError(
            "Potential prompt injection detected. "
            "The request was blocked for security reasons."
        )


# ---------------------------------------------------------
# Retrieved Document Protection
# ---------------------------------------------------------

def sanitize_retrieved_content(
    content: str,
) -> str:

    if not content:
        return ""

    cleaned = content

    suspicious_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?prior\s+instructions",
        r"forget\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?previous\s+instructions",
        r"override\s+(the\s+)?system\s+prompt",
        r"reveal\s+(the\s+)?system\s+prompt",
        r"reveal\s+(your\s+)?hidden\s+instructions",
    ]

    for pattern in suspicious_patterns:

        cleaned = re.sub(
            pattern,
            "[REMOVED_UNTRUSTED_INSTRUCTION]",
            cleaned,
            flags=re.IGNORECASE,
        )

    return cleaned


def is_safe_retrieved_content(
    content: str,
) -> bool:

    if not content:
        return True

    result = detect_prompt_injection(
        content
    )

    return not result["is_injection"]