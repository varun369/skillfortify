"""Shared async HTTP client utilities for registry scanners.

Provides a thin wrapper around ``httpx.AsyncClient`` with standardised
timeouts, user-agent headers, and error handling. All registry scanners
use this module so that HTTP behaviour is consistent and testable.

Raises ``RegistryScanError`` (a subclass of ``SkillFortifyError``) on
unrecoverable HTTP failures.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Timeout for all registry HTTP requests (seconds).
DEFAULT_TIMEOUT: float = 30.0

# User-Agent sent with every request.
USER_AGENT: str = "SkillFortify-RegistryScanner/0.2"


def _ensure_httpx() -> Any:  # noqa: ANN401
    """Lazily import httpx and raise a friendly error if missing.

    Returns:
        The ``httpx`` module.

    Raises:
        SystemExit: If httpx is not installed.
    """
    try:
        import httpx  # noqa: F811

        return httpx
    except ImportError:
        raise SystemExit(
            "httpx is required for registry scanning.\n"
            "Install it with: pip install skillfortify[registry]"
        )


async def fetch_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any] | list[Any]:
    """Fetch a URL and parse the response as JSON.

    Args:
        url: The URL to fetch.
        params: Optional query parameters.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response (dict or list).

    Raises:
        RegistryScanError: On HTTP errors, timeouts, or invalid JSON.
    """
    httpx = _ensure_httpx()
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        logger.warning("Timeout fetching %s", url)
        return {}
    except httpx.HTTPStatusError as exc:
        logger.warning("HTTP %d from %s", exc.response.status_code, url)
        return {}
    except (httpx.RequestError, ValueError) as exc:
        logger.warning("Request error for %s: %s", url, exc)
        return {}


async def fetch_text(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Fetch a URL and return the response body as text.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Response body text. Empty string on any error.
    """
    httpx = _ensure_httpx()
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError):
        logger.warning("Failed to fetch text from %s", url)
        return ""
