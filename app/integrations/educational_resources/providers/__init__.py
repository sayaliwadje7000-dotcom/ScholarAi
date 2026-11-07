from app.integrations.educational_resources.providers.youtube import (
    YouTubeProvider,
)

from app.integrations.educational_resources.providers.openalex import (
    OpenAlexProvider,
)

from app.integrations.educational_resources.providers.crossref import (
    CrossrefProvider,
)

from app.integrations.educational_resources.providers.google_books import (
    GoogleBooksProvider,
)


__all__ = [
    "YouTubeProvider",
    "OpenAlexProvider",
    "CrossrefProvider",
    "GoogleBooksProvider",
]