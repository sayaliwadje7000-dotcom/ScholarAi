from __future__ import annotations

from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)


class ResourceURLNormalizationError(ValueError):
    """Raised when a resource URL cannot be normalized."""


class ResourceURLNormalizer:
    """Canonicalize HTTP and HTTPS resource URLs."""

    TRACKING_PARAMETERS = {
        "fbclid",
        "gclid",
        "dclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_src",
    }

    @classmethod
    def normalize(cls, url: str | None) -> str | None:
        if url is None:
            return None

        if not isinstance(url, str):
            raise TypeError("URL must be a string or None.")

        url = url.strip()

        if not url:
            return None

        try:
            parsed = urlsplit(url)

            scheme = parsed.scheme.lower()

            if scheme not in {"http", "https"}:
                raise ResourceURLNormalizationError(
                    "Only HTTP and HTTPS URLs are supported."
                )

            if not parsed.hostname:
                raise ResourceURLNormalizationError(
                    "URL must contain a hostname."
                )

            if parsed.username is not None or parsed.password is not None:
                raise ResourceURLNormalizationError(
                    "URLs containing credentials are not allowed."
                )

            hostname = parsed.hostname.lower().rstrip(".")

            if not hostname:
                raise ResourceURLNormalizationError(
                    "URL hostname cannot be empty."
                )

            try:
                port = parsed.port
            except ValueError as exc:
                raise ResourceURLNormalizationError(
                    "URL contains an invalid port."
                ) from exc

            if ":" in hostname and not hostname.startswith("["):
                hostname = f"[{hostname}]"

            if port is not None:
                if not (
                    (scheme == "http" and port == 80)
                    or (scheme == "https" and port == 443)
                ):
                    netloc = f"{hostname}:{port}"
                else:
                    netloc = hostname
            else:
                netloc = hostname

            path = parsed.path or "/"

            while "//" in path:
                path = path.replace("//", "/")

            if path != "/":
                path = path.rstrip("/")

            query_parameters = parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )

            filtered_parameters = []

            for key, value in query_parameters:
                lowered_key = key.lower()

                if lowered_key.startswith("utm_"):
                    continue

                if lowered_key in cls.TRACKING_PARAMETERS:
                    continue

                filtered_parameters.append((key, value))

            filtered_parameters.sort(
                key=lambda item: (item[0].casefold(), item[1])
            )

            query = urlencode(filtered_parameters, doseq=True)

            return urlunsplit(
                (
                    scheme,
                    netloc,
                    path,
                    query,
                    "",
                )
            )

        except ResourceURLNormalizationError:
            raise

        except Exception as exc:
            raise ResourceURLNormalizationError(
                "Unable to normalize resource URL."
            ) from exc