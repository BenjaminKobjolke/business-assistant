"""Health checks for external service dependencies."""

from __future__ import annotations

import logging
import urllib.request

from business_assistant.config.constants import OLLAMA_HEALTH_RESPONSE

logger = logging.getLogger(__name__)


def check_ollama_health(base_url: str, timeout: float = 5.0) -> bool:
    """Check if the Ollama server is reachable.

    Derives the root URL from the OpenAI-compatible base_url (strips /v1 suffix)
    and sends a GET request. Ollama responds with "Ollama is running" at its root.
    """
    root_url = base_url.rstrip("/")
    if root_url.endswith("/v1"):
        root_url = root_url[:-3]

    try:
        req = urllib.request.Request(root_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return OLLAMA_HEALTH_RESPONSE in body
    except Exception:
        logger.debug("Ollama health check error", exc_info=True)
        return False
