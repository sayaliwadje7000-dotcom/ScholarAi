import json

from app.evaluation.experiments.comparison import compare_experiment
from app.evaluation.experiments.reporting import (
    render_report,
    report_to_dict,
    save_report,
)
from app.evaluation.experiments.schemas import (
    ExperimentConfig,
    ExperimentObservation,
)


def make_report():
    config = ExperimentConfig(
        experiment_id="exp-report",
        baseline_variant="baseline",
        candidate_variant="candidate",
        metric_name="accuracy",
        minimum_samples_per_variant=10,
        bootstrap_iterations=500,
    )

    observations = []

    for index in range(20):
        sample_id = f"sample-{index}"

        observations.extend([
            ExperimentObservation(
                experiment_id="exp-report",
                variant="baseline",
                metric_name="accuracy",
                sample_id=sample_id,
                value=0.7,
            ),
            ExperimentObservation(
                experiment_id="exp-report",
                variant="candidate",
                metric_name="accuracy",
                sample_id=sample_id,
                value=0.9,
            ),
        ])

    return compare_experiment(config, observations)


def test_report_to_dict():
    result = report_to_dict(make_report())

    assert result["experiment_id"] == "exp-report"
    assert result["candidate_variant"] == "candidate"


def test_render_report():
    rendered = render_report(make_report())

    assert "Experiment: exp-report" in rendered
    assert "Mean difference:" in rendered
    assert "P-value:" in rendered


def test_save_report(tmp_path):
    report = make_report()
    path = save_report(report, tmp_path / "reports" / "report.json")

    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["experiment_id"] == "exp-report"
    assert data["passed"] is True
