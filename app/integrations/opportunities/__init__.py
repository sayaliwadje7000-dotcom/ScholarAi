from app.integrations.opportunities.base import (
    BaseOpportunityProvider,
)

from app.integrations.opportunities.registry import (
    OpportunityProviderRegistry,
)

__all__ = [
    "BaseOpportunityProvider",
    "OpportunityProviderRegistry",
]