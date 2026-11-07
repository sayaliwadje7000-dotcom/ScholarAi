from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)


class OpportunityURLNormalizer:
    """Normalize opportunity URLs into canonical identities."""

    TRACKING_PARAMETERS = {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }

    @staticmethod
    def normalize(url: str) -> str | None:
        """
        Normalize a URL.

        Returns None for empty or invalid URLs.
        Removes tracking parameters and fragments.
        Sorts query parameters for consistent identity matching.
        """

        if not isinstance(url, str):
         raise TypeError("URL must be a string.")

        if not url.strip():
         return None

        try:
            parsed = urlsplit(url.strip())

            scheme = parsed.scheme.lower()

            if scheme not in {"http", "https"}:
                return None

            if not parsed.hostname:
                return None

            if parsed.username or parsed.password:
                return None

            hostname = parsed.hostname.lower()

            if hostname.startswith("www."):
                hostname = hostname[4:]

            port = parsed.port

            if port and not (
                (scheme == "http" and port == 80)
                or (scheme == "https" and port == 443)
            ):
                netloc = f"{hostname}:{port}"
            else:
                netloc = hostname

            query_parameters = parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )

            filtered_parameters = [
                (key, value)
                for key, value in query_parameters
                if key.casefold() not in (
                    OpportunityURLNormalizer.TRACKING_PARAMETERS
                )
                and not key.casefold().startswith("utm_")
            ]

            # Sort parameters to ensure equivalent URLs
            # produce identical normalized identities.
            sorted_parameters = sorted(
                filtered_parameters,
                key=lambda item: (
                    item[0].casefold(),
                    item[1],
                ),
            )

            normalized_query = urlencode(sorted_parameters)

            path = parsed.path.rstrip("/")

            return urlunsplit(
                (
                    scheme,
                    netloc,
                    path,
                    normalized_query,
                    "",
                )
            )

        except (ValueError, TypeError):
            return None