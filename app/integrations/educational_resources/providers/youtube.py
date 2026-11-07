from datetime import datetime, timezone
from typing import Any

from app.integrations.educational_resources.base import (
    BaseResourceProvider,
)
from app.integrations.educational_resources.exceptions import (
    ResourceProviderConfigurationError,
    ResourceProviderValidationError,
)
from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResource,
    ExternalResourceType,
)

class YouTubeProvider(BaseResourceProvider):
    """
    Educational video discovery provider using YouTube Data API v3.

    Responsibilities:
    - Search for educational videos.
    - Normalize YouTube API responses.
    - Preserve video and channel metadata.
    - Return standardized ExternalResource objects.
    """

    provider_name = "youtube"

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    SEARCH_ENDPOINT = f"{BASE_URL}/search"

    def __init__(self, client, settings):
        if not settings.youtube_api_key:
            raise ResourceProviderConfigurationError(
                "YouTube API key is required."
            )

        super().__init__(
            client=client,
            settings=settings,
        )

    async def search(
        self,
        query: str,
        limit: int = 10,
        **filters: Any,
    ) -> list[ExternalResource]:
        """
        Search YouTube for educational videos.

        Supported optional filters:
        - relevance_language
        - video_duration
        - published_after
        - published_before
        - order
        """

        if not isinstance(query, str) or not query.strip():
            raise ResourceProviderValidationError(
                "Search query must be a non-empty string."
            )

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ResourceProviderValidationError(
                "Result limit must be an integer."
            )

        if limit < 1:
            raise ResourceProviderValidationError(
                "Result limit must be at least 1."
            )

        max_results = min(
            limit,
            self.settings.max_results_per_provider,
            50,
        )

        params = {
            "part": "snippet",
            "type": "video",
            "q": query.strip(),
            "maxResults": max_results,
            "key": self.settings.youtube_api_key,
        }

        allowed_filters = {
            "relevanceLanguage": "relevance_language",
            "videoDuration": "video_duration",
            "publishedAfter": "published_after",
            "publishedBefore": "published_before",
            "order": "order",
        }

        for api_parameter, filter_name in allowed_filters.items():
            value = filters.get(filter_name)

            if value is not None:
                params[api_parameter] = value

        payload = await self._request_json(
            "GET",
            self.SEARCH_ENDPOINT,
            params=params,
        )

        items = payload.get("items", [])

        if not isinstance(items, list):
            raise ResourceProviderValidationError(
                "YouTube API returned an invalid items collection."
            )

        resources = []

        for item in items:
            resource = self.normalize(item)

            if resource is not None:
                resources.append(resource)

        return resources

    def normalize(
        self,
        payload: dict[str, Any],
    ) -> ExternalResource | None:
        """
        Convert one YouTube search result into ExternalResource.
        """

        if not isinstance(payload, dict):
            return None

        video_id_data = payload.get("id", {})

        if not isinstance(video_id_data, dict):
            return None

        video_id = video_id_data.get("videoId")

        if not isinstance(video_id, str) or not video_id.strip():
            return None

        snippet = payload.get("snippet", {})

        if not isinstance(snippet, dict):
            return None

        title = snippet.get("title")

        if not isinstance(title, str) or not title.strip():
            return None

        description = snippet.get("description")

        if not isinstance(description, str):
            description = ""

        channel_title = snippet.get("channelTitle")
        channel_id = snippet.get("channelId")

        authors = (
            (channel_title.strip(),)
            if isinstance(channel_title, str) and channel_title.strip()
            else ()
        )

        published_at = self._parse_datetime(
            snippet.get("publishedAt")
        )

        thumbnails = snippet.get("thumbnails", {})

        if not isinstance(thumbnails, dict):
            thumbnails = {}

        thumbnail_url = None

        for quality in ("high", "medium", "default"):
            thumbnail = thumbnails.get(quality)

            if isinstance(thumbnail, dict):
                url = thumbnail.get("url")

                if isinstance(url, str):
                    thumbnail_url = url
                    break

        metadata = {
            "video_id": video_id,
            "channel_id": channel_id,
            "channel_title": channel_title,
            "thumbnail_url": thumbnail_url,
            "live_broadcast_content": snippet.get(
                "liveBroadcastContent"
            ),
        }

        return ExternalResource(
            provider=self.provider_name,
            external_id=video_id,
            title=title.strip(),
            canonical_url=(
                f"https://www.youtube.com/watch?v={video_id}"
            ),
            resource_type=ExternalResourceType.VIDEO,
            description=description.strip(),
            authors=authors,
            subject=None,
            language=snippet.get("defaultLanguage")
            or snippet.get("defaultAudioLanguage"),
            published_at=published_at,
            retrieved_at=datetime.now(timezone.utc),
            license=None,
            access_type=ExternalAccessType.PUBLIC,
            metadata=metadata,
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None

        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed

        except ValueError:
            return None