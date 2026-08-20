from __future__ import annotations

import json
import re
from typing import Protocol

from .models import ContextItem
from .token_count import TokenCounter


class ContextCompressor(Protocol):
    def compress(self, item: ContextItem, max_tokens: int, counter: TokenCounter) -> str: ...


class StructuredTextCompressor:
    """Deterministic compression with explicit omission and source markers."""

    _blank_lines = re.compile(r"\n\s*\n+")
    _spaces = re.compile(r"[ \t]+")

    def compress(self, item: ContextItem, max_tokens: int, counter: TokenCounter) -> str:
        if max_tokens <= 0:
            return ""

        normalized = self._normalize(item.content)
        compact_json = self._compact_json(normalized)
        if compact_json is not None:
            normalized = compact_json

        if counter.count(normalized) <= max_tokens:
            return normalized

        source = item.source_id or item.item_id
        marker = f"[compressed source={source}]"
        if counter.count(marker) >= max_tokens:
            return self._fit(marker, max_tokens, counter)

        available = max_tokens - counter.count(marker)
        head_size = max(1, int(len(normalized) * 0.6))
        tail_size = max(1, int(len(normalized) * 0.25))
        candidate = f"{marker}\n{normalized[:head_size]}\n[content omitted]\n{normalized[-tail_size:]}"

        while counter.count(candidate) > max_tokens and (head_size > 1 or tail_size > 1):
            if head_size >= tail_size and head_size > 1:
                head_size = max(1, int(head_size * 0.8))
            elif tail_size > 1:
                tail_size = max(1, int(tail_size * 0.8))
            candidate = f"{marker}\n{normalized[:head_size]}\n[content omitted]\n{normalized[-tail_size:]}"

        if counter.count(candidate) <= max_tokens:
            return candidate

        return self._fit(f"{marker}\n{normalized}", max_tokens, counter, available)

    def _normalize(self, content: str) -> str:
        paragraphs = []
        seen = set()
        for paragraph in self._blank_lines.split(content.strip()):
            cleaned = self._spaces.sub(" ", paragraph).strip()
            if cleaned and cleaned not in seen:
                paragraphs.append(cleaned)
                seen.add(cleaned)
        return "\n\n".join(paragraphs)

    @staticmethod
    def _compact_json(content: str) -> str | None:
        if not content.startswith(("{", "[")):
            return None
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            return None
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _fit(text: str, max_tokens: int, counter: TokenCounter, initial_size: int | None = None) -> str:
        if counter.count(text) <= max_tokens:
            return text
        low = 0
        high = min(len(text), initial_size or len(text))
        while low < high:
            middle = (low + high + 1) // 2
            if counter.count(text[:middle]) <= max_tokens:
                low = middle
            else:
                high = middle - 1
        return text[:low]
