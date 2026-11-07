from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)

from app.schemas.opportunities.discovery import (
    OpportunityDiscoveryRequest,
)

from app.schemas.opportunities.api import (
    OpportunityCategoriesResponse,
    OpportunityDiscoveryAPIRequest,
    OpportunityDiscoveryAPIResponse,
    OpportunityProviderFailureResponse,
    OpportunityRankedItemResponse,
)

from app.services.opportunities.discovery_service import (
    OpportunityDiscoveryService,
)

from app.services.opportunities.discovery_exceptions import (
    OpportunityDiscoveryConfigurationError,
    OpportunityDiscoveryUnavailableError,
    OpportunityDiscoveryValidationError,
    OpportunityDiscoveryResponseError,
)

from app.services.opportunities.normalization.deduplication_service import (
    OpportunityDeduplicationService,
)

from app.services.opportunities.ranking.ranking_service import (
    OpportunityRankingService,
)


router = APIRouter()


OPPORTUNITY_CATEGORIES = [
    "hackathon",
    "internship",
    "competition",
    "workshop",
    "conference",
    "academic_event",
    "scholarship",
    "other",
]


# ============================================================
# SERVICE CONSTRUCTION
# ============================================================

def get_opportunity_registry(request: Request):

    registry = getattr(
        request.app.state,
        "opportunity_provider_registry",
        None,
    )

    if registry is None:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Opportunity provider registry is unavailable.",
        )

    return registry


def build_opportunity_services(registry):

    discovery_service = OpportunityDiscoveryService(
        registry=registry,
        max_concurrent_providers=4,
    )

    deduplication_service = (
        OpportunityDeduplicationService()
    )

    ranking_service = OpportunityRankingService()

    return (
        discovery_service,
        deduplication_service,
        ranking_service,
    )


# ============================================================
# SERIALIZATION
# ============================================================

def _serialize_opportunity(value: Any) -> dict:

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if hasattr(value, "__dict__"):
        return dict(vars(value))

    raise TypeError(
        "Unsupported opportunity response object."
    )


def _serialize_ranked_item(item):

    validity = item.validity

    return OpportunityRankedItemResponse(
        opportunity=_serialize_opportunity(
            item.opportunity
        ),

        quality_score=item.quality.score,

        relevance_score=item.relevance.score,

        final_score=item.final_score,

        rank=item.rank,

        eligibility_status=(
            validity.eligibility.status
        ),

        deadline_status=(
            validity.deadline.status
        ),

        freshness_status=(
            validity.freshness.status
        ),

        requires_refresh=(
            validity.requires_refresh
        ),

        explanations=list(
            item.explanations
        ),
    )


# ============================================================
# DISCOVERY ENDPOINT
# ============================================================

@router.post(
    "/discover",
    response_model=OpportunityDiscoveryAPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover and recommend opportunities",
    description=(
        "Search configured opportunity providers, "
        "normalize and deduplicate results, evaluate "
        "validity, and rank opportunities."
    ),
)
async def discover_opportunities(
    payload: OpportunityDiscoveryAPIRequest,
    request: Request,
):

    registry = get_opportunity_registry(request)

    (
        discovery_service,
        deduplication_service,
        ranking_service,
    ) = build_opportunity_services(registry)

    # --------------------------------------------------------
    # STEP 1: BUILD INTERNAL DISCOVERY REQUEST
    # --------------------------------------------------------

    discovery_request = OpportunityDiscoveryRequest(
        query=payload.query,
        providers=payload.providers,
        opportunity_types=payload.opportunity_types,
        location=payload.location,
        is_remote=payload.is_remote,
        limit_per_provider=payload.limit_per_provider,
        max_results=payload.max_results,
    )

    # --------------------------------------------------------
    # STEP 2: DISCOVER OPPORTUNITIES
    # --------------------------------------------------------

    try:

        discovery_result = await discovery_service.discover(
            discovery_request
        )

    except OpportunityDiscoveryUnavailableError:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Opportunity discovery is currently unavailable.",
        )

    except OpportunityDiscoveryConfigurationError:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Opportunity provider configuration is invalid.",
        )

    except OpportunityDiscoveryValidationError as exc:

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except OpportunityDiscoveryResponseError:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An opportunity provider returned an invalid response.",
        )

    # --------------------------------------------------------
    # STEP 3: NORMALIZE AND DEDUPLICATE
    # --------------------------------------------------------

    try:

        unique_opportunities = (
            deduplication_service.deduplicate(
                discovery_result.opportunities
            )
        )

    except (TypeError, ValueError):

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Opportunity normalization failed.",
        )

    # --------------------------------------------------------
    # STEP 4: PREPARE STUDENT PROFILE
    # --------------------------------------------------------

    student_profile = {}

    if payload.student_profile is not None:

        student_profile = (
            payload.student_profile.model_dump(
                exclude_none=True
            )
        )

    # --------------------------------------------------------
    # STEP 5: VALIDITY + QUALITY + RELEVANCE + RANKING
    # --------------------------------------------------------

    try:

        ranking_result = ranking_service.rank(
            opportunities=unique_opportunities,
            student_profile=student_profile,
            query=payload.query,
            limit=payload.ranking_limit,
            now=datetime.now(timezone.utc),
        )

    except (TypeError, ValueError):

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Opportunity ranking could not be completed.",
        )

    # --------------------------------------------------------
    # STEP 6: SERIALIZE RANKED RESULTS
    # --------------------------------------------------------

    ranked_items = [
        _serialize_ranked_item(item)
        for item in ranking_result.ranked_opportunities
    ]

    # --------------------------------------------------------
    # STEP 7: BUILD RESPONSE
    # --------------------------------------------------------

    provider_failures = [
        OpportunityProviderFailureResponse(
            provider=failure.provider,
            error_type=failure.error_type,
            message=failure.message,
        )
        for failure in discovery_result.provider_failures
    ]

    return OpportunityDiscoveryAPIResponse(
        query=payload.query,

        total_received=(
            ranking_result.total_received
        ),

        total_ranked=(
            ranking_result.total_ranked
        ),

        total_excluded=(
            ranking_result.total_excluded
        ),

        exclusion_reasons=(
            ranking_result.exclusion_reasons
        ),

        providers_requested=(
            discovery_result.providers_requested
        ),

        providers_searched=(
            discovery_result.providers_searched
        ),

        providers_failed=(
            discovery_result.providers_failed
        ),

        provider_failures=provider_failures,

        opportunities=ranked_items,

        retrieved_at=discovery_result.retrieved_at,
    )


# ============================================================
# OPPORTUNITY CATEGORIES
# ============================================================

@router.get(
    "/categories",
    response_model=OpportunityCategoriesResponse,
    summary="Get available opportunity categories",
)
async def get_opportunity_categories():

    return OpportunityCategoriesResponse(
        categories=OPPORTUNITY_CATEGORIES
    )