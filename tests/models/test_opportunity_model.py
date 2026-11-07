import uuid

from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.opportunity import Opportunity


def test_opportunity_table_name():

    assert Opportunity.__tablename__ == "opportunities"


def test_opportunity_primary_key():

    column = Opportunity.__table__.columns["id"]

    assert column.primary_key is True
    assert isinstance(column.type, UUID)


def test_opportunity_default_values():

    opportunity = Opportunity(
        provider="adzuna",
        title="Software Engineering Internship",
    )

    assert isinstance(opportunity.id, uuid.UUID)
    assert opportunity.opportunity_type == "other"
    assert opportunity.status == "discovered"
    assert opportunity.verification_status == "unverified"
    assert opportunity.required_skills == []
    assert opportunity.opportunity_metadata == {}


def test_opportunity_initialization():

    opportunity = Opportunity(
        provider="adzuna",
        external_id="12345",
        title="Python Internship",
        description="Python development internship.",
        opportunity_type="internship",
        organizer="Example Organization",
        official_url="https://example.com",
        source_url="https://example.com/source",
        application_url="https://example.com/apply",
        eligibility="Undergraduate students",
        required_skills=["Python", "SQL"],
        location="Pune",
        is_remote=True,
        status="open",
        verification_status="official_verified",
        opportunity_metadata={
            "source": "adzuna",
        },
    )

    assert opportunity.provider == "adzuna"
    assert opportunity.external_id == "12345"
    assert opportunity.title == "Python Internship"
    assert opportunity.opportunity_type == "internship"
    assert opportunity.required_skills == ["Python", "SQL"]
    assert opportunity.is_remote is True
    assert opportunity.opportunity_metadata["source"] == "adzuna"


def test_opportunity_metadata_database_column():

    column = Opportunity.__table__.columns["metadata"]

    assert isinstance(column.type, JSONB)


def test_opportunity_skills_database_column():

    column = Opportunity.__table__.columns["required_skills"]

    assert isinstance(column.type, JSONB)


def test_opportunity_external_identity_constraint():

    constraints = {
        constraint.name
        for constraint in Opportunity.__table__.constraints
    }

    assert (
        "uq_opportunities_provider_external_id"
        in constraints
    )


def test_opportunity_indexes():

    indexes = {
        index.name
        for index in Opportunity.__table__.indexes
    }

    assert "ix_opportunities_provider" in indexes

    assert "ix_opportunities_type" in indexes

    assert "ix_opportunities_status" in indexes

    assert "ix_opportunities_registration_deadline" in indexes

    assert "ix_opportunities_event_start" in indexes

    assert "ix_opportunities_type_status_deadline" in indexes


def test_opportunity_python_metadata_attribute_does_not_override_base_metadata():

    assert hasattr(Opportunity, "metadata")
    assert isinstance(
        Opportunity.opportunity_metadata.property.columns[0].type,
        JSONB,
    )