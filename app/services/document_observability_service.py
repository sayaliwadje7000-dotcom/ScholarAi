import logging
import threading
import time

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


logger = logging.getLogger("scholarai.document.observability")


@dataclass
class StageMetric:
    executions: int = 0
    total_duration_seconds: float = 0.0
    maximum_duration_seconds: float = 0.0
    failures: int = 0


@dataclass
class DocumentProcessingMetrics:

    processing_started: int = 0
    processing_completed: int = 0
    processing_failed: int = 0

    stage_metrics: dict[str, StageMetric] = field(
        default_factory=dict
    )


class DocumentObservability:

    """
    Thread-safe in-process document processing metrics.

    This collector is intentionally process-local.

    It is suitable for operational diagnostics during
    development and single-process execution.

    It is not a replacement for distributed metrics
    storage or Prometheus.
    """

    def __init__(self):

        self._lock = threading.RLock()

        self._metrics = DocumentProcessingMetrics()

    def record_processing_started(
        self,
        document_id: str,
        attempt: int,
    ) -> None:

        with self._lock:

            self._metrics.processing_started += 1

        logger.info(
            "document_processing_started",
            extra={
                "event": "document_processing_started",
                "document_id": document_id,
                "attempt": attempt,
            },
        )

    def record_processing_completed(
        self,
        document_id: str,
        duration_seconds: float,
        page_count: int,
        attempt: int,
    ) -> None:

        with self._lock:

            self._metrics.processing_completed += 1

        logger.info(
            "document_processing_completed",
            extra={
                "event": "document_processing_completed",
                "document_id": document_id,
                "duration_seconds": round(
                    duration_seconds,
                    3,
                ),
                "page_count": page_count,
                "attempt": attempt,
            },
        )

    def record_processing_failed(
        self,
        document_id: str,
        stage: str,
        error_type: str,
        attempt: int,
    ) -> None:

        with self._lock:

            self._metrics.processing_failed += 1

            metric = self._metrics.stage_metrics.get(
                stage
            )

            if metric is None:

                metric = StageMetric()

                self._metrics.stage_metrics[stage] = metric

            metric.failures += 1

        logger.error(
            "document_processing_failed",
            extra={
                "event": "document_processing_failed",
                "document_id": document_id,
                "stage": stage,
                "error_type": error_type,
                "attempt": attempt,
            },
        )

    def record_stage(
        self,
        stage: str,
        duration_seconds: float,
        failed: bool = False,
    ) -> None:

        with self._lock:

            metric = self._metrics.stage_metrics.get(
                stage
            )

            if metric is None:

                metric = StageMetric()

                self._metrics.stage_metrics[stage] = metric

            metric.executions += 1

            metric.total_duration_seconds += (
                duration_seconds
            )

            metric.maximum_duration_seconds = max(
                metric.maximum_duration_seconds,
                duration_seconds,
            )

            if failed:
                metric.failures += 1

    def snapshot(self) -> dict:

        with self._lock:

            return {
                "processing": {
                    "started": self._metrics.processing_started,
                    "completed": self._metrics.processing_completed,
                    "failed": self._metrics.processing_failed,
                },

                "stages": {
                    name: {
                        "executions": metric.executions,
                        "failures": metric.failures,
                        "total_duration_seconds": round(
                            metric.total_duration_seconds,
                            3,
                        ),
                        "average_duration_seconds": round(
                            metric.total_duration_seconds
                            / metric.executions,
                            3,
                        ) if metric.executions else 0.0,
                        "maximum_duration_seconds": round(
                            metric.maximum_duration_seconds,
                            3,
                        ),
                    }

                    for name, metric
                    in self._metrics.stage_metrics.items()
                },
            }

    def reset(self) -> None:

        with self._lock:

            self._metrics = DocumentProcessingMetrics()


document_observability = DocumentObservability()


@contextmanager
def observe_processing_stage(
    document_id: str,
    stage: str,
) -> Iterator[None]:

    """
    Measure the execution time of a processing stage.

    Stage failures are recorded before the original
    exception is propagated.
    """

    started_at = time.perf_counter()

    failed = False

    try:

        yield

    except Exception:

        failed = True

        raise

    finally:

        duration = time.perf_counter() - started_at

        document_observability.record_stage(
            stage=stage,
            duration_seconds=duration,
            failed=failed,
        )

        logger.info(
            "document_processing_stage_finished",
            extra={
                "event": "document_processing_stage_finished",
                "document_id": document_id,
                "stage": stage,
                "duration_seconds": round(
                    duration,
                    3,
                ),
                "failed": failed,
            },
        )