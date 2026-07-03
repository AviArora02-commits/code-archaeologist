"""Text extraction and cleanup for Cognee recall results."""

from __future__ import annotations

import ast
import re
from typing import Any

_DICT_RE = re.compile(r"^\s*\{.*\}\s*$", re.DOTALL)


def extract_answer_text(result: Any) -> str:
    """Pull human-readable answer text from a Cognee recall item."""
    if result is None:
        return ""

    if isinstance(result, str):
        return _clean_text(_maybe_unwrap_dict_string(result))

    if isinstance(result, dict):
        for key in ("text", "raw", "answer", "content"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return _clean_text(val)
        return ""

    for attr in ("text", "raw", "answer", "content"):
        val = getattr(result, attr, None)
        if isinstance(val, str) and val.strip():
            return _clean_text(val)

    raw = str(result)
    return _clean_text(_maybe_unwrap_dict_string(raw))


def _maybe_unwrap_dict_string(raw: str) -> str:
    """Handle answers that are str(dict) from cloud recall."""
    if not _DICT_RE.match(raw):
        return raw
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, dict):
            for key in ("text", "raw", "answer"):
                val = parsed.get(key)
                if isinstance(val, str) and val.strip():
                    return val
    except (SyntaxError, ValueError):
        pass
    return raw


def _clean_text(text: str) -> str:
    text = text.replace("\\n", "\n").replace("\\t", "\t")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
