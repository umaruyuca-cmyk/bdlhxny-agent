from __future__ import annotations

import math
import unicodedata
from typing import Protocol


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


class ConservativeTokenCounter:
    """Deterministic fallback used when a model tokenizer is unavailable."""

    def count(self, text: str) -> int:
        if not text:
            return 0

        cjk_or_symbol = 0
        latin_or_number = 0
        for character in text:
            if character.isspace():
                continue
            name = unicodedata.name(character, "")
            if (
                "CJK" in name
                or "HIRAGANA" in name
                or "KATAKANA" in name
                or "HANGUL" in name
                or unicodedata.category(character).startswith("P")
            ):
                cjk_or_symbol += 1
            else:
                latin_or_number += 1

        return cjk_or_symbol + math.ceil(latin_or_number / 4)
