import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

from app.services.llm_service import generate_llm_response


DATASET_PATH = BASE_DIR / "evaluation" / "reliability_questions.json"
RESULTS_DIR = BASE_DIR / "evaluation" / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize(text):
    """Normalize text for phrase matching."""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_questions():
    """Load and validate the reliability dataset."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        questions = json.load(file)

    if not isinstance(questions, list) or not questions:
        raise ValueError("Reliability dataset is empty or invalid.")

    for question in questions:
        if "id" not in question:
            raise ValueError("Question is missing an ID.")

        if "question" not in question:
            raise ValueError("Question is missing its text.")

        if "expected_behaviors" not in question:
            raise ValueError(
                f"Question {question['id']} has no expected_behaviors."
            )

        for behavior in question["expected_behaviors"]:
            if "name" not in behavior or "any" not in behavior:
                raise ValueError(
                    f"Invalid behavior structure in question {question['id']}."
                )

    return questions


def score_reliability(answer, expected_behaviors):
    """
    Evaluate expected reliability signals.

    Each behavior passes when at least one phrase
    from its 'any' list appears in the answer.
    """

    normalized_answer = normalize(answer)

    matched_behaviors = []
    missing_behaviors = []
    behavior_details = []

    for behavior in expected_behaviors:

        behavior_name = behavior["name"]
        expected_phrases = behavior["any"]

        matched_phrases = [
            phrase
            for phrase in expected_phrases
            if normalize(phrase) in normalized_answer
        ]

        matched = len(matched_phrases) > 0

        if matched:
            matched_behaviors.append(behavior_name)
        else:
            missing_behaviors.append(behavior_name)

        behavior_details.append({
            "behavior": behavior_name,
            "matched": matched,
            "matched_phrases": matched_phrases
        })

    total = len(expected_behaviors)
    matched_count = len(matched_behaviors)

    score = (
        matched_count / total * 100
        if total else 0
    )

    return {
        "expected_behavior_count": total,
        "matched_behavior_count": matched_count,
        "reliability_screening_score": round(score, 2),
        "matched_behaviors": matched_behaviors,
        "missing_behaviors": missing_behaviors,
        "behavior_details": behavior_details
    }


async def evaluate_question(question_data):
    """Generate and evaluate one reliability response."""

    question_id = question_data["id"]
    question = question_data["question"]

    logger.info(
        "Running reliability test %s",
        question_id
    )

    try:
        answer = await generate_llm_response(question)

        evaluation = score_reliability(
            answer,
            question_data["expected_behaviors"]
        )

        return {
            "id": question_id,
            "category": question_data.get("category"),
            "question": question,
            "status": "success",
            "answer": answer,
            "evaluation": evaluation
        }

    except Exception as error:

        logger.exception(
            "Reliability test %s failed",
            question_id
        )

        return {
            "id": question_id,
            "category": question_data.get("category"),
            "question": question,
            "status": "failed",
            "error": str(error)
        }


async def run_evaluation():

    questions = load_questions()

    results = []

    for question_data in questions:
        result = await evaluate_question(question_data)
        results.append(result)

    successful = [
        result for result in results
        if result["status"] == "success"
    ]

    failed = [
        result for result in results
        if result["status"] == "failed"
    ]

    total_behaviors = sum(
        result["evaluation"]["expected_behavior_count"]
        for result in successful
    )

    matched_behaviors = sum(
        result["evaluation"]["matched_behavior_count"]
        for result in successful
    )

    overall_score = (
        matched_behaviors / total_behaviors * 100
        if total_behaviors else 0
    )

    report = {
        "evaluation_type": "Academic Response Reliability Evaluation",
        "phase": "5.7",
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(questions),
        "successful": len(successful),
        "failed": len(failed),
        "total_expected_behaviors": total_behaviors,
        "matched_behaviors": matched_behaviors,
        "overall_reliability_screening_score": round(
            overall_score, 2
        ),
        "results": results
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_path = (
        RESULTS_DIR / f"reliability_{timestamp}.json"
    )

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n========== PHASE 5.7 RELIABILITY ==========")

    print(f"Total questions: {len(questions)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    print(f"Expected behaviors: {total_behaviors}")
    print(f"Matched behaviors: {matched_behaviors}")

    print(
        f"Overall reliability screening score: "
        f"{overall_score:.2f}%"
    )

    print("\nINDIVIDUAL RESULTS:")

    for result in results:

        if result["status"] == "success":

            evaluation = result["evaluation"]

            print(
                f"Q{result['id']}: "
                f"{evaluation['reliability_screening_score']}%"
            )

            if evaluation["missing_behaviors"]:
                print(
                    "  Missing:",
                    evaluation["missing_behaviors"]
                )

        else:
            print(f"Q{result['id']}: FAILED")

    print(f"\nReport saved at: {report_path}")
    print("============================================\n")


if __name__ == "__main__":
    asyncio.run(run_evaluation())