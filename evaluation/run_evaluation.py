import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from app.services.llm_service import generate_llm_response


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_PATH = BASE_DIR / "evaluation" / "academic_questions.json"
RESULTS_DIR = BASE_DIR / "evaluation" / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# EXPECTED ELEMENT KEYWORDS
# ============================================================

ELEMENT_ALIASES = {
    "volatility": ["volatile", "non-volatile"],
    "data storage": ["data storage", "memory storage", "stores data"],
    "read and write operations": ["read/write", "read and write", "read-only"],
    "speed": ["speed", "access time", "faster", "slower"],
    "applications": ["applications", "used for", "use cases"],

    "bst property": ["binary search tree property", "left subtree", "right subtree"],
    "node structure": ["node structure", "left child", "right child"],
    "insertion": ["insertion", "insert"],
    "searching": ["searching", "search operation"],
    "deletion": ["deletion", "delete"],
    "time complexity": ["time complexity", "o(log n)", "o(n)"],

    "max heap property": ["max-heap property", "max heap property", "parent is greater"],
    "heapify up": ["heapify-up", "heapify up", "bubble up", "percolate up"],
    "deletion of root": ["delete the root", "deletion of root", "extract-max", "extract max"],
    "heapify down": ["heapify-down", "heapify down", "percolate down", "sink down"],

    "bfs": ["breadth-first search", "bfs"],
    "dfs": ["depth-first search", "dfs"],
    "queue": ["queue", "fifo"],
    "stack or recursion": ["stack", "recursion", "recursive"],
    "traversal": ["traversal", "visit vertices", "visit nodes"],
    "complexity": ["complexity", "o(v + e)"],

    "binary place values": ["place values", "positional values", "powers of 2"],
    "decimal conversion": ["decimal conversion", "decimal value"],
    "hexadecimal conversion": ["hexadecimal conversion", "hexadecimal"],
    "calculation steps": ["calculation", "step-by-step", "steps"],

    "python code": ["```python", "class ", "def "],
    "push": ["push", "append"],
    "pop": ["pop"],
    "peek": ["peek", "self.items[-1]"],
    "underflow handling": ["underflow", "empty stack", "indexerror"],
}


# ============================================================
# LOAD DATASET
# ============================================================

def load_questions():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        questions = json.load(file)

    if not isinstance(questions, list) or not questions:
        raise ValueError("Evaluation dataset must contain questions.")

    return questions


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# CHECK EXPECTED ELEMENTS
# ============================================================

def evaluate_content(answer, expected_elements):
    answer_text = normalize_text(answer)

    element_results = []

    for element in expected_elements:
        key = normalize_text(element)

        keywords = ELEMENT_ALIASES.get(
            key,
            [element]
        )

        matched = any(
            normalize_text(keyword) in answer_text
            for keyword in keywords
        )

        element_results.append({
            "element": element,
            "covered": matched,
        })

    total = len(element_results)
    covered = sum(
        item["covered"] for item in element_results
    )

    score = round((covered / total) * 100, 2) if total else 0

    return {
        "expected_elements_count": total,
        "covered_elements_count": covered,
        "coverage_percentage": score,
        "element_results": element_results,
    }


# ============================================================
# EVALUATE QUESTIONS
# ============================================================

async def evaluate_question(question):
    question_id = question["id"]
    category = question["category"]
    prompt = question["question"]
    expected = question.get("expected_elements", [])

    logger.info(
        "Evaluating question %s: %s",
        question_id,
        category,
    )

    try:
        answer = await generate_llm_response(prompt)

        content_evaluation = evaluate_content(
            answer,
            expected,
        )

        return {
            "id": question_id,
            "category": category,
            "question": prompt,
            "expected_elements": expected,
            "answer": answer,
            "status": "success",
            "error": None,
            "quality_evaluation": content_evaluation,
        }

    except Exception as exc:
        logger.exception(
            "Evaluation failed for question %s",
            question_id,
        )

        return {
            "id": question_id,
            "category": category,
            "question": prompt,
            "expected_elements": expected,
            "answer": None,
            "status": "failed",
            "error": str(exc),
            "quality_evaluation": None,
        }


# ============================================================
# RUN EVALUATION
# ============================================================

async def run_evaluation():
    questions = load_questions()

    logger.info("Starting ScholarAI academic evaluation.")
    logger.info("Total questions: %s", len(questions))

    results = []

    for question in questions:
        result = await evaluate_question(question)
        results.append(result)

    successful = sum(
        result["status"] == "success"
        for result in results
    )

    failed = len(results) - successful

    successful_results = [
        result for result in results
        if result["status"] == "success"
    ]

    total_expected = sum(
        result["quality_evaluation"]["expected_elements_count"]
        for result in successful_results
    )

    total_covered = sum(
        result["quality_evaluation"]["covered_elements_count"]
        for result in successful_results
    )

    overall_score = (
        round((total_covered / total_expected) * 100, 2)
        if total_expected else 0
    )

    evaluation_report = {
        "project": "ScholarAI",
        "evaluation_type": "Academic Response Quality",
        "model": "Gemini",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(questions),
        "successful_responses": successful,
        "failed_responses": failed,
        "overall_quality_score": overall_score,
        "total_expected_elements": total_expected,
        "total_covered_elements": total_covered,
        "results": results,
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = RESULTS_DIR / f"evaluation_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            evaluation_report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n========== SCHOLARAI EVALUATION ==========")
    print(f"Total questions: {len(questions)}")
    print(f"Successful responses: {successful}")
    print(f"Failed responses: {failed}")
    print(f"Expected elements: {total_expected}")
    print(f"Covered elements: {total_covered}")
    print(f"Overall coverage score: {overall_score}%")

    print("\nQUESTION-WISE SCORES:")

    for result in successful_results:
        quality = result["quality_evaluation"]

        print(
            f"Question {result['id']}: "
            f"{quality['coverage_percentage']}%"
        )

    print(f"\nResults saved to: {output_path}")
    print("===========================================")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(run_evaluation())