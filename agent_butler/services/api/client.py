from __future__ import annotations

import os

import anthropic

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
CAPPED_DEFAULT_MAX_TOKENS = 8_000
ESCALATED_MAX_TOKENS = 64_000
COMPACT_MAX_OUTPUT_TOKENS = 20_000
MAX_OUTPUT_TOKENS_RECOVERY_LIMIT = 3
DEFAULT_MAX_TOKENS = CAPPED_DEFAULT_MAX_TOKENS

_client_instance: anthropic.Anthropic | None = None


def get_anthropic_client(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> anthropic.Anthropic:
    global _client_instance
    if _client_instance and api_key is None and base_url is None:
        return _client_instance

    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN"),
        base_url=base_url or os.environ.get("ANTHROPIC_BASE_URL"),
    )

    if api_key is None and base_url is None:
        _client_instance = client

    return client


async def verify_api_key(api_key: str | None = None) -> bool:
    try:
        client = get_anthropic_client(api_key=api_key) if api_key else get_anthropic_client()
        client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True
    except Exception:
        return False


def reset_client() -> None:
    global _client_instance
    _client_instance = None
