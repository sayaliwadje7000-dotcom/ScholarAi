from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user_preferences import UserPreferences
from app.models.document import Document
from app.models.learning_activity import LearningActivity
from app.models.study_resource import StudyResource
from app.models.resource_category import ResourceCategory
from app.models.study_resource_category import study_resource_categories
from app.models.user_resource_interaction import UserResourceInteraction
from app.models.recommendation import Recommendation
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.document_chunk import DocumentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.models.resource_embedding import ResourceEmbedding
__all__ = [
    "User",
    "Conversation",
    "Message",
    "UserPreferences",
    "Document",
    "LearningActivity",
    "StudyResource",
    "ResourceCategory",
    "study_resource_categories",
    "UserResourceInteraction",
    "Recommendation",
    "RecommendationFeedback",
    "DocumentChunk",
    "ChunkEmbedding",
]