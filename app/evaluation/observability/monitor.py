import inspect
import time
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from app.evaluation.observability.collector import PerformanceCollector
from app.evaluation.observability.cost import estimate_cost_for_model
from app.evaluation.observability.schemas import (
    ModelPricing,
    PerformanceSample,
)


class PerformanceMonitor:
    def __init__(
        self,
        collector: PerformanceCollector,
        pricing_registry: Mapping[str, ModelPricing] | None = None,
    ):
        self.collector = collector
        self.pricing_registry = dict(pricing_registry or {})

    async def measure(
        self,
        operation_callable: Callable[..., Any],
        *,
        component: str,
        operation: str,
        model_name: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        started_at = datetime.now(timezone.utc)
        started = time.perf_counter()
        success = False

        try:
            result = operation_callable(**kwargs)

            if inspect.isawaitable(result):
                result = await result

            success = True
            return result

        finally:
            latency_ms = (time.perf_counter() - started) * 1000

            estimated_cost = None

            if model_name and model_name in self.pricing_registry:
                estimated_cost = estimate_cost_for_model(
                    model_name=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    pricing_registry=self.pricing_registry,
                )

            sample = PerformanceSample(
                sample_id=str(uuid.uuid4()),
                component=component,
                operation=operation,
                timestamp=started_at,
                latency_ms=latency_ms,
                success=success,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=estimated_cost,
                metadata=metadata or {},
            )

            self.collector.record(sample)
