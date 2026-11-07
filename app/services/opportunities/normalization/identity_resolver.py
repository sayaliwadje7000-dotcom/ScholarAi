from app.services.opportunities.normalization.text_normalizer import (
    OpportunityTextNormalizer,
)

from app.services.opportunities.normalization.url_normalizer import (
    OpportunityURLNormalizer,
)


class OpportunityIdentityResolver:
    """
    Resolves stable identities for opportunities.

    Identity priority:
    1. Official URL.
    2. Provider + external ID.
    3. Semantic identity using title, organizer,
       opportunity type and event year.
    """

    @staticmethod
    def resolve(opportunity: dict) -> str:

        if not isinstance(opportunity, dict):
            raise TypeError("Opportunity must be a dictionary.")

        # 1. Official URL identity
        official_url = opportunity.get("official_url")

        if official_url is not None and not isinstance(
            official_url, str
        ):
            raise TypeError("Official URL must be a string or None.")

        normalized_url = (
            OpportunityURLNormalizer.normalize(official_url)
            if isinstance(official_url, str) and official_url.strip()
            else None
        )

        if normalized_url:
            return f"url:{normalized_url}"

        # 2. Provider + external ID identity
        provider = opportunity.get("provider")
        external_id = opportunity.get("external_id")

        if provider is not None and not isinstance(provider, str):
            raise TypeError("Provider must be a string or None.")

        if external_id is not None and not isinstance(
            external_id, str
        ):
            raise TypeError("External ID must be a string or None.")

        if (
            isinstance(provider, str)
            and provider.strip()
            and isinstance(external_id, str)
            and external_id.strip()
        ):
            return (
                f"provider:{provider.strip().casefold()}:"
                f"{external_id.strip().casefold()}"
            )

        # 3. Semantic identity fallback
        title = opportunity.get("title")
        organizer = opportunity.get("organizer")
        opportunity_type = opportunity.get("opportunity_type")

        if not isinstance(title, str) or not title.strip():
            raise ValueError(
                "Opportunity title is required for semantic identity."
            )

        if not isinstance(organizer, str) or not organizer.strip():
            raise ValueError(
                "Opportunity organizer is required for semantic identity."
            )

        if (
            not isinstance(opportunity_type, str)
            or not opportunity_type.strip()
        ):
            raise ValueError(
                "Opportunity type is required for semantic identity."
            )

        normalized_title = OpportunityTextNormalizer.normalize(title)
        normalized_organizer = OpportunityTextNormalizer.normalize(
            organizer
        )
        normalized_type = OpportunityTextNormalizer.normalize(
            opportunity_type
        )

        event_start = opportunity.get("event_start")

        event_year = (
            event_start.year
            if event_start is not None
            else "unknown"
        )

        return (
            f"semantic:{normalized_title}:"
            f"{normalized_organizer}:"
            f"{normalized_type}:"
            f"{event_year}"
        )
    