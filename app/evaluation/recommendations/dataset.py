import json
from pathlib import Path

from app.evaluation.recommendations.schemas import (
    RecommendationBenchmarkDataset,
)


class RecommendationDatasetError(ValueError):
    pass


class RecommendationDatasetRegistry:
    def __init__(self):
        self._datasets = {}

    def register(self, dataset):
        name = dataset.dataset_name

        if name in self._datasets:
            raise RecommendationDatasetError(
                f"Dataset already registered: {name}"
            )

        self._datasets[name] = dataset

    def get(self, name):
        if name not in self._datasets:
            raise RecommendationDatasetError(
                f"Unknown dataset: {name}"
            )
        return self._datasets[name]

    def list_names(self):
        return sorted(self._datasets)

    def unregister(self, name):
        if name not in self._datasets:
            raise RecommendationDatasetError(
                f"Unknown dataset: {name}"
            )
        del self._datasets[name]


def load_recommendation_dataset(path):
    source = Path(path)

    if not source.is_file():
        raise FileNotFoundError(source)

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        return RecommendationBenchmarkDataset.model_validate(data)
    except Exception as exc:
        raise RecommendationDatasetError(
            f"Unable to load dataset: {exc}"
        ) from exc


def save_recommendation_dataset(dataset, path):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        dataset.model_dump_json(indent=2),
        encoding="utf-8",
    )
