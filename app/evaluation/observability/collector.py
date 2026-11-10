from threading import RLock

from app.evaluation.observability.schemas import PerformanceSample


class PerformanceCollector:
    def __init__(self):
        self._samples: list[PerformanceSample] = []
        self._lock = RLock()

    def record(self, sample: PerformanceSample) -> None:
        with self._lock:
            if any(
                existing.sample_id == sample.sample_id
                for existing in self._samples
            ):
                raise ValueError(
                    f"Duplicate performance sample ID: {sample.sample_id}"
                )

            self._samples.append(sample)

    def get_samples(self) -> list[PerformanceSample]:
        with self._lock:
            return list(self._samples)

    def get_by_component(
        self,
        component: str,
    ) -> list[PerformanceSample]:
        with self._lock:
            return [
                sample
                for sample in self._samples
                if sample.component == component
            ]

    def get_by_operation(
        self,
        operation: str,
    ) -> list[PerformanceSample]:
        with self._lock:
            return [
                sample
                for sample in self._samples
                if sample.operation == operation
            ]

    def clear(self) -> None:
        with self._lock:
            self._samples.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._samples)
