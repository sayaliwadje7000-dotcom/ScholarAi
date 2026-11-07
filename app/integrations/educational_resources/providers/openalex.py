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


class OpenAlexProvider(BaseResourceProvider):

    provider_name = "openalex"

    BASE_URL = "https://api.openalex.org/works"

    async def search(
        self,
        query: str,
        limit: int = 10,
        **filters,
    ) -> list[ExternalResource]:

        if not isinstance(query, str) or not query.strip():

            raise ResourceProviderValidationError(
                "OpenAlex search query cannot be empty."
            )

        limit = min(
            max(1, limit),
            self.settings.max_results_per_provider,
            100,
        )

        params = {
            "search": query.strip(),
            "per-page": limit,
        }

        if self.settings.openalex_api_key:

            params["api_key"] = (
                self.settings.openalex_api_key
            )

        publication_year = filters.get(
            "publication_year"
        )

        if publication_year:

            params["filter"] = (
                f"publication_year:{publication_year}"
            )

        if self.settings.crossref_mailto:
            params["mailto"] = self.settings.crossref_mailto

        payload = await self._request_json(
            "GET",
            self.BASE_URL,
            params=params,
        )

        results = []

        for item in payload.get("results", []):

            if not isinstance(item, dict):
                continue

            resource = self.normalize(item)

            if resource is not None:
                results.append(resource)

        return results

    def normalize(self, payload):

        try:

            work_id = payload.get("id")

            title = payload.get("title")

            if not work_id or not title:
                return None

            doi = payload.get("doi")

            canonical_url = (
                doi
                if doi and doi.startswith("https://")
                else work_id
            )

            authors = []

            for authorship in payload.get(
                "authorships",
                [],
            ):

                author = (
                    authorship.get("author", {})
                )

                name = author.get("display_name")

                if name:
                    authors.append(name)

            publication_date = None

            raw_date = payload.get(
                "publication_date"
            )

            if raw_date:

                publication_date = datetime.strptime(
                    raw_date,
                    "%Y-%m-%d",
                )

            locations = payload.get(
                "locations",
                [],
            )

            open_access = payload.get(
                "open_access",
                {},
            )

            access_type = ExternalAccessType.UNKNOWN

            if open_access.get("is_oa"):

                access_type = (
                    ExternalAccessType.OPEN_ACCESS
                )

            best_oa_location = (
                payload.get(
                    "best_oa_location"
                ) or {}
            )

            license_value = (
                best_oa_location.get("license")
            )

            primary_location = (
                payload.get(
                    "primary_location"
                ) or {}
            )

            landing_page = (
                primary_location.get(
                    "landing_page_url"
                )
            )

            return ExternalResource(

                provider=self.provider_name,

                external_id=work_id,

                title=title,

                description=payload.get(
                    "abstract"
                ),

                canonical_url=canonical_url,

                resource_type=ExternalResourceType.ARTICLE,

                authors=tuple(dict.fromkeys(authors)),

                published_at=publication_date,

                license=license_value,

                access_type=access_type,

                metadata={
                    "doi": doi,
                    "publication_year": payload.get(
                        "publication_year"
                    ),
                    "type": payload.get("type"),
                    "cited_by_count": payload.get(
                        "cited_by_count"
                    ),
                    "open_access": open_access,
                    "open_access_locations": locations,
                    "landing_page_url": landing_page,
                    "primary_topic": payload.get(
                        "primary_topic"
                    ),
                },
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
        ):
            return None