"""Shared plumbing for the AI-Initiatives projects.

Import from here rather than re-creating clients in every script:

    from aicore import complete, stream_text, settings
"""

from aicore.config import settings
from aicore.cost import SpendLimitExceeded, ledger
from aicore.llm import LLMResult, complete, count_tokens, stream_text

__all__ = [
    "LLMResult",
    "SpendLimitExceeded",
    "complete",
    "count_tokens",
    "ledger",
    "settings",
    "stream_text",
]
