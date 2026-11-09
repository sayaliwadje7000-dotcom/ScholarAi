import pytest

from app.services.recommendations.exploration_allocator import (
    ExplorationAllocator,
)


@pytest.fixture
def allocator():
    return ExplorationAllocator()


def test_standard_allocation(allocator):
    result = allocator.allocate(
        total_candidates=10,
        exploration_ratio=0.8,
    )

    assert result.total_count == 10
    assert result.exploration_count == 8
    assert result.personalized_count == 2


def test_balanced_allocation(allocator):
    result = allocator.allocate(
        total_candidates=10,
        exploration_ratio=0.5,
    )

    assert result.exploration_count == 5
    assert result.personalized_count == 5


def test_zero_exploration(allocator):
    result = allocator.allocate(
        total_candidates=10,
        exploration_ratio=0.0,
    )

    assert result.exploration_count == 0
    assert result.personalized_count == 10


def test_full_exploration(allocator):
    result = allocator.allocate(
        total_candidates=10,
        exploration_ratio=1.0,
    )

    assert result.exploration_count == 10
    assert result.personalized_count == 0


def test_zero_candidate_pool(allocator):
    result = allocator.allocate(
        total_candidates=0,
        exploration_ratio=0.5,
    )

    assert result.total_count == 0
    assert result.exploration_count == 0
    assert result.personalized_count == 0


@pytest.mark.parametrize(
    "candidate_count",
    [-1, -10],
)
def test_negative_candidate_count_is_rejected(
    allocator,
    candidate_count,
):
    with pytest.raises(ValueError):
        allocator.allocate(
            total_candidates=candidate_count,
            exploration_ratio=0.5,
        )


@pytest.mark.parametrize(
    "candidate_count",
    [True, 1.5, "10"],
)
def test_invalid_candidate_count_type_is_rejected(
    allocator,
    candidate_count,
):
    with pytest.raises(TypeError):
        allocator.allocate(
            total_candidates=candidate_count,
            exploration_ratio=0.5,
        )


@pytest.mark.parametrize(
    "ratio",
    [-0.1, 1.1],
)
def test_out_of_range_exploration_ratio_is_rejected(
    allocator,
    ratio,
):
    with pytest.raises(ValueError):
        allocator.allocate(
            total_candidates=10,
            exploration_ratio=ratio,
        )


@pytest.mark.parametrize(
    "ratio",
    [True, "invalid", None],
)
def test_invalid_exploration_ratio_type_is_rejected(
    allocator,
    ratio,
):
    with pytest.raises(TypeError):
        allocator.allocate(
            total_candidates=10,
            exploration_ratio=ratio,
        )


def test_allocation_always_preserves_total_count(allocator):
    for total in range(0, 51):
        for ratio in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0):
            result = allocator.allocate(
                total_candidates=total,
                exploration_ratio=ratio,
            )

            assert (
                result.exploration_count
                + result.personalized_count
                == total
            )