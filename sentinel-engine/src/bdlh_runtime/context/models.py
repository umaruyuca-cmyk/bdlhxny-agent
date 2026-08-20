from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ContextClassification(StrEnum):
    REQUIRED = "required"
    COMPRESSIBLE = "compressible"
    REFERENCE_ONLY = "reference_only"
    DISTRACTOR = "distractor"


class ContextRole(StrEnum):
    SYSTEM = "system"
    INSTRUCTION = "instruction"
    USER_DATA = "user_data"
    TOOL_DEFINITION = "tool_definition"
    TOOL_RESULT = "tool_result"
    REFERENCE = "reference"
    UNTRUSTED_DATA = "untrusted_data"


class ContextStrategy(StrEnum):
    FULL = "full"
    RECENT_N = "recent-n"
    SINGLE_SUMMARY = "single-summary"
    BUDGETED = "budgeted"


class ContextAction(StrEnum):
    KEPT = "kept"
    COMPRESSED = "compressed"
    REFERENCED = "referenced"
    OMITTED = "omitted"
    ISOLATED = "isolated"


class ContextBudgetError(ValueError):
    def __init__(self, required_tokens: int, token_budget: int) -> None:
        self.required_tokens = required_tokens
        self.token_budget = token_budget
        super().__init__(
            f"required context needs {required_tokens} tokens, but the working-context budget is {token_budget}"
        )


class ContextWindowError(ValueError):
    def __init__(self, working_tokens: int, token_budget: int) -> None:
        self.working_tokens = working_tokens
        self.token_budget = token_budget
        super().__init__(f"working context needs {working_tokens} tokens, but the configured budget is {token_budget}")


@dataclass(frozen=True)
class ContextItem:
    item_id: str
    content: str
    classification: ContextClassification
    role: ContextRole = ContextRole.USER_DATA
    priority: int = 0
    source_id: str | None = None
    observed_at: str | None = None
    owner_id: str | None = None
    trusted: bool = True
    sequence: int = 0

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise ValueError("item_id must not be empty")
        if not self.content.strip():
            raise ValueError(f"context item {self.item_id!r} must not be empty")


@dataclass(frozen=True)
class ContextBuildRequest:
    items: tuple[ContextItem, ...]
    token_budget: int
    strategy: ContextStrategy = ContextStrategy.BUDGETED
    owner_id: str | None = None
    recent_n: int = 10
    compression_ratio: float = 0.35
    minimum_compressed_tokens: int = 32

    def __post_init__(self) -> None:
        if self.token_budget <= 0:
            raise ValueError("token_budget must be positive")
        if self.recent_n <= 0:
            raise ValueError("recent_n must be positive")
        if not 0 < self.compression_ratio <= 1:
            raise ValueError("compression_ratio must be in (0, 1]")
        if self.minimum_compressed_tokens <= 0:
            raise ValueError("minimum_compressed_tokens must be positive")
        item_ids = [item.item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("context item ids must be unique")


@dataclass(frozen=True)
class ContextDecision:
    item_id: str
    action: ContextAction
    reason: str
    input_tokens: int
    output_tokens: int
    source_id: str | None = None


@dataclass(frozen=True)
class ContextMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ContextReport:
    strategy: ContextStrategy
    token_budget: int
    original_tokens: int
    working_tokens: int
    required_item_ids: tuple[str, ...]
    retained_required_item_ids: tuple[str, ...]
    decisions: tuple[ContextDecision, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def required_retained(self) -> bool:
        return set(self.required_item_ids) == set(self.retained_required_item_ids)

    @property
    def budget_fit(self) -> bool:
        return self.working_tokens <= self.token_budget

    @property
    def counts(self) -> dict[str, int]:
        result = {action.value: 0 for action in ContextAction}
        for decision in self.decisions:
            result[decision.action.value] += 1
        return result


@dataclass(frozen=True)
class ContextBuildResult:
    messages: tuple[ContextMessage, ...]
    report: ContextReport
