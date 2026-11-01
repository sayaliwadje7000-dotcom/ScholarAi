
import json
from pathlib import Path

from evaluation.run_reliability import score_reliability


BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    BASE_DIR / "evaluation" / "reliability_questions.json"
)


def load_questions():
    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def test_ambiguous_question_detection():
    questions = load_questions()
    question = next(q for q in questions if q["id"] == 1)

    unreliable_answer = (
        "A stack is something used to store items."
    )

    result = score_reliability(
        unreliable_answer,
        question["expected_behaviors"]
    )

    assert result["reliability_screening_score"] < 100

    print("PASS: Ambiguous response correctly detected.")


def test_false_bst_premise_detection():
    questions = load_questions()
    question = next(q for q in questions if q["id"] == 2)

    unreliable_answer = (
        "Every Binary Search Tree is balanced. "
        "Searching always takes O(log n)."
    )

    result = score_reliability(
        unreliable_answer,
        question["expected_behaviors"]
    )

    assert (
        "Corrects the false premise"
        in result["missing_behaviors"]
    )

    assert result["reliability_screening_score"] < 100

    print("PASS: False BST premise correctly detected.")


def test_invalid_mathematics_detection():
    questions = load_questions()
    question = next(q for q in questions if q["id"] == 3)

    unreliable_answer = (
        "1 divided by 0 equals 5. "
        "The calculation is correct."
    )

    result = score_reliability(
        unreliable_answer,
        question["expected_behaviors"]
    )

    assert result["reliability_screening_score"] < 100

    print("PASS: Invalid mathematical claim correctly detected.")


def test_fabricated_information_detection():
    questions = load_questions()
    question = next(q for q in questions if q["id"] == 4)

    unreliable_answer = (
        "The exact examination question tomorrow will be: "
        "Explain the working of a Binary Search Tree."
    )

    result = score_reliability(
        unreliable_answer,
        question["expected_behaviors"]
    )

    assert result["reliability_screening_score"] < 100

    print("PASS: Fabricated information correctly detected.")


def test_programming_edge_case_detection():
    questions = load_questions()
    question = next(q for q in questions if q["id"] == 5)

    unreliable_answer = """
    ```python
    def get_first(items):
        return items[0]
    ```
    """

    result = score_reliability(
        unreliable_answer,
        question["expected_behaviors"]
    )

    assert (
        "Handles the empty-list case"
        in result["missing_behaviors"]
    )

    assert result["reliability_screening_score"] < 100

    print("PASS: Missing empty-list handling correctly detected.")


def test_all_negative_cases():

    test_ambiguous_question_detection()
    test_false_bst_premise_detection()
    test_invalid_mathematics_detection()
    test_fabricated_information_detection()
    test_programming_edge_case_detection()

    print("\nAll five negative test cases passed.")

