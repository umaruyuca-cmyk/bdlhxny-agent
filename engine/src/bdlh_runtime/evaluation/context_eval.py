"""长上下文压缩对照 runner(核心功能任务清单 任务二)。

六套 ctx 用例 × (full-raw / budgeted-comp) 两变体,同一 Agent 逻辑、同一冻结
工具数据、同一判官(工具/数字/合规断言与编排对照复用),唯一变量是上下文处理
策略。变体上下文条目来自 data 服务(优先 fixture_context_items 正规表,兼容
case_variants.data_fixture JSONB),运行记录关联真实 variant_id。

上下文断言(压缩对照特有):
- required_items 保留率 100%(构建报告 retained == required);
- required_facts 在工作上下文(构建后消息)中出现;
- forbidden_facts(stale/旧口径)不出现在最终答案;
- 注入条目(untrusted)被 <untrusted-data> 包裹且不进入指令区(system 消息)。

CLI: LLM_API_KEY=xxx python -m bdlh_runtime.evaluation.context_eval
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from bdlh_runtime.context import (
    CONSERVATIVE_TOKENIZER_VERSION,
    ContextBuilder,
    ContextClassification,
    ContextItem,
    ContextRole,
)
from bdlh_runtime.data_client import DataClient
from bdlh_runtime.engine.loop import AgentLoop, AgentResult, AgentTurn, assemble_model_context, load_prompt
from bdlh_runtime.engine.output_guardrail import (
    C1ComplianceCheck,
    C2ComplianceCheck,
    NumberGroundingCheck,
    OutputGuardrail,
)
from bdlh_runtime.engine.semantic_router.fastpath_data import CHITCHAT_RESPONSE, FORBIDDEN_RESPONSE
from bdlh_runtime.evaluation.ab_eval import FrozenToolExecutor, _tool_catalog_hash, build_llm_from_env
from bdlh_runtime.evaluation.frozen_observations import FIXTURE_SET_ID, FrozenObservations
from bdlh_runtime.evaluation.run_telemetry import (
    MODE_TREATMENT,
    RecordingExecutor,
    RecordingLLM,
    RunRecord,
    RunRecorder,
    classify_failure,
    context_build_payload,
    record_output_guardrail,
    record_treatment_audits,
    validity_of,
)
from bdlh_runtime.registry import load_and_validate_payload
from bdlh_runtime.tools.catalog import ToolCatalog, catalog_from_snapshot

_REPO_ROOT = Path(__file__).resolve().parents[4]
#: 压缩对照执行的变体口径:全量透传 vs 按预算压缩
FULL_VARIANT = "full-raw"
BUDGETED_VARIANT = "budgeted-comp"
COMPARISON_VARIANTS = (FULL_VARIANT, BUDGETED_VARIANT)

_number_check = NumberGroundingCheck()
_c1_check = C1ComplianceCheck()
_c2_check = C2ComplianceCheck()


# ── 变体输入 ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContextVariantCase:
    """一次压缩对照执行单元:(case, variant) 二元组。"""

    case_id: str
    case_version: int
    variant_id: str
    snapshot_id: str
    snapshot_hash: str
    message: str
    scene_tag: str
    authenticated: bool
    category: str
    context_strategy: str
    token_budget: int
    fixture_items: tuple[dict[str, Any], ...]
    expected_tools: tuple[str, ...] = ()
    absent_tools: tuple[str, ...] = ()
    fastpath: str | None = None
    history: tuple[dict[str, str], ...] = ()
    expectations: dict[str, Any] = field(default_factory=dict)
    context_source: str = "data_fixture"


def load_context_variant_cases(
    views: list[dict[str, Any]],
    data: DataClient,
    *,
    variant_ids: tuple[str, ...] = COMPARISON_VARIANTS,
) -> list[ContextVariantCase]:
    """从用例目录 + 变体上下文接口装配压缩对照执行单元。

    选择口径:用例的变体目录里出现对照变体(full-raw/budgeted-comp)即入选。
    """

    cases: list[ContextVariantCase] = []
    for view in views:
        variants = view.get("variants") or []
        wanted = [item for item in variants if str(item.get("variantId")) in variant_ids]
        if not wanted:
            continue
        checks = view.get("expectedChecks") or {}
        steps = view.get("steps") or []
        history = tuple(
            {
                "role": "assistant" if step.get("assistant") else "user",
                "content": str(step.get("message") or ""),
            }
            for step in steps[:-1]
        )
        fastpath = checks.get("fastpath")
        for variant in wanted:
            variant_id = str(variant["variantId"])
            context_payload = data.get_case_variant_context(
                str(view["id"]), int(view.get("version") or 1), variant_id
            )
            items = tuple(context_payload.get("items") or [])
            if not items:
                raise ValueError(f"变体 {view['id']}/{variant_id} 无上下文条目,无法执行压缩对照")
            cases.append(
                ContextVariantCase(
                    case_id=str(view["id"]),
                    case_version=int(view.get("version") or 1),
                    variant_id=variant_id,
                    snapshot_id=str(variant.get("snapshotId") or ""),
                    snapshot_hash=str(variant.get("snapshotHash") or ""),
                    message=str(view.get("message") or ""),
                    scene_tag=str(view.get("scene") or "research"),
                    authenticated=bool(view.get("authenticated")),
                    category=str(checks.get("category") or view.get("title") or ""),
                    context_strategy=str(context_payload.get("contextStrategy") or "budgeted"),
                    token_budget=int(context_payload.get("tokenBudget") or 0),
                    fixture_items=items,
                    expected_tools=tuple(checks.get("expected_tools") or ()),
                    absent_tools=tuple(checks.get("absent_tools") or ()),
                    fastpath=fastpath if isinstance(fastpath, str) and fastpath else None,
                    history=history,
                    expectations=dict(checks.get("context_expectations") or {}),
                    context_source=str(context_payload.get("source") or "data_fixture"),
                )
            )
    return cases


#: 当前用户属主(隔离跨用户条目);与 fixture 内容的 user-identity 条目对齐
_OWNER_ID = "fixture-user-001"


def fixture_items_to_context_items(fixture_items: tuple[dict[str, Any], ...]) -> tuple[ContextItem, ...]:
    """data 服务变体条目 → 构建器 ContextItem(分类/可信/属主保真)。"""

    items: list[ContextItem] = []
    for row in fixture_items:
        untrusted = bool(row.get("untrusted"))
        cross_user = bool(row.get("crossUser"))
        classification = ContextClassification(str(row.get("classification") or "compressible"))
        items.append(
            ContextItem(
                item_id=str(row.get("itemKey") or f"item-{len(items)}"),
                content=str(row.get("content") or ""),
                classification=classification,
                role=ContextRole.UNTRUSTED_DATA if untrusted else ContextRole.USER_DATA,
                priority=int(row.get("priority") or 0),
                source_id=str(row.get("itemKey") or ""),
                observed_at=(str(row.get("observedAt")) if row.get("observedAt") else None),
                owner_id=f"cross-user:{row.get('itemKey')}" if cross_user else None,
                trusted=not untrusted,
                sequence=int(row.get("sequence") or 0) + 1,
                item_type=str(row.get("itemType") or "generic"),
            )
        )
    return tuple(items)


class GoldRouter:
    """按题库金标返回快路径;非快路径题返回 None(进循环)。"""

    def __init__(self, case: ContextVariantCase) -> None:
        self._case = case

    def route(self, _message: str) -> Any:
        if not self._case.fastpath:
            return None
        canned = None
        if self._case.fastpath == "chitchat":
            canned = CHITCHAT_RESPONSE
        elif self._case.fastpath == "forbidden":
            canned = FORBIDDEN_RESPONSE
        return SimpleNamespace(name=self._case.fastpath, response=canned)


# ── 判定 ─────────────────────────────────────────────────────────────────


@dataclass
class ContextJudgment:
    """压缩对照运行的机械判定:编排对照断言 + 上下文断言。"""

    # 编排对照断言(与 ab_eval 同口径)
    tool_correct: bool = False
    hallucinated_tools: list[str] = field(default_factory=list)
    forbidden_leak: list[str] = field(default_factory=list)
    number_hallucinations: list[str] = field(default_factory=list)
    c1_violations: list[str] = field(default_factory=list)
    c2_violations: list[str] = field(default_factory=list)
    # 上下文断言(压缩对照特有)
    required_retained: bool = False
    required_retention_rate: float = 0.0
    missing_required_facts: list[str] = field(default_factory=list)
    forbidden_facts_in_answer: list[str] = field(default_factory=list)
    injection_isolated: bool = True
    untrusted_wrapped: bool = True
    # 效率与状态
    rounds: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tokens_estimated: bool = False
    duration_ms: int = 0
    original_tokens: int = 0
    working_tokens: int = 0
    error: str | None = None
    context_error: str | None = None
    run_key: str = ""
    repeat_index: int = 0
    validity: str = "VALID"
    error_category: str | None = None


def _working_context_text(agent_result: AgentResult, builder: ContextBuilder, turn: AgentTurn) -> str:
    """构建后工作上下文全文(与循环内构建确定性一致;罐头快路径无则空)。"""

    if agent_result.context_build_result is not None:
        return "\n".join(message.content for message in agent_result.context_build_result.messages)
    # 罐头快路径:用同一拼装函数重建(确定性),覆盖"上下文应进入模型"的口径
    with suppress(ValueError):
        assembly = assemble_model_context(
            builder,
            system_prompt=load_prompt("system_base.md", "scene_direct.md"),
            turn=turn,
        )
        return "\n".join(str(getattr(m, "content", "")) for m in assembly.messages)
    return ""


def _instruction_text(agent_result: AgentResult) -> str:
    """指令区文本:构建产出中 role=system 的消息(不应含注入条目正文)。"""

    if agent_result.context_build_result is None:
        return ""
    return "\n".join(m.content for m in agent_result.context_build_result.messages if m.role == "system")


def _stringify_fact(value: Any) -> str:
    if isinstance(value, bool):
        return ""
    return str(value)


def judge_context_run(
    case: ContextVariantCase,
    agent_result: AgentResult,
    fixed_answer: str,
    executor_results: list[tuple[str, dict[str, Any], dict[str, Any]]],
    catalog_names: set[str],
    working_text: str,
) -> ContextJudgment:
    judgment = ContextJudgment()
    expectations = case.expectations
    report = agent_result.context_report

    # 编排对照断言(复用 ab_eval 口径)
    successful = {a.tool_name for a in agent_result.audits if a.status == "SUCCESS"}
    blocked = {a.tool_name for a in agent_result.audits if a.status != "SUCCESS"}
    attempted = successful | blocked
    judgment.hallucinated_tools = sorted(attempted - catalog_names)
    judgment.forbidden_leak = sorted(successful & set(case.absent_tools))
    if case.fastpath:
        judgment.tool_correct = agent_result.fastpath_name == case.fastpath and not agent_result.entered_loop
    else:
        judgment.tool_correct = successful == set(case.expected_tools)
    obs_texts = [json.dumps(r, ensure_ascii=False, default=str) for _n, _a, r in executor_results]
    if obs_texts:
        judgment.number_hallucinations = [v.detail for v in _number_check.check(fixed_answer, obs_texts)]
    judgment.c1_violations = [v.detail for v in _c1_check.check(fixed_answer, [])]
    judgment.c2_violations = [v.detail for v in _c2_check.check(fixed_answer, [])]

    # 上下文断言
    if report is not None:
        required = set(report.required_item_ids)
        retained = set(report.retained_required_item_ids)
        judgment.required_retained = required == retained
        judgment.required_retention_rate = (len(retained & required) / len(required)) if required else 1.0
        judgment.original_tokens = report.original_tokens
        judgment.working_tokens = report.working_tokens
    required_facts = dict(expectations.get("required_facts") or {})
    missing = [
        key
        for key, value in required_facts.items()
        if (fact := _stringify_fact(value)) and fact not in working_text
    ]
    judgment.missing_required_facts = missing
    forbidden_facts = dict(expectations.get("forbidden_facts") or {})
    leaked = [
        key
        for key, value in forbidden_facts.items()
        if (fact := _stringify_fact(value)) and fact in fixed_answer
    ]
    judgment.forbidden_facts_in_answer = leaked
    injection_keys = list(expectations.get("injection_items") or [])
    untrusted_keys = {
        str(row.get("itemKey")) for row in case.fixture_items if row.get("untrusted")
    }
    watch_keys = [key for key in injection_keys if key in untrusted_keys] or sorted(untrusted_keys)
    instruction = _instruction_text(agent_result)
    injection_violations = [key for key in watch_keys if key and key in instruction]
    judgment.injection_isolated = not injection_violations
    untrusted_contents = [str(row.get("content") or "") for row in case.fixture_items if row.get("untrusted")]
    judgment.untrusted_wrapped = all(
        _untrusted_content_is_contained(content, working_text) for content in untrusted_contents
    )
    return judgment


def _untrusted_content_is_contained(content: str, working_text: str) -> bool:
    """不可信内容的安全形态:未进入工作上下文(被隔离/省略),或位于 <untrusted-data> 块内。"""

    if not content.strip() or content.strip() not in working_text:
        return True
    index = working_text.find(content)
    block_start = working_text.rfind("<untrusted-data>", 0, index)
    if block_start == -1:
        return False
    block_end = working_text.find("</untrusted-data>", block_start)
    return block_end != -1 and block_end > index


# ── 运行 ─────────────────────────────────────────────────────────────────


@dataclass
class VariantRunOutcome:
    case_id: str
    variant_id: str
    judgment: ContextJudgment
    record: RunRecord


@dataclass
class ContextEvalReport:
    case_count: int
    variant_runs: list[VariantRunOutcome] = field(default_factory=list)
    model: str = "glm-4.7-flash"
    run_records: list[RunRecord] = field(default_factory=list)


async def run_context_eval(
    cases: list[ContextVariantCase],
    llm: Any | None = None,
    model: str = "glm-4.7-flash",
    *,
    catalog: ToolCatalog | None = None,
    frozen: FrozenObservations | None = None,
    data: DataClient | None = None,
    runs_per_variant: int = 1,
    retry_delay_s: float = 30.0,
    inter_run_delay_s: float = 1.0,
) -> ContextEvalReport:
    """跑压缩对照批次;每个 (case, variant, repeat) 产出完整 RunRecord。"""

    if not cases:
        raise ValueError("压缩对照用例为空:需从 data 服务加载 ctx 变体")
    if llm is None:
        llm = build_llm_from_env(model)
    if catalog is None or frozen is None:
        client = data or DataClient()
        catalog = catalog or catalog_from_snapshot(load_and_validate_payload(client.get_tool_catalog()))
        frozen = frozen or FrozenObservations(client.get_tool_fixtures(FIXTURE_SET_ID))
    catalog_names = {c.name for c in catalog.list()}
    catalog_hash = _tool_catalog_hash(catalog)
    builder = ContextBuilder()

    guardrail = OutputGuardrail()
    report = ContextEvalReport(case_count=len({case.case_id for case in cases}), model=model)
    for case in cases:
        for repeat_index in range(runs_per_variant):
            recorder = RunRecorder(
                run_key=f"{case.case_id}:{case.variant_id}:{repeat_index}",
                case_id=case.case_id,
                case_version=case.case_version,
                variant_id=case.variant_id,
                snapshot_id=case.snapshot_id,
                snapshot_hash=case.snapshot_hash,
                agent_mode=MODE_TREATMENT,
                context_strategy=case.context_strategy,
                model=model,
                repeat_index=repeat_index,
                message=case.message,
                category=case.category,
            )
            recorder.record.provenance["tool_catalog_hash"] = catalog_hash
            recorder.record.provenance["context_source"] = case.context_source
            started = time.perf_counter()

            executor = RecordingExecutor(FrozenToolExecutor(frozen), recorder)
            turn = AgentTurn(
                user_id=_OWNER_ID if case.authenticated else "guest",
                message=case.message,
                scene_tag=case.scene_tag,
                authenticated=case.authenticated,
                history=list(case.history),
                run_id=recorder.record.run_key,
                context_entries=fixture_items_to_context_items(case.fixture_items),
                context_strategy=case.context_strategy,
                token_budget=case.token_budget,
                owner_id=_OWNER_ID,
            )
            loop = AgentLoop(
                llm=RecordingLLM(llm, recorder, model),
                catalog=catalog,
                executor=executor,
                router=GoldRouter(case) if case.fastpath else None,
                tool_loading="scoped",
                max_tool_calls=20,
                context_builder=builder,
            )
            try:
                agent_result = await loop.run(turn)
            except Exception as exc:  # noqa: BLE001 —— 异常降级为一次运行,不中断批次
                agent_result = AgentResult(answer="", entered_loop=False, degraded=True, context_error=str(exc))

            # 上下文构建报告(真实或重建)
            if agent_result.context_build_result is not None:
                build = context_build_payload(
                    agent_result.context_build_result,
                    list(agent_result.context_items_used),
                    duration_ms=agent_result.context_build_ms,
                    status="COMPLETE",
                )
            else:
                assembly = None
                with suppress(ValueError):
                    assembly = assemble_model_context(
                        builder,
                        system_prompt=load_prompt("system_base.md", "scene_direct.md"),
                        turn=turn,
                    )
                if assembly is None:
                    build = None
                else:
                    build = context_build_payload(
                        assembly.result,
                        list(assembly.items),
                        duration_ms=assembly.duration_ms,
                        status="COMPLETE",
                    )
            if build is not None:
                recorder.attach_context_build(build)
                recorder.record_context(
                    {
                        "strategy": build["strategy"],
                        "variantId": case.variant_id,
                        "itemCount": len(build["items"]),
                        "tokenBudget": build["tokenBudget"],
                        "originalTokens": build["originalTokens"],
                        "workingTokens": build["workingTokens"],
                        "requiredRetained": build["requiredRetained"],
                        "budgetFit": build["budgetFit"],
                        "tokenizerVersion": build["tokenizerVersion"],
                        "counts": build["counts"],
                    }
                )
            else:
                recorder.record_context(
                    {
                        "strategy": case.context_strategy,
                        "variantId": case.variant_id,
                        "status": "FAILED",
                        "errorCode": "CONTEXT_BUILD_FAILED",
                        "tokenizerVersion": CONSERVATIVE_TOKENIZER_VERSION,
                    }
                )

            recorder.mark_judgment_started()
            fixed_answer = agent_result.answer
            if not agent_result.degraded:
                guard_report = guardrail.check(agent_result.answer, agent_result.observations)
                record_output_guardrail(recorder, guard_report)
                fixed_answer = guard_report.fixed_answer
                record_treatment_audits(recorder, agent_result.audits, agent_result.observations)
            working_text = _working_context_text(agent_result, builder, turn)
            judgment = judge_context_run(
                case, agent_result, fixed_answer, executor.results, catalog_names, working_text
            )
            judgment.duration_ms = round((time.perf_counter() - started) * 1000)
            judgment.rounds = sum(1 for m in agent_result.messages if getattr(m, "type", "") == "ai")
            prompt, completion, estimated = _extract_tokens(agent_result)
            judgment.prompt_tokens = prompt
            judgment.completion_tokens = completion
            judgment.tokens_estimated = estimated
            judgment.error = agent_result.context_error if agent_result.degraded else None
            judgment.context_error = agent_result.context_error
            judgment.run_key = recorder.record.run_key
            judgment.repeat_index = repeat_index
            status, category = classify_failure(judgment.error)
            judgment.validity = validity_of(status)
            judgment.error_category = category or None

            recorder.record_judgment(asdict(judgment))
            if status == "COMPLETE":
                recorder.record_output(answer_excerpt=fixed_answer, audit_codes=[])
            recorder.complete(status=status, error_category=category or None, error_text=judgment.error)
            report.variant_runs.append(
                VariantRunOutcome(
                    case_id=case.case_id,
                    variant_id=case.variant_id,
                    judgment=judgment,
                    record=recorder.record,
                )
            )
            report.run_records.append(recorder.record)
            print(
                f"  {case.case_id}/{case.variant_id} "
                f"required_retained={judgment.required_retained} "
                f"tokens {judgment.original_tokens}->{judgment.working_tokens} "
                f"validity={judgment.validity}"
            )
            await asyncio.sleep(inter_run_delay_s)
    return report


def _extract_tokens(agent_result: AgentResult) -> tuple[int, int, bool]:
    """(prompt, completion, 是否估算);与编排对照判官同口径。"""

    prompt = completion = 0
    estimated = True
    for message in agent_result.messages:
        usage = getattr(message, "usage_metadata", None)
        if usage is not None:
            prompt += int(getattr(usage, "input_tokens", 0) or 0)
            completion += int(getattr(usage, "output_tokens", 0) or 0)
            estimated = False
            continue
        meta = getattr(message, "response_metadata", None)
        if isinstance(meta, dict):
            usage = meta.get("token_usage") or meta.get("usage") or {}
            if isinstance(usage, dict) and usage:
                prompt += int(usage.get("prompt_tokens", 0) or 0)
                completion += int(usage.get("completion_tokens", 0) or 0)
                estimated = False
    return prompt, completion, estimated


# ── 聚合与渲染 ───────────────────────────────────────────────────────────


def summarize_by_variant(report: ContextEvalReport) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[ContextJudgment]] = {}
    for outcome in report.variant_runs:
        grouped.setdefault(outcome.variant_id, []).append(outcome.judgment)
    summary: dict[str, dict[str, Any]] = {}
    for variant_id, judgments in sorted(grouped.items()):
        valid = [j for j in judgments if j.validity != "INVALID"]
        summary[variant_id] = {
            "total_runs": len(judgments),
            "valid_runs": len(valid),
            "invalid_runs": len(judgments) - len(valid),
            "required_retained_runs": sum(1 for j in valid if j.required_retained),
            "mean_required_retention_rate": (
                statistics.mean(j.required_retention_rate for j in valid) if valid else 0.0
            ),
            "missing_required_fact_runs": sum(1 for j in valid if j.missing_required_facts),
            "forbidden_fact_leak_runs": sum(1 for j in valid if j.forbidden_facts_in_answer),
            "injection_isolated_runs": sum(1 for j in valid if j.injection_isolated),
            "tool_correct_runs": sum(1 for j in valid if j.tool_correct),
            "mean_original_tokens": round(statistics.mean(j.original_tokens for j in valid)) if valid else 0,
            "mean_working_tokens": round(statistics.mean(j.working_tokens for j in valid)) if valid else 0,
            "mean_duration_ms": round(statistics.mean(j.duration_ms for j in valid)) if valid else 0,
        }
    return summary


def render_markdown(report: ContextEvalReport) -> str:
    summary = summarize_by_variant(report)
    lines = [
        f"# 长上下文压缩对照({date.today().isoformat()})",
        "",
        "## 实验设置",
        "",
        f"- 用例数:{report.case_count}(每套 full-raw / budgeted-comp 两变体)",
        f"- 模型:{report.model}",
        "- 同一 Agent 逻辑、同一冻结工具数据、同一判官;唯一变量是上下文处理策略",
        "- tokenizer:" + CONSERVATIVE_TOKENIZER_VERSION,
        "",
        "## 变体总表",
        "",
        "| 变体 | 有效运行 | required 保留 | 平均保留率 | 漏 required 事实 | 禁用事实入答案 | 注入隔离 | 工具正确 | 原始 token | 工作 token |",  # noqa: E501
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant_id, row in summary.items():
        lines.append(
            f"| {variant_id} | {row['valid_runs']}/{row['total_runs']} "
            f"| {row['required_retained_runs']} | {row['mean_required_retention_rate']:.0%} "
            f"| {row['missing_required_fact_runs']} | {row['forbidden_fact_leak_runs']} "
            f"| {row['injection_isolated_runs']} | {row['tool_correct_runs']} "
            f"| {row['mean_original_tokens']} | {row['mean_working_tokens']} |"
        )
    lines += [
        "",
        "## 口径",
        "",
        "- required 保留率:构建报告 retained_required / required(按条目计)",
        "- 漏 required 事实:required_facts 的取值未出现在构建后的工作上下文",
        "- 禁用事实入答案:forbidden_facts(stale/旧口径)的取值出现在最终答案",
        "- 注入隔离:untrusted 条目不在指令区(system 消息)且被 <untrusted-data> 包裹",
        "- INVALID 运行(429/构建失败等)不进入分母",
    ]
    return "\n".join(lines)


def _report_payload(report: ContextEvalReport) -> dict[str, Any]:
    return {
        "generated_at": date.today().isoformat(),
        "model": report.model,
        "case_count": report.case_count,
        "by_variant": summarize_by_variant(report),
        "variant_runs": [
            {
                "case_id": outcome.case_id,
                "variant_id": outcome.variant_id,
                "judgment": asdict(outcome.judgment),
            }
            for outcome in report.variant_runs
        ],
        "run_records": [
            {
                "run_key": record.run_key,
                "case_id": record.case_id,
                "agent_mode": record.agent_mode,
                "variant_id": record.variant_id,
                "repeat_index": record.repeat_index,
                "status": record.status,
                "validity": validity_of(record.status),
                "error_category": record.error_category,
                "run_id": record.run_id,
            }
            for record in report.run_records
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="长上下文压缩对照")
    parser.add_argument("--runs", type=int, default=1, help="每变体重复次数")
    parser.add_argument("--model", type=str, default=os.getenv("LLM_MODEL", "glm-4.7-flash"))
    parser.add_argument("--no-write-report", action="store_true")
    args = parser.parse_args(argv)

    data = DataClient()
    cases = load_context_variant_cases(data.list_cases(), data)
    if not cases:
        print("库内没有 ctx-* 对照变体;先执行 changes/20260821-long-context-cases.sql")
        return 1
    report = asyncio.run(
        run_context_eval(cases=cases, model=args.model, runs_per_variant=args.runs, data=data)
    )
    md = render_markdown(report)
    if not args.no_write_report:
        out = _REPO_ROOT / "docs" / "eval" / f"{date.today().strftime('%Y%m%d')}_长上下文压缩对照.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        payload = _REPO_ROOT / "web" / "public" / "docs" / "context-report.json"
        payload.write_text(json.dumps(_report_payload(report), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report written to {out}")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
