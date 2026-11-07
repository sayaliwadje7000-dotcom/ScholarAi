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


class CrossrefProvider(BaseResourceProvider):

    provider_name = "crossref"

    BASE_URL = "https://api.crossref.org/works"

    async def search(
        self,
        query: str,
        limit: int = 10,
        **filters,
    ) -> list[ExternalResource]:

        if not isinstance(query, str) or not query.strip():

            raise ResourceProviderValidationError(
                "Crossref search query cannot be empty."
            )

        limit = min(
            max(1, limit),
            self.settings.max_results_per_provider,
            1000,
        )

        params = {
            "query": query.strip(),
            "rows": limit,
        }

        if self.settings.crossref_mailto:

            params["mailto"] = (
                self.settings.crossref_mailto
            )

        if filters.get("from_date"):

            params["filter"] = (
                "from-pub-date:"
                f"{filters['from_date']}"
            )

        payload = await self._request_json(
            "GET",
            self.BASE_URL,
            params=params,
        )

        message = payload.get("message", {})

        results = []

        for item in message.get("items", []):

            if not isinstance(item, dict):
                continue

            resource = self.normalize(item)

            if resource is not None:
                results.append(resource)

        return results

    def normalize(self, payload):

        try:

            doi = payload.get("DOI")

            title_list = payload.get("title", [])

            title = (
                title_list[0]
                if title_list
                else None
            )

            if not doi or not title:
                return None

            authors = []

            for author in payload.get(
                "author",
                [],
            ):

                given = author.get("given", "")
                family = author.get("family", "")

                full_name = (
                    f"{given} {family}"
                ).strip()

                if full_name:
                    authors.append(full_name)

            published_at = None

            date_parts = (
                payload.get(
                    "published",
                    {},
                )
                .get("date-parts", [])
            )

            if date_parts and date_parts[0]:

                parts = date_parts[0]

                year = parts[0]
                month = parts[1] if len(parts) > 1 else 1
                day = parts[2] if len(parts) > 2 else 1

                published_at = datetime(
                    year,
                    month,
                    day,
                )

            abstract = payload.get("abstract")

            publisher = payload.get("publisher")

            resource_type = (
                ExternalResourceType.ARTICLE
            )

            return ExternalResource(

                provider=self.provider_name,

                external_id=doi,

                title=title,

                description=abstract,

                canonical_url=(
                    f"https://doi.org/{doi}"
                ),

                resource_type=resource_type,

                authors=tuple(dict.fromkeys(authors)),

                published_at=published_at,

                access_type=ExternalAccessType.UNKNOWN,

                metadata={
                    "publisher": publisher,
                    "container_title": payload.get(
                        "container-title"
                    ),
                    "type": payload.get("type"),
                    "volume": payload.get("volume"),
                    "issue": payload.get("issue"),
                    "page": payload.get("page"),
                    "issn": payload.get("ISSN"),
                    "isbn": payload.get("ISBN"),
                    "subject": payload.get("subject", []),
                    "license": payload.get("license", []),
                    "link": payload.get("link", []),
                },
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
            IndexError,
        ):
            return None