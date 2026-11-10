from pathlib import Path

from app.evaluation.rag.schemas import RAGBenchmarkDataset
from app.schemas.rag_evaluation import RAGEvaluationDataset


class RAGDatasetRegistry:
    """Version-aware in-memory registry for RAG benchmark datasets."""

    def __init__(self):
        self._datasets: dict[str, dict[str, RAGBenchmarkDataset]] = {}

    def register(self, dataset: RAGBenchmarkDataset) -> None:
        if not isinstance(dataset, RAGBenchmarkDataset):
            raise TypeError("dataset must be a RAGBenchmarkDataset")

        versions = self._datasets.setdefault(dataset.dataset_name, {})

        if dataset.version in versions:
            raise ValueError(
                f"Dataset '{dataset.dataset_name}' version "
                f"'{dataset.version}' is already registered"
            )

        versions[dataset.version] = dataset

    def get(self, dataset_name: str, version: str) -> RAGBenchmarkDataset:
        try:
            return self._datasets[dataset_name][version]
        except KeyError as exc:
            raise KeyError(
                f"Dataset '{dataset_name}' version '{version}' was not found"
            ) from exc

    def list_versions(self, dataset_name: str) -> list[str]:
        return sorted(self._datasets.get(dataset_name, {}).keys())


def validate_rag_dataset(
    dataset: RAGEvaluationDataset,
) -> RAGEvaluationDataset:
    if not isinstance(dataset, RAGEvaluationDataset):
        raise TypeError("dataset must be a RAGEvaluationDataset")

    if not dataset.cases:
        raise ValueError("RAG evaluation dataset cannot be empty")

    case_ids = [case.case_id for case in dataset.cases]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError("RAG evaluation dataset contains duplicate case IDs")

    return dataset


def load_rag_dataset(path: str | Path) -> RAGEvaluationDataset:
    dataset_path = Path(path)

    if not dataset_path.exists():
        raise FileNotFoundError(f"RAG dataset not found: {dataset_path}")

    if not dataset_path.is_file():
        raise ValueError("Dataset path must point to a file")

    try:
        raw_data = dataset_path.read_text(encoding="utf-8")
        dataset = RAGEvaluationDataset.model_validate_json(raw_data)
    except Exception as exc:
        raise ValueError(
            f"Unable to load RAG evaluation dataset: {exc}"
        ) from exc

    return validate_rag_dataset(dataset)


def save_rag_dataset(
    dataset: RAGEvaluationDataset,
    path: str | Path,
) -> Path:
    validate_rag_dataset(dataset)

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        dataset.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return destination
