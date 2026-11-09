from scripts.phase_16_10_integration_audit import (
    IMPORTANT_INTEGRATION_GAPS,
    REQUIRED_FILES,
    build_audit_report,
    inspect_required_files,
)


def test_audit_contains_all_phase_16_subphases():

    report = build_audit_report()

    expected_phases = {
        "16.1",
        "16.2",
        "16.3",
        "16.4",
        "16.5",
        "16.6",
        "16.7",
        "16.8",
        "16.9",
    }

    assert set(report["file_inventory"]) == expected_phases


def test_required_file_inventory_is_not_empty():

    for phase, files in REQUIRED_FILES.items():

        assert phase.startswith("16.")

        assert files


def test_audit_reports_file_presence_consistently():

    results = inspect_required_files()

    for phase, result in results.items():

        assert result["expected_files"] == (
            result["present_files"]
            + len(result["missing_files"])
        )

        if result["missing_files"]:
            assert result["status"] == "FILES_MISSING"
        else:
            assert result["status"] == "FILES_PRESENT"


def test_audit_reports_known_integration_gaps():

    report = build_audit_report()

    assert report["integration_gaps"] == (
        IMPORTANT_INTEGRATION_GAPS
    )

    assert len(report["integration_gaps"]) >= 4


def test_audit_does_not_claim_runtime_verification():

    report = build_audit_report()

    assert "runtime correctness" in (
        report["verification_warning"]
    )


def test_audit_contains_phase_metadata():

    report = build_audit_report()

    assert report["project"] == "ScholarAI"

    assert report["phase"] == "16"

    assert report["phase_title"] == (
        "Personalized Learning and Adaptive Recommendations"
    )