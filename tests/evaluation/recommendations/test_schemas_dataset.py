import pytest

from app.evaluation.recommendations.schemas import (
    RecommendationBenchmarkCase,
    RecommendationBenchmarkDataset,
)
from app.evaluation.recommendations.dataset import (
    RecommendationDatasetRegistry,
    RecommendationDatasetError,
    save_recommendation_dataset,
    load_recommendation_dataset,
)


def make_dataset():
    return RecommendationBenchmarkDataset(
        dataset_name="recommendation-test",
        cases=[
            RecommendationBenchmarkCase(
                case_id="case-1",
                user_id="user-1",
                query="machine learning",
                relevant_item_ids=["resource-1"],
            )
        ],
    )


def test_benchmark_dataset_creation():
    dataset = make_dataset()
    assert dataset.dataset_name == "recommendation-test"
    assert len(dataset.cases) == 1


def test_duplicate_case_ids_rejected():
    case = RecommendationBenchmarkCase(
        case_id="same",
        user_id="user-1",
        query="AI",
    )

    with pytest.raises(ValueError):
        RecommendationBenchmarkDataset(
            dataset_name="invalid",
            cases=[case, case],
        )


def test_registry_register_and_get():
    registry = RecommendationDatasetRegistry()
    dataset = make_dataset()
    registry.register(dataset)
    assert registry.get("recommendation-test") == dataset


def test_registry_rejects_duplicate_registration():
    registry = RecommendationDatasetRegistry()
    dataset = make_dataset()
    registry.register(dataset)

    with pytest.raises(RecommendationDatasetError):
        registry.register(dataset)


def test_dataset_json_round_trip(tmp_path):
    dataset = make_dataset()
    path = tmp_path / "dataset.json"
    save_recommendation_dataset(dataset, path)
    assert load_recommendation_dataset(path) == dataset
