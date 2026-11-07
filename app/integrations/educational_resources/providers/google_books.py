from datetime import datetime

from app.integrations.educational_resources.base import (
    BaseResourceProvider,
)

from app.integrations.educational_resources.exceptions import (
    ResourceProviderValidationError,
)

from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResource,
    ExternalResourceType,
)


class GoogleBooksProvider(BaseResourceProvider):

    provider_name = "google_books"

    BASE_URL = (
        "https://www.googleapis.com/books/v1/volumes"
    )

    async def search(
        self,
        query: str,
        limit: int = 10,
        **filters,
    ) -> list[ExternalResource]:

        if not isinstance(query, str) or not query.strip():

            raise ResourceProviderValidationError(
                "Google Books search query cannot be empty."
            )

        limit = min(
            max(1, limit),
            self.settings.max_results_per_provider,
            40,
        )

        search_query = query.strip()

        if filters.get("subject"):

            search_query += (
                f"+subject:{filters['subject']}"
            )

        params = {
            "q": search_query,
            "maxResults": limit,
            "printType": "books",
        }

        if self.settings.google_books_api_key:

            params["key"] = (
                self.settings.google_books_api_key
            )

        if filters.get("language"):

            params["langRestrict"] = (
                filters["language"]
            )

        payload = await self._request_json(
            "GET",
            self.BASE_URL,
            params=params,
        )

        results = []

        for item in payload.get("items", []):

            if not isinstance(item, dict):
                continue

            resource = self.normalize(item)

            if resource is not None:
                results.append(resource)

        return results

    def normalize(self, payload):

        try:

            volume_id = payload.get("id")

            volume = payload.get(
                "volumeInfo",
                {},
            )

            title = volume.get("title")

            if not volume_id or not title:
                return None

            authors = tuple(
                dict.fromkeys(
                    volume.get("authors", [])
                )
            )

            published_at = None

            raw_date = volume.get(
                "publishedDate"
            )

            if raw_date:

                try:

                    if len(raw_date) == 4:

                        published_at = datetime.strptime(
                            raw_date,
                            "%Y",
                        )

                    elif len(raw_date) == 7:

                        published_at = datetime.strptime(
                            raw_date,
                            "%Y-%m",
                        )

                    else:

                        published_at = datetime.strptime(
                            raw_date[:10],
                            "%Y-%m-%d",
                        )

                except ValueError:
                    published_at = None

            access_info = payload.get(
                "accessInfo",
                {},
            )

            access_view_status = (
                access_info.get(
                    "accessViewStatus"
                )
            )

            access_type = ExternalAccessType.UNKNOWN

            if access_view_status == "FULL_PUBLIC_DOMAIN":

                access_type = (
                    ExternalAccessType.OPEN_ACCESS
                )

            elif access_view_status == "SAMPLE":

                access_type = (
                    ExternalAccessType.PREVIEW
                )

            elif access_view_status:

                access_type = (
                    ExternalAccessType.RESTRICTED
                )

            return ExternalResource(

                provider=self.provider_name,

                external_id=volume_id,

                title=title,

                description=volume.get(
                    "description"
                ),

                canonical_url=volume.get(
                    "infoLink",
                    f"https://books.google.com/books?id={volume_id}",
                ),

                resource_type=ExternalResourceType.BOOK,

                authors=authors,

                language=volume.get(
                    "language"
                ),

                published_at=published_at,

                access_type=access_type,

                metadata={
                    "publisher": volume.get(
                        "publisher"
                    ),
                    "page_count": volume.get(
                        "pageCount"
                    ),
                    "categories": volume.get(
                        "categories",
                        [],
                    ),
                    "industry_identifiers": volume.get(
                        "industryIdentifiers",
                        [],
                    ),
                    "preview_link": volume.get(
                        "previewLink"
                    ),
                    "web_reader_link": volume.get(
                        "webReaderLink"
                    ),
                    "access_view_status": (
                        access_view_status
                    ),
                    "sale_info": payload.get(
                        "saleInfo",
                        {},
                    ),
                },
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
        ):
            return None