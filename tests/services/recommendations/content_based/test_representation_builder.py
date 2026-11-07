import pytest

from app.services.recommendations.content_based import (
    ContentFeatureExtractor,
    ResourceRepresentationBuilder,
)


@pytest.fixture
def extractor():
    return ContentFeatureExtractor()


@pytest.fixture
def builder():
    return ResourceRepresentationBuilder()


@pytest.fixture
def extracted_features(extractor):
    resource = {
        "resource_id": "resource-101",
        "title": "Introduction to Machine Learning",
        "description": (
            "Learn supervised learning, "
            "unsupervised learning, and model evaluation."
        ),
        "subject": "Artificial Intelligence",
        "resource_type": "course",
        "category_slugs": [
            "machine-learning",
            "artificial-intelligence",
        ],
        "topics": [
            "Regression",
            "Classification",
            "Clustering",
        ],
        "keywords": [
            "machine learning",
            "neural networks",
            "model training",
        ],
        "learning_objectives": [
            "Understand regression algorithms",
            "Evaluate classification models",
        ],
        "prerequisites": [
            "Basic Python",
            "Statistics",
        ],
        "content_format": "video course",
        "language": "english",
        "difficulty": "intermediate",
    }

    return extractor.extract(resource)


def test_builder_creates_resource_representation(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    assert representation.resource_id == "resource-101"

    assert (
        representation.title
        == "introduction to machine learning"
    )

    assert representation.resource_type == "course"

    assert representation.has_semantic_content is True

    assert representation.section_count > 0

    assert representation.token_count > 0

    assert len(representation.content_hash) == 64


def test_builder_creates_expected_sections(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    section_names = {
        section.name
        for section in representation.sections
    }

    expected_sections = {
        "title",
        "description",
        "subject",
        "resource_type",
        "categories",
        "topics",
        "keywords",
        "learning_objectives",
        "prerequisites",
        "content_format",
    }

    assert section_names == expected_sections


def test_builder_preserves_section_weights(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    title_section = representation.get_section("title")

    objective_section = representation.get_section(
        "learning_objectives"
    )

    assert title_section is not None
    assert objective_section is not None

    assert title_section.weight == 3.0
    assert objective_section.weight == 3.0


def test_builder_generates_embedding_text(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    assert "Title:" in representation.embedding_text

    assert "Description:" in representation.embedding_text

    assert "Topics:" in representation.embedding_text

    assert (
        "Learning Objectives:"
        in representation.embedding_text
    )


def test_embedding_text_preserves_semantic_labels(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    assert (
        "Topics: regression; classification; clustering"
        in representation.embedding_text
    )


def test_builder_generates_deterministic_hash(
    builder,
    extracted_features,
):
    first = builder.build(extracted_features)

    second = builder.build(extracted_features)

    assert first.content_hash == second.content_hash


def test_content_hash_changes_when_content_changes(
    extractor,
    builder,
):
    first_resource = {
        "resource_id": "resource-102",
        "title": "Python Programming",
        "resource_type": "course",
        "topics": ["Variables", "Functions"],
    }

    second_resource = {
        "resource_id": "resource-102",
        "title": "Python Programming",
        "resource_type": "course",
        "topics": ["Variables", "Object Oriented Programming"],
    }

    first = builder.build(
        extractor.extract(first_resource)
    )

    second = builder.build(
        extractor.extract(second_resource)
    )

    assert first.content_hash != second.content_hash


def test_builder_rejects_invalid_input(builder):
    with pytest.raises(TypeError):
        builder.build({"title": "Invalid input"})


def test_builder_rejects_resource_without_content(
    builder,
):
    from app.services.recommendations.content_based.feature_extractor import (
        ExtractedContentFeatures,
    )

    features = ExtractedContentFeatures(
        resource_id="resource-103",
        title="",
        description="",
        subject="",
        resource_type="",
        category_slugs=(),
        topics=(),
        keywords=(),
        learning_objectives=(),
        prerequisites=(),
        content_format="",
        language="",
        difficulty="",
        tokens=(),
    )

    with pytest.raises(ValueError):
        builder.build(features)


def test_builder_does_not_duplicate_text_to_apply_weights(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    title_section = representation.get_section("title")

    assert title_section is not None

    assert representation.embedding_text.count(
        title_section.text
    ) == 1


def test_builder_preserves_language_and_difficulty(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    assert representation.language == "english"

    assert representation.difficulty == "intermediate"


def test_representation_is_immutable(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    with pytest.raises(AttributeError):
        representation.title = "Modified title"


def test_get_section_is_case_insensitive(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    section = representation.get_section("TOPICS")

    assert section is not None

    assert section.name == "topics"


def test_representation_exposes_counts(
    builder,
    extracted_features,
):
    representation = builder.build(extracted_features)

    assert representation.section_count == len(
        representation.sections
    )

    assert representation.token_count == len(
        representation.tokens
    )

    assert representation.feature_count == (
        extracted_features.feature_count
    )