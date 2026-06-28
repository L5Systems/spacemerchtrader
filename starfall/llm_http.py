"""Shared HTTP client settings for OpenAI-compatible LLM API calls."""

from __future__ import annotations

import httpx

from starfall.config import settings


def llm_verify_option() -> bool | str:
    """SSL verification target for httpx (certifi bundle, or disabled in dev)."""
    if not settings.launch_broker_llm_verify_ssl:
        return False
    try:
        import certifi

        return certifi.where()
    except ImportError:
        return True


def llm_http_client(**kwargs) -> httpx.Client:
    return httpx.Client(verify=llm_verify_option(), **kwargs)
