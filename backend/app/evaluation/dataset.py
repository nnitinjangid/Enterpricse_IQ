import json
from pathlib import Path


# =========================================================
# Evaluation Dataset Path
# =========================================================

DATASET_PATH = (
    Path(__file__).resolve().parent
    / "evaluation_dataset.json"
)


# =========================================================
# Load Evaluation Dataset
# =========================================================

def load_evaluation_dataset() -> list[dict]:

    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            f"Evaluation dataset not found: "
            f"{DATASET_PATH}"
        )

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        dataset = json.load(file)

    if not isinstance(dataset, list):

        raise ValueError(
            "Evaluation dataset must contain "
            "a JSON list."
        )

    return dataset


# =========================================================
# Validate Evaluation Dataset
# =========================================================

def validate_evaluation_dataset(
    dataset: list[dict],
) -> None:

    required_fields = {
        "question",
        "expected_answer",
        "relevant_documents",
        "relevant_chunks",
    }

    for index, item in enumerate(
        dataset,
        start=1,
    ):

        if not isinstance(item, dict):

            raise ValueError(
                f"Dataset item {index} must be an object."
            )

        missing_fields = (
            required_fields
            - item.keys()
        )

        if missing_fields:

            raise ValueError(
                f"Dataset item {index} is missing "
                f"fields: {missing_fields}"
            )

        if not isinstance(
            item["relevant_documents"],
            list,
        ):

            raise ValueError(
                f"relevant_documents in item "
                f"{index} must be a list."
            )

        if not isinstance(
            item["relevant_chunks"],
            list,
        ):

            raise ValueError(
                f"relevant_chunks in item "
                f"{index} must be a list."
            )


# =========================================================
# Load + Validate
# =========================================================

def get_evaluation_dataset() -> list[dict]:

    dataset = load_evaluation_dataset()

    validate_evaluation_dataset(
        dataset
    )

    return dataset