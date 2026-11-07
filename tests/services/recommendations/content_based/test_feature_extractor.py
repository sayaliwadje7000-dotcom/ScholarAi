import pytest

from app.schemas.resource_metadata import (
    ResourceClassification,
)

from app.services.recommendations.content_based import (
    ContentFeatureExtractor,
    ContentFeatureNormalizer,
)


@pytest.fixture
def extractor():
    return ContentFeatureExtractor()


@pytest.fixture
def sample_resource():
    return ResourceClassification(
        resource_id="resource-001",
        title="Machine Learning Fundamentals",
        resource_type="video",
        subject="Computer Science",
        difficulty="beginner",
        language="English",
        category_slugs=[
            "artificial-intelligence",
            "machine-learning",
        ],
        topics=[
            "Supervised Learning",
            "Unsupervised Learning",
        ],
        keywords=[
            "Python",
            "Neural Networks",
            "Data Science",
        ],
        learning_objectives=[
            "Understand machine learning concepts",
            "Build basic prediction models",
        ],
        prerequisites=[
            "Basic Python",
        ],
        content_format="video lecture",
    )


def test_extract_resource_features(
    extractor,
    sample_resource,
):
    result = extractor.extract(sample_resource)

    assert result.resource_id == "resource-001"
    assert result.title == "machine learning fundamentals"
    assert result.subject == "computer science"
    assert result.resource_type == "video"
    assert result.language == "english"
    assert "supervised learning" in result.topics
    assert "python" in result.keywords
    assert "basic python" in result.prerequisites


def test_feature_normalization_removes_duplicates(
    extractor,
):
    resource = ResourceClassification(
        resource_id="resource-002",
        title="Python Programming",
        resource_type="course",
        keywords=[
            "Python",
            "python",
            " PYTHON ",
            "Programming",
        ],
    )

    result = extractor.extract(resource)

    assert result.keywords == (
        "python",
        "programming",
    )


def test_missing_optional_features_are_empty(
    extractor,
):
    resource = ResourceClassification(
        resource_id="resource-003",
        title="Database Fundamentals",
        resource_type="article",
    )

    result = extractor.extract(resource)

    assert result.subject == ""
    assert result.description == ""
    assert result.topics == ()
    assert result.keywords == ()
    assert result.learning_objectives == ()
    assert result.prerequisites == ()
    assert result.has_content_features is True


def test_extractor_rejects_invalid_resource_type(
    extractor,
):
    with pytest.raises(TypeError):
        extractor.extract(
            [
                "resource-004",
                "Python",
                "course",
            ]
        )


def test_extractor_rejects_empty_title(
    extractor,
):
    with pytest.raises(ValueError):
        extractor.extract(
            {
                "resource_id": "resource-005",
                "title": "   ",
                "resource_type": "course",
            }
        )


def test_extractor_supports_mapping_input(
    extractor,
):
    resource = {
        "resource_id": "resource-009",
        "title": "Python Programming",
        "resource_type": "course",
        "subject": "Computer Science",
        "keywords": [
            "Python",
            "Programming",
        ],
    }

    result = extractor.extract(resource)

    assert result.resource_id == "resource-009"
    assert result.title == "python programming"
    assert result.subject == "computer science"
    assert result.keywords == (
        "python",
        "programming",
    )


def test_extractor_supports_optional_description(
    extractor,
):
    resource = {
        "resource_id": "resource-006",
        "title": "Neural Networks",
        "resource_type": "course",
        "description": (
            "  Introduction   to Deep Learning "
        ),
    }

    result = extractor.extract(resource)

    assert result.description == (
        "introduction to deep learning"
    )


def test_extracted_tokens_are_unique(
    extractor,
):
    resource = ResourceClassification(
        resource_id="resource-007",
        title="Python Programming",
        resource_type="course",
        subject="Python",
        keywords=[
            "Programming",
            "Python",
        ],
    )

    result = extractor.extract(resource)

    assert len(result.tokens) == len(
        set(result.tokens)
    )


def test_unicode_normalization():
    normalizer = ContentFeatureNormalizer()

    result = normalizer.normalize_text(
        "  ＰＹＴＨＯＮ   Programming  "
    )

    assert result == "python programming"


def test_normalizer_preserves_meaningful_negation():
    normalizer = ContentFeatureNormalizer()

    result = normalizer.tokenize(
        "Topics without prerequisites"
    )

    assert "without" in result
    assert "prerequisites" in result


def test_normalizer_rejects_non_string_values():
    normalizer = ContentFeatureNormalizer()

    with pytest.raises(TypeError):
        normalizer.normalize_terms(
            ["Python", 123]
        )


def test_normalizer_preserves_first_occurrence():
    normalizer = ContentFeatureNormalizer()

    result = normalizer.normalize_terms(
        [
            "Machine Learning",
            "PYTHON",
            "machine learning",
            "Data Science",
        ]
    )

    assert result == (
        "machine learning",
        "python",
        "data science",
    )


def test_feature_count():
    extractor = ContentFeatureExtractor()

    resource = ResourceClassification(
        resource_id="resource-008",
        title="Operating Systems",
        resource_type="notes",
        subject="Computer Science",
        topics=["Process Management"],
    )

    result = extractor.extract(resource)

    assert result.feature_count == 4