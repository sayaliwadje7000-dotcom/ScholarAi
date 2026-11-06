from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.resource_metadata import ResourceMetadata
from app.services.recommendations.resource_classifier import (
    ResourceClassifier,
)


@pytest.fixture
def classifier():
    return ResourceClassifier()


@pytest.fixture
def sample_resource():
    category = SimpleNamespace(
        slug="data-structures"
    )

    return SimpleNamespace(
        id=uuid4(),
        title="Introduction to Binary Trees",
        resource_type="video",
        is_active=True,
        subject="Data Structures",
        difficulty="beginner",
        language="English",
        quality_score=Decimal("4.500"),
        estimated_duration_minutes=25,
        published_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        categories=[category],
        recommendation_metadata={
            "topics": [
                "Binary Trees",
                "Tree Traversal",
                "binary trees",
            ],
            "keywords": [
                "BST",
                "Nodes",
                "Traversal",
            ],
            "learning_objectives": [
                "Understand binary tree structures",
                "Perform tree traversal",
            ],
            "prerequisites": [
                "Basic knowledge of linked lists",
            ],
            "content_format": "video",
            "source_language": "English",
            "estimated_reading_minutes": 15,
            "is_beginner_friendly": True,
        },
    )


def test_resource_metadata_defaults():
    metadata = ResourceMetadata()

    assert metadata.topics == []
    assert metadata.keywords == []
    assert metadata.prerequisites == []
    assert metadata.learning_objectives == []


def test_resource_metadata_normalizes_lists():
    metadata = ResourceMetadata(
        topics=[
            " Binary Trees ",
            "binary trees",
            "Tree Traversal",
            "",
        ]
    )

    assert metadata.topics == [
        "Binary Trees",
        "Tree Traversal",
    ]


def test_resource_metadata_accepts_single_string():
    metadata = ResourceMetadata(
        topics="Binary Trees"
    )

    assert metadata.topics == ["Binary Trees"]


def test_resource_metadata_rejects_invalid_list_values():
    with pytest.raises(ValueError):
        ResourceMetadata(
            topics=["Binary Trees", 123]
        )


def test_resource_metadata_rejects_invalid_reading_duration():
    with pytest.raises(ValueError):
        ResourceMetadata(
            estimated_reading_minutes=0
        )


def test_classifier_returns_resource_classification(
    classifier,
    sample_resource,
):
    result = classifier.classify(sample_resource)

    assert result.resource_id == str(sample_resource.id)
    assert result.title == "Introduction to Binary Trees"
    assert result.resource_type == "video"
    assert result.subject == "Data Structures"
    assert result.difficulty == "beginner"
    assert result.language == "english"
    assert result.is_active is True


def test_classifier_extracts_category_slugs(
    classifier,
    sample_resource,
):
    result = classifier.classify(sample_resource)

    assert result.category_slugs == [
        "data-structures"
    ]


def test_classifier_extracts_topics(
    classifier,
    sample_resource,
):
    result = classifier.classify(sample_resource)

    assert result.topics == [
        "Binary Trees",
        "Tree Traversal",
    ]


def test_classifier_extracts_keywords(
    classifier,
    sample_resource,
):
    result = classifier.classify(sample_resource)

    assert result.keywords == [
        "BST",
        "Nodes",
        "Traversal",
    ]


def test_classifier_extracts_learning_objectives(
    classifier,
    sample_resource,
):
    result = classifier.classify(sample_resource)

    assert len(result.learning_objectives) == 2


def test_classifier_extracts_prerequisites(
    classifier,
    sample_resource,
):
    result = classifier.classify(sample_resource)

    assert result.prerequisites == [
        "Basic knowledge of linked lists"
    ]


def test_classifier_extracts_duration_and_quality(
    classifier,
    sample_resource,
):
    result = classifier.classify(sample_resource)

    assert result.estimated_duration_minutes == 25
    assert result.estimated_reading_minutes == 15
    assert result.quality_score == 4.5


def test_classifier_handles_missing_metadata(classifier):
    resource = SimpleNamespace(
        id=uuid4(),
        title="Introduction to Python",
        resource_type="article",
        is_active=True,
        subject="Programming",
        difficulty="beginner",
        language="English",
        quality_score=None,
        estimated_duration_minutes=None,
        published_at=None,
        categories=[],
        recommendation_metadata=None,
    )

    result = classifier.classify(resource)

    assert result.topics == []
    assert result.keywords == []
    assert result.prerequisites == []
    assert result.learning_objectives == []
    assert result.quality_score is None
    assert result.is_active is True


def test_classifier_does_not_invent_missing_subject(classifier):
    resource = SimpleNamespace(
        id=uuid4(),
        title="Introduction to Algorithms",
        resource_type="article",
        is_active=True,
        subject=None,
        difficulty=None,
        language=None,
        quality_score=None,
        estimated_duration_minutes=None,
        published_at=None,
        categories=[],
        recommendation_metadata={},
    )

    result = classifier.classify(resource)

    assert result.subject is None
    assert result.difficulty is None
    assert result.language is None
    assert result.prerequisites == []
    assert result.is_active is True


def test_classifier_rejects_missing_resource_id(classifier):
    resource = SimpleNamespace(
        title="Introduction to Python",
        resource_type="article",
        recommendation_metadata={},
    )

    with pytest.raises(ValueError, match="Resource ID"):
        classifier.classify(resource)


def test_classifier_rejects_missing_title(classifier):
    resource = SimpleNamespace(
        id=uuid4(),
        title=" ",
        resource_type="article",
        recommendation_metadata={},
    )

    with pytest.raises(ValueError, match="Resource title"):
        classifier.classify(resource)


def test_classifier_rejects_missing_resource_type(classifier):
    resource = SimpleNamespace(
        id=uuid4(),
        title="Introduction to Python",
        resource_type=None,
        recommendation_metadata={},
    )

    with pytest.raises(ValueError, match="Resource type"):
        classifier.classify(resource)


def test_classifier_rejects_non_dictionary_metadata(classifier):
    resource = SimpleNamespace(
        id=uuid4(),
        title="Introduction to Python",
        resource_type="article",
        recommendation_metadata="invalid",
    )

    with pytest.raises(ValueError, match="dictionary-like"):
        classifier.classify(resource)


def test_classifier_rejects_invalid_standardized_metadata(classifier):
    resource = SimpleNamespace(
        id=uuid4(),
        title="Introduction to Python",
        resource_type="article",
        recommendation_metadata={
            "estimated_reading_minutes": -10,
        },
    )

    with pytest.raises(ValueError, match="invalid standardized metadata"):
        classifier.classify(resource)