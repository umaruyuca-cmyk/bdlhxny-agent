from __future__ import annotations

import math
import unicodedata
from typing import Protocol

#: 计数口径版本:CJK/标点每字 1 token,拉丁字母/数字每 4 字符 1 token。
#: 写入工件与上下文处理报告(tokenizer_version),保证口径可辨。
CONSERVATIVE_TOKENIZER_VERSION = "conservative-cjk1-latin4-v1"


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
