from dataclasses import dataclass
from enum import Enum


class EmbeddingTask(str, Enum):
    DOCUMENT = "document"
    QUERY = "query"


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    text: str
    task: EmbeddingTask

    def __post_init__(self):
        if not isinstance(self.text, str):
            raise TypeError("Embedding text must be a string.")

        if not self.text.strip():
            raise ValueError("Embedding text cannot be empty.")

        if not isinstance(self.task, EmbeddingTask):
            raise TypeError("Invalid embedding task.")


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vector: tuple[float, ...]
    model: str
    provider: str
    dimensions: int

    def __post_init__(self):
        if not self.vector:
            raise ValueError("Embedding vector cannot be empty.")

        if len(self.vector) != self.dimensions:
            raise ValueError(
                "Vector length does not match declared dimensions."
            )

        if not self.model:
            raise ValueError("Model metadata is required.")

        if not self.provider:
            raise ValueError("Provider metadata is required.")