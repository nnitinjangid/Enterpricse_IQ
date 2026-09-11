import json
from pathlib import Path

from app.core.database import SessionLocal
from app.evaluation.agent_evaluator import (
    evaluate_agent_dataset,
)


DATASET_PATH = (
    Path(__file__).resolve().parent
    / "agent_evaluation_dataset.json"
)


def load_dataset() -> list[dict]:

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        dataset = json.load(file)

    if not isinstance(
        dataset,
        list,
    ):
        raise ValueError(
            "Agent evaluation dataset "
            "must be a JSON list."
        )

    return dataset


def main():

    print()
    print("=" * 70)
    print("              ENTERPRISEIQ AGENT EVALUATION")
    print("=" * 70)

    dataset = load_dataset()

    print()
    print(
        f"Total evaluation questions: "
        f"{len(dataset)}"
    )

    db = SessionLocal()

    try:

        user_id = 1
        user_role = "admin"

        result = evaluate_agent_dataset(
            dataset=dataset,
            db=db,
            user_id=user_id,
            user_role=user_role,
        )

        print()
        print("=" * 70)
        print("                    FINAL RESULTS")
        print("=" * 70)

        average_metrics = result[
            "average_metrics"
        ]

        print()
        print("-" * 70)
        print("AGENT METRICS")
        print("-" * 70)

        print(
            f"Route Accuracy           : "
            f"{average_metrics['route_accuracy']:.4f}"
        )

        print(
            f"Tool Selection Accuracy  : "
            f"{average_metrics['tool_selection_accuracy']:.4f}"
        )

        print(
            f"Tool Execution Accuracy  : "
            f"{average_metrics['tool_execution_accuracy']:.4f}"
        )

        print(
            f"Final Answer Accuracy    : "
            f"{average_metrics['final_answer_accuracy']:.4f}"
        )

        print()
        print("-" * 70)
        print("QUESTION-WISE RESULTS")
        print("-" * 70)

        for index, question_result in enumerate(
            result["questions"],
            start=1,
        ):

            print()
            print("=" * 70)
            print(
                f"QUESTION {index}"
            )
            print("=" * 70)

            print(
                f"Question:\n"
                f"{question_result['question']}"
            )

            print()
            print(
                f"Expected Route : "
                f"{question_result['expected_route']}"
            )

            print(
                f"Actual Route   : "
                f"{question_result['actual_route']}"
            )

            print()
            print(
                f"Expected Tools : "
                f"{question_result['expected_tools']}"
            )

            print(
                f"Actual Tools   : "
                f"{question_result['actual_tools']}"
            )

            print()
            print(
                f"Expected Answer Values:"
            )

            print(
                question_result[
                    "expected_answer_contains"
                ]
            )

            print()
            print("-" * 70)
            print("ACTUAL FINAL ANSWER")
            print("-" * 70)

            print(
                question_result.get(
                    "answer",
                    "",
                )
            )

            print()
            print("-" * 70)
            print("TOOL RESULTS")
            print("-" * 70)

            tool_results = question_result.get(
                "tool_results",
                {},
            )

            if tool_results:

                print(
                    json.dumps(
                        tool_results,
                        indent=2,
                        ensure_ascii=False,
                        default=str,
                    )
                )

            else:

                print(
                    "No tool results."
                )

            print()
            print("-" * 70)
            print("METRICS")
            print("-" * 70)

            metrics = question_result[
                "metrics"
            ]

            print(
                f"Route Accuracy          : "
                f"{metrics['route_accuracy']:.4f}"
            )

            print(
                f"Tool Selection Accuracy : "
                f"{metrics['tool_selection_accuracy']:.4f}"
            )

            print(
                f"Tool Execution Accuracy : "
                f"{metrics['tool_execution_accuracy']:.4f}"
            )

            print(
                f"Final Answer Accuracy   : "
                f"{metrics['final_answer_accuracy']:.4f}"
            )

        print()
        print("=" * 70)
        print("Agent evaluation completed.")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()