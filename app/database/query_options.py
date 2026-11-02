from sqlalchemy.orm import selectinload


def user_dashboard_options():
    """
    Load the main relationships needed for a user dashboard.
    """

    from app.models.user import User

    return (
        selectinload(User.preferences),
        selectinload(User.conversations),
        selectinload(User.documents),
        selectinload(User.learning_activities),
        selectinload(User.resource_interactions),
        selectinload(User.recommendations),
    )


def study_resource_options():
    """
    Load study resources with their related categories,
    interactions and recommendations.
    """

    from app.models.study_resource import StudyResource

    return (
        selectinload(StudyResource.categories),
        selectinload(StudyResource.user_interactions),
        selectinload(StudyResource.recommendations),
    )


def recommendation_options():
    """
    Load recommendations with their associated user,
    resource and feedback.
    """

    from app.models.recommendation import Recommendation

    return (
        selectinload(Recommendation.user),
        selectinload(Recommendation.resource),
        selectinload(Recommendation.feedback_entries),
    )