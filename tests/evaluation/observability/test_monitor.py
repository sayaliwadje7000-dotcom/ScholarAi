import pytest

from app.evaluation.observability.collector import PerformanceCollector
from app.evaluation.observability.monitor import PerformanceMonitor
from app.evaluation.observability.schemas import ModelPricing


@pytest.mark.asyncio
async def test_monitor_async_operation():
    collector = PerformanceCollector()
    monitor = PerformanceMonitor(collector)

    async def operation(value):
        return value * 2

    result = await monitor.measure(
        operation,
        component="llm",
        operation="generate",
        value=5,
    )

    assert result == 10

    samples = collector.get_samples()

    assert len(samples) == 1
    assert samples[0].success is True
    assert samples[0].latency_ms >= 0


@pytest.mark.asyncio
async def test_monitor_sync_operation():
    collector = PerformanceCollector()
    monitor = PerformanceMonitor(collector)

    def operation(value):
        return value + 1

    result = await monitor.measure(
        operation,
        component="retrieval",
        operation="search",
        value=5,
    )

    assert result == 6
    assert collector.get_samples()[0].success is True


@pytest.mark.asyncio
async def test_monitor_records_failed_operation():
    collector = PerformanceCollector()
    monitor = PerformanceMonitor(collector)

    async def failing_operation():
        raise RuntimeError("Operation failed")

    with pytest.raises(RuntimeError):
        await monitor.measure(
            failing_operation,
            component="llm",
            operation="generate",
        )

    samples = collector.get_samples()

    assert len(samples) == 1
    assert samples[0].success is False


@pytest.mark.asyncio
async def test_monitor_records_token_usage_and_cost():
    collector = PerformanceCollector()

    pricing = {
        "test-model": ModelPricing(
            model_name="test-model",
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.02,
        )
    }

    monitor = PerformanceMonitor(
        collector,
        pricing_registry=pricing,
    )

    async def operation():
        return "Generated response"

    await monitor.measure(
        operation,
        component="llm",
        operation="generate",
        model_name="test-model",
        input_tokens=1000,
        output_tokens=500,
    )

    sample = collector.get_samples()[0]

    assert sample.input_tokens == 1000
    assert sample.output_tokens == 500
    assert sample.estimated_cost_usd == pytest.approx(0.02)


@pytest.mark.asyncio
async def test_monitor_records_metadata():
    collector = PerformanceCollector()
    monitor = PerformanceMonitor(collector)

    async def operation():
        return True

    await monitor.measure(
        operation,
        component="rag",
        operation="retrieve",
        metadata={"source": "benchmark"},
    )

    assert (
        collector.get_samples()[0].metadata["source"]
        == "benchmark"
    )
