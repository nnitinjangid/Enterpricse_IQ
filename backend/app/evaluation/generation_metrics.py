import re


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    """

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9%₹.,/\-\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def extract_sentences(
    text: str,
) -> list[str]:

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def tokenize(
    text: str,
) -> set[str]:

    normalized = normalize_text(
        text
    )

    if not normalized:
        return set()

    return set(
        normalized.split()
    )


def faithfulness_score(
    answer: str,
    context: str,
) -> float:
    """
    Measure how much of the answer is supported
    by the retrieved context.

    This is a lightweight lexical approximation.
    It is not a replacement for an LLM judge.
    """

    if not answer or not answer.strip():
        return 0.0

    if not context or not context.strip():
        return 0.0

    answer_sentences = extract_sentences(
        answer
    )

    if not answer_sentences:
        return 0.0

    context_tokens = tokenize(
        context
    )

    if not context_tokens:
        return 0.0

    supported_sentences = 0

    for sentence in answer_sentences:

        sentence_tokens = tokenize(
            sentence
        )

        if not sentence_tokens:
            continue

        overlap = (
            sentence_tokens
            & context_tokens
        )

        overlap_ratio = (
            len(overlap)
            / len(sentence_tokens)
        )

        if overlap_ratio >= 0.5:
            supported_sentences += 1

    return round(
        supported_sentences
        / len(answer_sentences),
        4,
    )


def answer_relevance_score(
    question: str,
    answer: str,
) -> float:
    """
    Measure lexical relevance between
    the question and generated answer.
    """

    if not question or not question.strip():
        return 0.0

    if not answer or not answer.strip():
        return 0.0

    question_tokens = tokenize(
        question
    )

    answer_tokens = tokenize(
        answer
    )

    if not question_tokens:
        return 0.0

    if not answer_tokens:
        return 0.0

    overlap = (
        question_tokens
        & answer_tokens
    )

    return round(
        len(overlap)
        / len(question_tokens),
        4,
    )


def answer_correctness_score(
    answer: str,
    expected_answer: str,
) -> float:
    """
    Measure lexical overlap between the generated
    answer and the expected/reference answer.
    """

    if not answer or not answer.strip():
        return 0.0

    if not expected_answer or not expected_answer.strip():
        return 0.0

    answer_tokens = tokenize(
        answer
    )

    expected_tokens = tokenize(
        expected_answer
    )

    if not expected_tokens:
        return 0.0

    overlap = (
        answer_tokens
        & expected_tokens
    )

    return round(
        len(overlap)
        / len(expected_tokens),
        4,
    )


def evaluate_generation(
    question: str,
    answer: str,
    expected_answer: str,
    context: str,
) -> dict:

    faithfulness = faithfulness_score(
        answer=answer,
        context=context,
    )

    relevance = answer_relevance_score(
        question=question,
        answer=answer,
    )

    correctness = answer_correctness_score(
        answer=answer,
        expected_answer=expected_answer,
    )

    return {
        "faithfulness": faithfulness,
        "answer_relevance": relevance,
        "answer_correctness": correctness,
    }


def evaluate_multiple_generations(
    evaluation_cases: list[dict],
) -> dict:

    if not evaluation_cases:
        return {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "answer_correctness": 0.0,
        }

    results = []

    for case in evaluation_cases:

        result = evaluate_generation(
            question=case["question"],
            answer=case["answer"],
            expected_answer=case["expected_answer"],
            context=case["context"],
        )

        results.append(
            result
        )

    count = len(results)

    total_faithfulness = sum(
        result["faithfulness"]
        for result in results
    )

    total_relevance = sum(
        result["answer_relevance"]
        for result in results
    )

    total_correctness = sum(
        result["answer_correctness"]
        for result in results
    )

    return {
        "faithfulness": round(
            total_faithfulness / count,
            4,
        ),
        "answer_relevance": round(
            total_relevance / count,
            4,
        ),
        "answer_correctness": round(
            total_correctness / count,
            4,
        ),
    }