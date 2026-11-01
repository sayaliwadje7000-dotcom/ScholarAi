"""
ScholarAI Safety Evaluation.

Evaluates deterministic safety screening locally.
Does not call Gemini or consume API quota.
"""

import json

from pathlib import Path

from app.services.safety_service import evaluate_message


BASE_DIR = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    BASE_DIR
    / "evaluation"
    / "safety"
    / "safety_questions.json"
)

RESULTS_DIR = (
    BASE_DIR
    / "evaluation"
    / "results"
    / "safety"
)


def load_dataset():

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def evaluate_dataset():

    questions = load_dataset()

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []

    passed = 0

    for item in questions:

        result = evaluate_message(item["question"])

        actual = (
            "allow"
            if result.allowed
            else "block"
        )

        success = actual == item["expected"]

        if success:
            passed += 1

        results.append({

            "id": item["id"],

            "category": item["category"],

            "expected": item["expected"],

            "actual": actual,

            "detected_category": result.category.value,

            "passed": success,

        })

        print(
            f"Q{item['id']}: "
            f"{'PASS' if success else 'FAIL'} "
            f"| Expected={item['expected']} "
            f"| Actual={actual}"
        )

    total = len(questions)

    accuracy = (
        passed / total * 100
        if total
        else 0
    )

    report = {

        "total_questions": total,

        "passed": passed,

        "failed": total - passed,

        "screening_accuracy": round(accuracy, 2),

        "results": results,

    }

    report_path = RESULTS_DIR / "safety_report.json"

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
        )

    print("\nSAFETY EVALUATION SUMMARY")

    print(f"Total: {total}")

    print(f"Passed: {passed}")

    print(f"Failed: {total - passed}")

    print(f"Screening accuracy: {accuracy:.2f}%")

    print(f"Report: {report_path}")


if __name__ == "__main__":

    evaluate_dataset()