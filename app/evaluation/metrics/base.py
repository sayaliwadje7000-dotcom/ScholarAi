from dataclasses import dataclass, field
from typing import Any
import math


@dataclass(frozen=True)
class MetricResult:
    name: str
    value: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Metric name must be a non-empty string.")

        if isinstance(self.value, bool):
            raise ValueError("Metric value must be numeric.")

        if not isinstance(self.value, (int, float)):
            raise ValueError("Metric value must be numeric.")

        if not math.isfinite(self.value):
            raise ValueError("Metric value must be finite.")

        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary.")