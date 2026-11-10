import pytest

from app.evaluation.observability.collector import PerformanceCollector
from app.evaluation.observability.schemas import PerformanceSample


def make_sample(
    sample_id="sample-1",
    component="rag",
    operation="retrieve",
):
    return PerformanceSample(
        sample_id=sample_id,
        component=component,
        operation=operation,
        latency_ms=120,
        success=True,
    )


def test_record_and_retrieve_sample():
    collector = PerformanceCollector()
    sample = make_sample()

    collector.record(sample)

    assert collector.get_samples() == [sample]
    assert len(collector) == 1


def test_reject_duplicate_sample_ids():
    collector = PerformanceCollector()

    collector.record(make_sample())

    with pytest.raises(ValueError):
        collector.record(make_sample())


def test_filter_by_component():
    collector = PerformanceCollector()

    collector.record(make_sample("1", "rag", "retrieve"))
    collector.record(make_sample("2", "llm", "generate"))

    results = collector.get_by_component("rag")

    assert len(results) == 1
    assert results[0].component == "rag"


def test_filter_by_operation():
    collector = PerformanceCollector()

    collector.record(make_sample("1", "rag", "retrieve"))
    collector.record(make_sample("2", "rag", "rerank"))

    results = collector.get_by_operation("retrieve")

    assert len(results) == 1
    assert results[0].operation == "retrieve"


def test_clear_collector():
    collector = PerformanceCollector()
    collector.record(make_sample())

    collector.clear()

    assert len(collector) == 0
    assert collector.get_samples() == []


def test_returned_sample_list_is_independent():
    collector = PerformanceCollector()
    collector.record(make_sample())

    results = collector.get_samples()
    results.clear()

    assert len(collector) == 1
