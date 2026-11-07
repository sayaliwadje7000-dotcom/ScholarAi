from uuid import uuid4
from types import SimpleNamespace

import pytest

from app.services.embeddings.resource_content import (
    ResourceContentBuilder,
)


@pytest.fixture
def resource():
    return SimpleNamespace(
        id=uuid4(),
        title="Machine Learning Fundamentals",
        description="Introduction to machine learning.",
        resource_type="course",
        provider="Example University",
        subject="Artificial Intelligence",
        language="English",
        difficulty_level="beginner",
        resource_metadata={
            "topics": [
                "Regression",
                "Classification",
            ],
            "keywords": [
                "Machine Learning",
                "Artificial Intelligence",
            ],
            "learning_objectives": [
                "Understand supervised learning",
            ],
            "prerequisites": [
                "Basic Python",
            ],
            "content_format": "video",
        },
        categories=[
            SimpleNamespace(slug="machine-learning"),
        ],
    )


def test_build_resource_content(resource):

    builder = ResourceContentBuilder()

    result = builder.build(resource)

    assert result.resource_id == resource.id
    assert "Machine Learning Fundamentals" in result.text
    assert "Regression" in result.text
    assert "Basic Python" in result.text
    assert len(result.content_hash) == 64


def test_content_hash_is_deterministic(resource):

    builder = ResourceContentBuilder()

    first = builder.build(resource)
    second = builder.build(resource)

    assert first.content_hash == second.content_hash


def test_content_hash_changes_when_description_changes(resource):

    builder = ResourceContentBuilder()

    first = builder.build(resource)

    resource.description = "Advanced deep learning course."

    second = builder.build(resource)

    assert first.content_hash != second.content_hash


def test_empty_title_is_rejected(resource):

    builder = ResourceContentBuilder()

    resource.title = "   "

    with pytest.raises(ValueError):
        builder.build(resource)


def test_invalid_metadata_is_rejected(resource):

    builder = ResourceContentBuilder()

    resource.resource_metadata = "invalid"

    with pytest.raises(TypeError):
        builder.build(resource)


def test_duplicate_topics_are_removed(resource):

    builder = ResourceContentBuilder()

    resource.resource_metadata["topics"] = [
        "Python",
        "python",
        "Machine Learning",
    ]

    result = builder.build(resource)

    topics_section = next(
        line
        for line in result.text.splitlines()
        if line.startswith("Topics:")
    )

    assert topics_section == "Topics: Python, Machine Learning"