class OpportunityRankingError(Exception):
    """Base exception for opportunity ranking."""


class OpportunityQualityError(OpportunityRankingError):
    """Raised when opportunity quality assessment fails."""


class OpportunityRelevanceError(OpportunityRankingError):
    """Raised when relevance scoring receives invalid input."""


class OpportunityRankingConfigurationError(OpportunityRankingError):
    """Raised when ranking configuration is invalid."""