from __future__ import annotations

from collections.abc import Iterable

from .compression import ContextCompressor, StructuredTextCompressor
from .models import (
    ContextAction,
    ContextBudgetError,
    ContextBuildRequest,
    ContextBuildResult,
    ContextClassification,
    ContextDecision,
    ContextItem,
    ContextMessage,
    ContextReport,
    ContextRole,
    ContextStrategy,
    ContextWindowError,
)
from .token_count import ConservativeTokenCounter, TokenCounter


class ContextBuilder:
    def __init__(
        self,
        counter: TokenCounter | None = None,
        compressor: ContextCompressor | None = None,
    ) -> None:
        self._counter = counter or ConservativeTokenCounter()
        self._compressor = compressor or StructuredTextCompressor()

    def build(self, request: ContextBuildRequest) -> ContextBuildResult:
        eligible, isolated = self._separate_owner_data(request)
        original_tokens = sum(self._counter.count(self._render(item, item.content)) for item in request.items)

        if request.strategy is ContextStrategy.FULL:
            selected, decisions = self._build_full(eligible, request.token_budget)
        elif request.strategy is ContextStrategy.RECENT_N:
            selected, decisions = self._build_recent(eligible, request)
        elif request.strategy is ContextStrategy.SINGLE_SUMMARY:
            selected, decisions = self._build_single_summary(eligible, request)
        else:
            selected, decisions = self._build_budgeted(eligible, request)

        decisions.extend(isolated)
        messages = self._to_messages(selected)
        working_tokens = sum(self._counter.count(message.content) for message in messages)
        if working_tokens > request.token_budget:
            raise ContextWindowError(working_tokens, request.token_budget)
        required_ids = tuple(
            item.item_id for item in request.items if item.classification is ContextClassification.REQUIRED
        )
        retained_required_ids = tuple(
            decision.item_id
            for decision in decisions
            if decision.item_id in required_ids
            and decision.action in {ContextAction.KEPT, ContextAction.COMPRESSED, ContextAction.REFERENCED}
        )
        warnings = []
        if set(required_ids) != set(retained_required_ids):
            warnings.append("one or more required context items were not retained")
        if working_tokens > request.token_budget:
            warnings.append("working context exceeds the configured token budget")

        report = ContextReport(
            strategy=request.strategy,
            token_budget=request.token_budget,
            original_tokens=original_tokens,
            working_tokens=working_tokens,
            required_item_ids=required_ids,
            retained_required_item_ids=retained_required_ids,
            decisions=tuple(decisions),
            warnings=tuple(warnings),
        )
        return ContextBuildResult(messages=messages, report=report)

    def _separate_owner_data(self, request: ContextBuildRequest) -> tuple[list[ContextItem], list[ContextDecision]]:
        eligible = []
        isolated = []
        for item in request.items:
            if request.owner_id and item.owner_id and item.owner_id != request.owner_id:
                input_tokens = self._counter.count(self._render(item, item.content))
                isolated.append(
                    ContextDecision(
                        item_id=item.item_id,
                        action=ContextAction.ISOLATED,
                        reason="item belongs to a different user scope",
                        input_tokens=input_tokens,
                        output_tokens=0,
                        source_id=item.source_id,
                    )
                )
                continue
            eligible.append(item)
        return eligible, isolated

    def _build_full(
        self, items: list[ContextItem], token_budget: int
    ) -> tuple[list[tuple[ContextItem, str]], list[ContextDecision]]:
        selected = [(item, self._render(item, item.content)) for item in self._ordered(items)]
        total = sum(self._counter.count(rendered) for _, rendered in selected)
        if total > token_budget:
            raise ContextWindowError(total, token_budget)
        decisions = [self._decision(item, ContextAction.KEPT, "full strategy", rendered) for item, rendered in selected]
        return selected, decisions

    def _build_recent(
        self, items: list[ContextItem], request: ContextBuildRequest
    ) -> tuple[list[tuple[ContextItem, str]], list[ContextDecision]]:
        ordered = self._ordered(items)
        recent_ids = {item.item_id for item in ordered[-request.recent_n :]}
        selected = []
        decisions = []
        remaining = request.token_budget
        for item in ordered:
            rendered = self._render(item, item.content)
            tokens = self._counter.count(rendered)
            if item.item_id in recent_ids and tokens <= remaining:
                selected.append((item, rendered))
                remaining -= tokens
                decisions.append(self._decision(item, ContextAction.KEPT, "within recent-n window", rendered))
            else:
                reason = "outside recent-n window" if item.item_id not in recent_ids else "token budget exhausted"
                decisions.append(self._decision(item, ContextAction.OMITTED, reason, ""))
        return selected, decisions

    def _build_single_summary(
        self, items: list[ContextItem], request: ContextBuildRequest
    ) -> tuple[list[tuple[ContextItem, str]], list[ContextDecision]]:
        required = [item for item in items if item.classification is ContextClassification.REQUIRED]
        optional = [item for item in items if item.classification is not ContextClassification.REQUIRED]
        selected, decisions, remaining = self._keep_required(required, request.token_budget)

        if optional and remaining > 0:
            combined_item = ContextItem(
                item_id="single-summary",
                content="\n\n".join(self._render(item, item.content) for item in self._ordered(optional)),
                classification=ContextClassification.COMPRESSIBLE,
                role=ContextRole.USER_DATA,
                priority=max(item.priority for item in optional),
                source_id=",".join(filter(None, (item.source_id for item in optional))) or None,
            )
            header_tokens = self._counter.count(self._render(combined_item, ""))
            summary_budget = max(0, remaining - header_tokens)
            summary = self._compressor.compress(combined_item, summary_budget, self._counter)
            rendered = self._render(combined_item, summary)
            summary_kept = False
            if summary and self._counter.count(rendered) <= remaining:
                selected.append((combined_item, rendered))
                summary_kept = True
        else:
            summary_kept = False

        for item in optional:
            decisions.append(
                self._decision(
                    item,
                    ContextAction.COMPRESSED if summary_kept else ContextAction.OMITTED,
                    "represented by single-summary"
                    if summary_kept
                    else "single summary could not fit the remaining budget",
                    "",
                )
            )
        return selected, decisions

    def _build_budgeted(
        self, items: list[ContextItem], request: ContextBuildRequest
    ) -> tuple[list[tuple[ContextItem, str]], list[ContextDecision]]:
        required = [item for item in items if item.classification is ContextClassification.REQUIRED]
        selected, decisions, remaining = self._keep_required(required, request.token_budget)

        candidates = [
            item
            for item in items
            if item.classification
            in {
                ContextClassification.COMPRESSIBLE,
                ContextClassification.REFERENCE_ONLY,
            }
        ]
        candidates.sort(key=lambda item: (-item.priority, item.sequence, item.item_id))

        for index, item in enumerate(candidates):
            original_rendered = self._render(item, item.content)
            original_tokens = self._counter.count(original_rendered)
            if remaining <= 0:
                decisions.append(self._decision(item, ContextAction.OMITTED, "token budget exhausted", ""))
                continue

            if item.classification is ContextClassification.REFERENCE_ONLY:
                value = self._reference(item, original_tokens)
                action = ContextAction.REFERENCED
                reason = "reference-only item represented by source metadata"
            else:
                remaining_candidates = max(1, len(candidates) - index)
                fair_share = max(request.minimum_compressed_tokens, remaining // remaining_candidates)
                header_tokens = self._counter.count(self._render(item, ""))
                target = min(
                    original_tokens,
                    max(request.minimum_compressed_tokens, int(original_tokens * request.compression_ratio)),
                    max(0, fair_share - header_tokens),
                )
                value = self._compressor.compress(item, target, self._counter)
                action = ContextAction.KEPT if value == item.content else ContextAction.COMPRESSED
                reason = "fits budget without compression" if action is ContextAction.KEPT else "compressed to budget"

            rendered = self._render(item, value)
            tokens = self._counter.count(rendered)
            if value and tokens <= remaining:
                selected.append((item, rendered))
                remaining -= tokens
                decisions.append(self._decision(item, action, reason, rendered))
            else:
                decisions.append(self._decision(item, ContextAction.OMITTED, "item does not fit remaining budget", ""))

        for item in items:
            if item.classification is ContextClassification.DISTRACTOR:
                decisions.append(
                    self._decision(
                        item,
                        ContextAction.ISOLATED,
                        "distractor excluded from budgeted working context",
                        "",
                    )
                )

        selected.sort(key=lambda pair: (pair[0].sequence, pair[0].item_id))
        return selected, decisions

    def _keep_required(
        self, required: list[ContextItem], token_budget: int
    ) -> tuple[list[tuple[ContextItem, str]], list[ContextDecision], int]:
        selected = []
        decisions = []
        required_tokens = 0
        for item in self._ordered(required):
            rendered = self._render(item, item.content)
            required_tokens += self._counter.count(rendered)
            selected.append((item, rendered))
            decisions.append(self._decision(item, ContextAction.KEPT, "required item", rendered))
        if required_tokens > token_budget:
            raise ContextBudgetError(required_tokens, token_budget)
        return selected, decisions, token_budget - required_tokens

    def _decision(
        self,
        item: ContextItem,
        action: ContextAction,
        reason: str,
        output: str,
    ) -> ContextDecision:
        return ContextDecision(
            item_id=item.item_id,
            action=action,
            reason=reason,
            input_tokens=self._counter.count(self._render(item, item.content)),
            output_tokens=self._counter.count(output),
            source_id=item.source_id,
        )

    def _render(self, item: ContextItem, content: str) -> str:
        source = f" source={item.source_id}" if item.source_id else ""
        header = f"[context item={item.item_id} type={item.classification.value}{source}]"
        body = f"{header}\n{content}"
        if not item.trusted or item.role is ContextRole.UNTRUSTED_DATA:
            return f"<untrusted-data>\n{body}\n</untrusted-data>"
        return body

    @staticmethod
    def _reference(item: ContextItem, original_tokens: int) -> str:
        source = item.source_id or item.item_id
        return f"[reference source={source} original_tokens={original_tokens}]"

    def _to_messages(self, selected: Iterable[tuple[ContextItem, str]]) -> tuple[ContextMessage, ...]:
        instruction_parts = []
        data_parts = []
        for item, rendered in selected:
            if item.role in {ContextRole.SYSTEM, ContextRole.INSTRUCTION} and item.trusted:
                instruction_parts.append(rendered)
            else:
                data_parts.append(rendered)

        messages = []
        if instruction_parts:
            messages.append(ContextMessage(role="system", content="\n\n".join(instruction_parts)))
        if data_parts:
            messages.append(ContextMessage(role="user", content="\n\n".join(data_parts)))
        return tuple(messages)

    @staticmethod
    def _ordered(items: Iterable[ContextItem]) -> list[ContextItem]:
        return sorted(items, key=lambda item: (item.sequence, item.item_id))
