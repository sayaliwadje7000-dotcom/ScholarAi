from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIRECTORY = PROJECT_ROOT / "artifacts"
AUDIT_OUTPUT_FILE = ARTIFACT_DIRECTORY / "phase_16_10_integration_audit.json"


REQUIRED_FILES: dict[str, list[str]] = {
    "16.1": [
        "docs/phase-16-1-personalization-architecture-audit.md",
    ],
    "16.2": [
        "app/schemas/learning_profile.py",
        "app/services/learning_profile_service.py",
        "app/api/learning_profile.py",
        "tests/test_learning_profile_schemas.py",
        "tests/test_learning_profile_service.py",
    ],
    "16.3": [
        "app/schemas/behavioral_signals.py",
        "app/services/behavioral_signal_service.py",
        "app/api/learning_activities.py",
    ],
    "16.4": [
        "app/services/recommendations/feedback_intelligence_service.py",
        "app/services/recommendations/feedback_signal_adapter.py",
    ],
    "16.5": [
        "app/schemas/personalized_learning_context.py",
        "app/services/recommendations/personalized_context_engine.py",
    ],
    "16.6": [
        "app/schemas/adaptive_recommendations.py",
        "app/services/recommendations/adaptive_policy_engine.py",
        "app/services/recommendations/adaptive_hybrid_service.py",
        "app/services/recommendations/hybrid_executor.py",
    ],
    "16.7": [
        "app/schemas/sparse_data.py",
        "app/services/recommendations/sparse_data_assessor.py",
        "app/services/recommendations/cold_start_strategy.py",
        "app/services/recommendations/exploration_allocator.py",
        "app/services/recommendations/sparse_data_intelligence.py",
    ],
    "16.8": [
        "app/schemas/personalization_controls.py",
        "app/services/personalization_controls_service.py",
        "app/api/personalization_controls.py",
        "tests/schemas/test_personalization_controls.py",
        "tests/services/test_personalization_controls_service.py",
        "tests/api/test_personalization_controls.py",
    ],
    "16.9": [
        "app/schemas/personalization_evaluation.py",
        "app/services/recommendations/personalization_evaluation_service.py",
        "tests/schemas/test_personalization_evaluation.py",
        "tests/services/recommendations/test_personalization_evaluation_service.py",
    ],
}


IMPORTANT_INTEGRATION_GAPS = [
    {
        "id": "P16-INT-001",
        "title": "Adaptive policy integration",
        "description": (
            "Adaptive policy weights have not yet been proven to affect "
            "the actual Phase 15 hybrid recommendation ranking."
        ),
        "status": "REQUIRES_INTEGRATION",
        "target_phase": "16",
    },
    {
        "id": "P16-INT-002",
        "title": "Exploration allocation integration",
        "description": (
            "Exploration ratios are calculated, but their enforcement "
            "inside the Phase 15 candidate allocation pipeline has not "
            "yet been demonstrated."
        ),
        "status": "REQUIRES_INTEGRATION",
        "target_phase": "16",
    },
    {
        "id": "P16-INT-003",
        "title": "Authentication integration",
        "description": (
            "Personalization endpoints still depend on the authentication "
            "placeholder. Production authentication and authorization "
            "are deferred to Phase 18."
        ),
        "status": "DEFERRED",
        "target_phase": "18",
    },
    {
        "id": "P16-INT-004",
        "title": "Evaluation dataset",
        "description": (
            "Personalization evaluation requires representative labelled "
            "recommendation and relevance data before its metrics can "
            "support reliable production conclusions."
        ),
        "status": "REQUIRES_DATA",
        "target_phase": "19",
    },
    {
        "id": "P16-INT-005",
        "title": "Production evaluation workflow",
        "description": (
            "The evaluation service currently evaluates explicitly "
            "provided cases. A production evaluation API or automated "
            "evaluation workflow has not been implemented."
        ),
        "status": "NOT_IMPLEMENTED",
        "target_phase": "19",
    },
]


def inspect_required_files() -> dict[str, dict[str, Any]]:
    """Inspect expected Phase 16 implementation files."""

    inventory = {}

    for subphase, paths in REQUIRED_FILES.items():
        present = [
            path
            for path in paths
            if (PROJECT_ROOT / path).is_file()
        ]

        missing = [
            path
            for path in paths
            if not (PROJECT_ROOT / path).is_file()
        ]

        inventory[subphase] = {
            "expected_files": len(paths),
            "present_files": len(present),
            "missing_files": missing,
            "status": (
                "FILES_PRESENT"
                if not missing
                else "FILES_MISSING"
            ),
        }

    return inventory


def build_audit_report() -> dict[str, Any]:
    """Build the Phase 16.10 integration audit report."""

    file_inventory = inspect_required_files()

    expected_count = sum(
        item["expected_files"]
        for item in file_inventory.values()
    )

    present_count = sum(
        item["present_files"]
        for item in file_inventory.values()
    )

    missing_count = expected_count - present_count

    all_files_present = missing_count == 0

    return {
        "project": "ScholarAI",
        "phase": "16",
        "phase_title": (
            "Personalized Learning and Adaptive Recommendations"
        ),
        "audit_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "file_inventory": file_inventory,

        "summary": {
            "expected_files": expected_count,
            "present_files": present_count,
            "missing_files": missing_count,
            "all_expected_files_present": all_files_present,
        },

        "integration_gaps": IMPORTANT_INTEGRATION_GAPS,

        "completion_status": (
            "IMPLEMENTATION_INVENTORY_COMPLETE"
            if all_files_present
            else "IMPLEMENTATION_INVENTORY_INCOMPLETE"
        ),

        "verification_warning": (
            "File presence does not establish runtime correctness, "
            "implementation correctness, successful test execution, "
            "database correctness, API integration, or production readiness. "
            "These require separate verification."
        ),
    }


def main() -> None:
    report = build_audit_report()

    ARTIFACT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with AUDIT_OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("=" * 65)
    print("SCHOLARAI — PHASE 16.10 INTEGRATION AUDIT")
    print("=" * 65)

    print(f"Expected files: {report['summary']['expected_files']}")
    print(f"Present files: {report['summary']['present_files']}")
    print(f"Missing files: {report['summary']['missing_files']}")

    print(f"Completion: {report['completion_status']}")

    print(
        f"Integration gaps: "
        f"{len(report['integration_gaps'])}"
    )

    print(f"\nReport saved: {AUDIT_OUTPUT_FILE}")


if __name__ == "__main__":
    main()