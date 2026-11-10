from __future__ import annotations

import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "phase_20"

JUNIT_REPORT = ARTIFACT_DIR / "final_validation_junit.xml"

JSON_REPORT = ARTIFACT_DIR / "final_validation_report.json"


def run_command(
    command: list[str],
    working_directory: Path,
) -> dict:
    started_at = time.time()

    result = subprocess.run(
        command,
        cwd=working_directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    duration = round(time.time() - started_at, 3)

    return {
        "command": command,
        "return_code": result.returncode,
        "duration_seconds": duration,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.returncode == 0,
    }


def parse_junit_report(report_path: Path) -> dict:
    if not report_path.exists():
        return {
            "available": False,
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        }

    try:
        root = ET.parse(report_path).getroot()

        if root.tag == "testsuites":
            suites = list(root.findall("testsuite"))
        elif root.tag == "testsuite":
            suites = [root]
        else:
            suites = []

        totals = {
            "available": True,
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        }

        for suite in suites:
            totals["tests"] += int(suite.get("tests", 0))
            totals["failures"] += int(suite.get("failures", 0))
            totals["errors"] += int(suite.get("errors", 0))
            totals["skipped"] += int(suite.get("skipped", 0))

        totals["passed"] = max(
            0,
            totals["tests"]
            - totals["failures"]
            - totals["errors"]
            - totals["skipped"],
        )

        return totals

    except (ET.ParseError, OSError, ValueError) as exc:
        return {
            "available": False,
            "error": str(exc),
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        }


def save_json_report(report: dict) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    JSON_REPORT.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("SCHOLARAI - PHASE 20 FINAL RELIABILITY VALIDATION")
    print("=" * 72)

    validation_started = time.time()

    report = {
        "project": "ScholarAI",
        "phase": "20.10",
        "validation_started_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "checks": {},
        "test_summary": {},
        "overall_status": "FAILED",
    }

    # -------------------------------------------------
    # CHECK 1: PYTHON COMPILATION
    # -------------------------------------------------

    print("\n[1/2] Checking Python compilation...")

    compilation = run_command(
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "app",
            "tests",
        ],
        PROJECT_ROOT,
    )

    report["checks"]["python_compilation"] = {
        "passed": compilation["passed"],
        "return_code": compilation["return_code"],
        "duration_seconds": compilation["duration_seconds"],
        "stderr": compilation["stderr"],
    }

    print(
        "Compilation:",
        "PASSED" if compilation["passed"] else "FAILED",
    )

    # -------------------------------------------------
    # CHECK 2: COMPLETE PYTEST SUITE
    # -------------------------------------------------

    if compilation["passed"]:
        print("\n[2/2] Running complete automated test suite...")

        testing = run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "-v",
                f"--junitxml={JUNIT_REPORT}",
            ],
            PROJECT_ROOT,
        )

        report["checks"]["automated_test_suite"] = {
            "passed": testing["passed"],
            "return_code": testing["return_code"],
            "duration_seconds": testing["duration_seconds"],
            "stdout": testing["stdout"],
            "stderr": testing["stderr"],
        }

        print(testing["stdout"])

        if testing["stderr"]:
            print("\nPytest stderr:")
            print(testing["stderr"])

        report["test_summary"] = parse_junit_report(
            JUNIT_REPORT
        )

        print("\nTest summary:")
        print(
            json.dumps(
                report["test_summary"],
                indent=4,
            )
        )

    else:
        print("\n[2/2] Pytest skipped because compilation failed.")

        report["checks"]["automated_test_suite"] = {
            "passed": False,
            "skipped": True,
            "reason": "Python compilation failed.",
        }

    # -------------------------------------------------
    # FINAL RESULT
    # -------------------------------------------------

    compilation_passed = report["checks"][
        "python_compilation"
    ]["passed"]

    tests_passed = report["checks"][
        "automated_test_suite"
    ]["passed"]

    report["overall_status"] = (
        "PASSED"
        if compilation_passed and tests_passed
        else "FAILED"
    )

    report["validation_duration_seconds"] = round(
        time.time() - validation_started,
        3,
    )

    report["validation_completed_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    save_json_report(report)

    print("\n" + "=" * 72)
    print("FINAL VALIDATION RESULT:", report["overall_status"])
    print("=" * 72)

    print("\nGenerated reports:")
    print(f"JUnit: {JUNIT_REPORT}")
    print(f"JSON:  {JSON_REPORT}")

    return 0 if report["overall_status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
