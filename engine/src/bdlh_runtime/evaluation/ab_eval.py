"""eval 对照：裸 tool calling、LangGraph 官方 ReAct 与完整工程模式三组对比。

固定题库的唯一真源是 data 服务（PostgreSQL seed）；本模块不再维护第二份题目，
由调用方通过 ``load_cases`` 把用例目录转换为执行输入。
同一 LLM、同一份冻结工具返回（data 服务 → PostgreSQL fixture 表），唯一变量是编排形态。
- 裸 tool calling（基线）：全量工具 + 无 Guardrail + 无 Selective Loading + 无 Fast-Path + 无 Output Guardrail
- LangGraph 官方 ReAct（可选对照组）：create_react_agent 框架默认编排（ToolNode 统一执行）
- 完整工程模式（本系统）：scoped 装载 + G1-G7 治理中间件 + 语义快路径 + Output Guardrail

CLI: LLM_API_KEY=xxx python -m bdlh_runtime.evaluation.ab_eval --runs 5 [--no-with-react]
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from langchain_core.messages import AIMessage

from bdlh_runtime.data_client import DataClient
from bdlh_runtime.engine.loop import AgentLoop, AgentResult, AgentTurn, load_prompt
from bdlh_runtime.engine.output_guardrail import (
    C1ComplianceCheck,
    C2ComplianceCheck,
    NumberGroundingCheck,
    OutputGuardrail,
)
from bdlh_runtime.engine.semantic_router.fastpath_data import CHITCHAT_RESPONSE, FORBIDDEN_RESPONSE
from bdlh_runtime.evaluation.baseline_agent import BASELINE_SYSTEM, BaselineResult, naive_run
from bdlh_runtime.evaluation.baseline_langgraph import react_official_run
from bdlh_runtime.evaluation.frozen_observations import FIXTURE_SET_ID, FrozenObservations
from bdlh_runtime.evaluation.run_telemetry import (
    MODE_BASELINE,
    MODE_REACT,
    MODE_TREATMENT,
    TOKENIZER_VERSION,
    RecordingExecutor,
    RecordingLLM,
    RunRecord,
    RunRecorder,
    classify_failure,
    context_build_payload,
    payload_hash,
    record_output_guardrail,
    record_treatment_audits,
    validity_of,
)
from bdlh_runtime.infra.llm import DEFAULT_LLM_BASE_URL, create_llm
from bdlh_runtime.registry import load_and_validate_payload
from bdlh_runtime.tools.catalog import ToolCatalog, catalog_from_snapshot

_REPO_ROOT = Path(__file__).resolve().parents[4]

#: 交错运行默认种子(确定性可复现;CLI/接口可覆盖)
DEFAULT_INTERLEAVE_SEED = 20260821
#: 每组最小 VALID 样本门槛(任务三);环境变量 EVAL_MIN_VALID_SAMPLES 可覆盖
DEFAULT_MIN_VALID_SAMPLES = 5


# ── 固定用例（唯一真源：data 服务 → PostgreSQL seed）──────────────────


@dataclass(frozen=True)
class ABCase:
    id: str
    category: str
    message: str
    scene_tag: str = "research"
    authenticated: bool = False
    history: tuple[dict[str, str], ...] = ()
    fastpath: str | None = None
    expected_tools: tuple[str, ...] = ()
    absent_tools: tuple[str, ...] = ()
    # 用例版本与真实变体/快照标识(来自 data 服务,运行记录据此关联
    # case_variants / data_snapshots,不再本地拼接)
    case_version: int = 1
    variant_id: str = "default"
    snapshot_id: str = ""
    snapshot_hash: str = ""
    context_strategy: str = "budgeted"
    token_budget: int = 0


def _default_variant(view: dict[str, Any]) -> dict[str, Any]:
    """取 default 变体条目;缺失即 fail-fast,禁止回退为拼接字符串。"""
    variants = view.get("variants")
    if not isinstance(variants, list):
        raise ValueError(f"case {view.get('id')} 视图缺少 variants(data 服务需提供真实变体/快照标识)")
    for item in variants:
        if isinstance(item, dict) and str(item.get("variantId")) == "default":
            return item
    raise ValueError(f"case {view.get('id')} 没有 default 变体")


def load_cases(views: list[dict[str, Any]]) -> list[ABCase]:
    """把 data 服务返回的固定用例目录转换为执行用例。

    多步用例（case_steps）中除最后一步外的消息作为 history 回放；
    ``role=assistant_fixture`` 的步骤按 assistant 消息处理。
    """
    cases: list[ABCase] = []
    for view in views:
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
        variant = _default_variant(view)
        cases.append(
            ABCase(
                id=str(view["id"]),
                category=str(checks.get("category") or view.get("title") or ""),
                message=str(view.get("message") or ""),
                scene_tag=str(view.get("scene") or "research"),
                authenticated=bool(view.get("authenticated")),
                history=history,
                fastpath=fastpath if isinstance(fastpath, str) and fastpath else None,
                expected_tools=tuple(checks.get("expected_tools") or ()),
                absent_tools=tuple(checks.get("absent_tools") or ()),
                case_version=int(view.get("version") or 1),
                variant_id=str(variant.get("variantId") or "default"),
                snapshot_id=str(variant.get("snapshotId") or ""),
                snapshot_hash=str(variant.get("snapshotHash") or ""),
                context_strategy=str(variant.get("contextStrategy") or "budgeted"),
                token_budget=int(variant.get("tokenBudget") or 0),
            )
        )
    return cases


# ── FrozenToolExecutor（三组共用，隔离执行质量差异）──────────────────────


class FrozenToolExecutor:
    """按 (tool_name, symbol) 查冻结数据集返回；记录 (name, args, result)（与真实执行器同接口，供判官检查）。"""

    def __init__(self, frozen: FrozenObservations) -> None:
        self._frozen = frozen
        self.call_log: list[tuple[str, dict[str, Any]]] = []
        self.results: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    async def __call__(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        args = dict(arguments)
        self.call_log.append((name, args))
        result = self._frozen.get(name, args)
        self.results.append((name, args, result))
        return result


# ── GoldRouter（Treatment 组用金标快路径，隔离路由误差）──────────────────


class GoldRouter:
    """按题库金标返回快路径；非快路径题返回 None（进循环）。"""

    def __init__(self, case: ABCase) -> None:
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


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class RunJudgment:
    """一次运行的机械判定结果。"""

    # 工具层
    tool_correct: bool = False
    hallucinated_tools: list[str] = field(default_factory=list)
    forbidden_leak: list[str] = field(default_factory=list)
    # 答案层
    number_hallucinations: list[str] = field(default_factory=list)
    c1_violations: list[str] = field(default_factory=list)
    c2_violations: list[str] = field(default_factory=list)
    # 效率
    rounds: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # API 未回 usage、token 为 chars//4 近似时置 True（指标口径标注）。
    tokens_estimated: bool = False
    duration_ms: int = 0
    # 异常
    error: str | None = None
    # 运行追溯与有效性(架构文档 §7.1):INVALID 不进能力统计
    run_key: str = ""
    repeat_index: int = 0
    validity: str = "VALID"
    error_category: str | None = None


@dataclass
class CaseReport:
    """单题 × N 次运行的汇总。"""

    case_id: str
    category: str
    message: str
    baseline_runs: list[RunJudgment] = field(default_factory=list)
    react_runs: list[RunJudgment] = field(default_factory=list)
    treatment_runs: list[RunJudgment] = field(default_factory=list)
    baseline_answers: list[str] = field(default_factory=list)
    react_answers: list[str] = field(default_factory=list)
    treatment_answers: list[str] = field(default_factory=list)
    # 完整模式组最近一次运行的数据链路：每步 工具 → 数据面 → 查询 → 返回
    lineage: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GroupSummary:
    """聚合指标(仅 VALID 运行进入分母;无效运行单列)。"""

    tool_selection_rate: float = 0.0
    hallucination_rate: float = 0.0
    forbidden_leak_rate: float = 0.0
    number_hallucination_rate: float = 0.0
    c1_violation_rate: float = 0.0
    c2_violation_rate: float = 0.0
    mean_rounds: float = 0.0
    mean_tokens: int = 0
    median_duration_ms: int = 0
    p95_duration_ms: int = 0
    error_count: int = 0
    total_runs: int = 0
    valid_runs: int = 0
    invalid_runs: int = 0
    invalid_reasons: dict[str, int] = field(default_factory=dict)


@dataclass
class ABReport:
    case_count: int
    runs_per_case: int
    baseline: GroupSummary
    treatment: GroupSummary
    react: GroupSummary | None = None
    cases: list[CaseReport] = field(default_factory=list)
    model: str = "glm-4.7"
    executor: str = "frozen"
    run_records: list[RunRecord] = field(default_factory=list)
    # 有效样本门槛(任务三):每组 VALID 运行数 ≥ min_valid_samples 才可认定正式批次
    min_valid_samples: int = DEFAULT_MIN_VALID_SAMPLES
    validity_threshold: dict[str, Any] = field(default_factory=dict)


def evaluate_validity_threshold(
    baseline: GroupSummary,
    treatment: GroupSummary,
    react: GroupSummary | None,
    *,
    min_valid: int,
) -> dict[str, Any]:
    """批次级有效样本门槛判定(任务三):任一组 VALID 数不足即未达门槛。

    未达门槛的批次可运行、可查看,但不可认定正式(任务五消费本判定)。
    """

    groups: dict[str, GroupSummary] = {"baseline": baseline, "treatment": treatment}
    if react is not None:
        groups["react"] = react
    detail = {
        name: {"required": min_valid, "valid": group.valid_runs, "met": group.valid_runs >= min_valid}
        for name, group in groups.items()
    }
    return {
        "min_valid_per_group": min_valid,
        "groups": detail,
        "met": all(row["met"] for row in detail.values()),
    }


# ── 运行函数 ────────────────────────────────────────────────────────────


def _extract_treatment_tokens(result: AgentResult) -> tuple[int, int, bool]:
    """提取 (prompt, completion, 是否近似估算)；估算值不与真实 usage 混用口径。"""
    prompt, completion = 0, 0
    for msg in result.messages:
        # langchain 0.2+: usage_metadata typed object
        um = getattr(msg, "usage_metadata", None)
        if um is not None:
            p = int(getattr(um, "input_tokens", 0) or 0)
            c = int(getattr(um, "output_tokens", 0) or 0)
            if p > 0 or c > 0:
                prompt += p
                completion += c
                continue
        # response_metadata.token_usage (OpenAI format)
        meta = getattr(msg, "response_metadata", None)
        if isinstance(meta, dict):
            usage = meta.get("token_usage") or meta.get("usage") or {}
            if isinstance(usage, dict) and usage:
                p = int(usage.get("prompt_tokens", 0) or 0)
                c = int(usage.get("completion_tokens", 0) or 0)
                if p > 0 or c > 0:
                    prompt += p
                    completion += c
    if prompt == 0 and completion == 0:
        # Fallback: estimate from message text length
        total_chars = sum(len(str(getattr(m, "content", "") or "")) for m in result.messages)
        approx = max(1, total_chars // 4)
        return 0, approx, True
    return prompt, completion, False


def _count_rounds(messages: list[Any]) -> int:
    return sum(1 for msg in messages if isinstance(msg, AIMessage))


async def run_treatment(case: ABCase, llm: Any, catalog: ToolCatalog, executor: Any) -> tuple[AgentResult, Any, Any]:
    loop = AgentLoop(
        llm=llm,
        catalog=catalog,
        executor=executor,
        router=GoldRouter(case) if case.fastpath else None,
        tool_loading="scoped",
        max_tool_calls=20,
    )
    turn = AgentTurn(
        user_id="eval-user" if case.authenticated else "guest",
        message=case.message,
        scene_tag=case.scene_tag,
        authenticated=case.authenticated,
        history=list(case.history),
        run_id=f"ab-{case.id}",
    )
    result = await loop.run(turn)
    return result, executor, loop


# ── 判官 ────────────────────────────────────────────────────────────────

_number_check = NumberGroundingCheck()
_c1_check = C1ComplianceCheck()
_c2_check = C2ComplianceCheck()


def _judge_baseline(case: ABCase, result: BaselineResult, executor: Any, catalog_names: set[str]) -> RunJudgment:
    j = RunJudgment(error=result.error)
    actual_tools = {name for name, _ in executor.call_log}
    j.hallucinated_tools = sorted(actual_tools - catalog_names)
    j.forbidden_leak = sorted(actual_tools & set(case.absent_tools))
    if case.fastpath:
        j.tool_correct = len(actual_tools) == 0
    else:
        j.tool_correct = actual_tools == set(case.expected_tools)
    j.rounds = result.rounds
    j.prompt_tokens = result.prompt_tokens
    j.completion_tokens = result.completion_tokens
    j.tokens_estimated = result.tokens_estimated
    # 答案层检查：数字接地基于执行器实际返回（冻结或真实 Observation）
    obs_texts = [json.dumps(r, ensure_ascii=False, default=str) for _n, _a, r in executor.results]
    if obs_texts:
        j.number_hallucinations = [v.detail for v in _number_check.check(result.answer, obs_texts)]
    j.c1_violations = [v.detail for v in _c1_check.check(result.answer, [])]
    j.c2_violations = [v.detail for v in _c2_check.check(result.answer, [])]
    return j


def _judge_react(
    case: ABCase, result: BaselineResult, executor: FrozenToolExecutor, catalog_names: set[str]
) -> RunJudgment:
    """B2 判定：attempted 取模型实际发起的 tool_calls（ToolNode 拦截的幻觉尝试不丢失），
    executed 取 executor 日志（越权泄漏按实际执行计）。"""
    j = RunJudgment(error=result.error)
    attempted = set(result.attempted_tools)
    executed = {name for name, _ in executor.call_log}
    j.hallucinated_tools = sorted(attempted - catalog_names)
    j.forbidden_leak = sorted(executed & set(case.absent_tools))
    if case.fastpath:
        j.tool_correct = not attempted
    else:
        j.tool_correct = attempted == set(case.expected_tools)
    j.rounds = result.rounds
    j.prompt_tokens = result.prompt_tokens
    j.completion_tokens = result.completion_tokens
    j.tokens_estimated = result.tokens_estimated
    obs_texts = [json.dumps(r, ensure_ascii=False, default=str) for _n, _a, r in executor.results]
    if obs_texts:
        j.number_hallucinations = [v.detail for v in _number_check.check(result.answer, obs_texts)]
    j.c1_violations = [v.detail for v in _c1_check.check(result.answer, [])]
    j.c2_violations = [v.detail for v in _c2_check.check(result.answer, [])]
    return j


def _judge_treatment(
    case: ABCase,
    agent_result: AgentResult,
    guard_report: Any,
    executor: Any,
    catalog_names: set[str],
) -> RunJudgment:
    j = RunJudgment()
    successful = {a.tool_name for a in agent_result.audits if a.status == "SUCCESS"}
    blocked = {a.tool_name for a in agent_result.audits if a.status != "SUCCESS"}
    all_attempted = successful | blocked
    j.hallucinated_tools = sorted(all_attempted - catalog_names)
    j.forbidden_leak = sorted(successful & set(case.absent_tools))
    if case.fastpath:
        j.tool_correct = agent_result.fastpath_name == case.fastpath and not agent_result.entered_loop
    else:
        j.tool_correct = successful == set(case.expected_tools)
    j.rounds = _count_rounds(agent_result.messages)
    p, c, estimated = _extract_treatment_tokens(agent_result)
    j.prompt_tokens = p
    j.completion_tokens = c
    j.tokens_estimated = estimated
    # 答案层检查（用 guardrail 修正后的答案；数字接地基于执行器实际返回，与其他两组同口径）
    fixed_answer = guard_report.fixed_answer
    obs_texts = [json.dumps(r, ensure_ascii=False, default=str) for _n, _a, r in executor.results]
    if obs_texts:
        j.number_hallucinations = [v.detail for v in _number_check.check(fixed_answer, obs_texts)]
    j.c1_violations = [v.detail for v in _c1_check.check(fixed_answer, [])]
    j.c2_violations = [v.detail for v in _c2_check.check(fixed_answer, [])]
    return j


# ── 聚合 ────────────────────────────────────────────────────────────────


def _summarize(runs: list[RunJudgment]) -> GroupSummary:
    """聚合口径(任务一):只有 VALID 运行进入分母;INVALID(429/余额/服务不可用)
    单列数量与原因分组,不冒充失败样本。"""

    valid = [r for r in runs if r.validity != "INVALID"]
    invalid = [r for r in runs if r.validity == "INVALID"]
    reasons: dict[str, int] = {}
    for run in invalid:
        key = run.error_category or "UNCLASSIFIED"
        reasons[key] = reasons.get(key, 0) + 1
    n = len(valid)
    if n == 0:
        return GroupSummary(
            total_runs=len(runs), valid_runs=0, invalid_runs=len(invalid), invalid_reasons=reasons
        )
    durations = sorted(r.duration_ms for r in valid)
    p95_index = max(0, min(n - 1, (95 * n + 99) // 100 - 1))
    return GroupSummary(
        tool_selection_rate=sum(1 for r in valid if r.tool_correct) / n,
        hallucination_rate=sum(1 for r in valid if r.hallucinated_tools) / n,
        forbidden_leak_rate=sum(1 for r in valid if r.forbidden_leak) / n,
        number_hallucination_rate=sum(1 for r in valid if r.number_hallucinations) / n,
        c1_violation_rate=sum(1 for r in valid if r.c1_violations) / n,
        c2_violation_rate=sum(1 for r in valid if r.c2_violations) / n,
        mean_rounds=sum(r.rounds for r in valid) / n,
        mean_tokens=sum(r.prompt_tokens + r.completion_tokens for r in valid) // n,
        median_duration_ms=round(statistics.median(durations)),
        p95_duration_ms=durations[p95_index],
        error_count=sum(1 for r in valid if r.error),
        total_runs=len(runs),
        valid_runs=n,
        invalid_runs=len(invalid),
        invalid_reasons=reasons,
    )


def build_llm_from_env(model: str) -> Any:
    """按环境变量构建 LLM 客户端（配置唯一入口，不接受请求级 base_url/key）。

    - ``LLM_API_KEY``：必填，缺失即失败；
    - ``LLM_BASE_URL``：缺省智谱端点；
    - 模型名由调用方传入（唯一请求级可配项，缺省取 ``LLM_MODEL``）。
    """

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY 未设置")
    llm = create_llm(api_key=api_key, model=model, base_url=os.getenv("LLM_BASE_URL") or DEFAULT_LLM_BASE_URL)
    if llm is None:
        raise RuntimeError("LLM 客户端创建失败")
    return llm


# ── 主 runner ───────────────────────────────────────────────────────────

#: 机械判官版本(与 data 服务 evaluation_results.evaluator_version 一致)
JUDGE_VERSION = "fixed-rules-v1"

_RETRY_ATTEMPTS = 3


def _tool_catalog_hash(catalog: ToolCatalog) -> str:
    cards = [
        {"name": card.name, "description": card.description, "parameters": card.parameters}
        for card in sorted(catalog.list(), key=lambda item: item.name)
    ]
    return payload_hash(cards)


def _finalize_run(
    recorder: RunRecorder,
    judgment: RunJudgment,
    *,
    answer: str,
    prompt_hash: str,
    audit_codes: list[str] | None = None,
) -> None:
    """判官结论落事件流;有效性分类(§7.1)并写入工件 provenance。"""

    status, category = classify_failure(judgment.error)
    judgment.validity = validity_of(status)
    judgment.error_category = category or None
    judgment.run_key = recorder.record.run_key
    judgment.repeat_index = recorder.record.repeat_index
    recorder.record.provenance = {
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),
        "prompt_hash": prompt_hash,
        "tool_catalog_hash": recorder.record.provenance.get("tool_catalog_hash", ""),
        "judge_version": JUDGE_VERSION,
        # 走过构建器的运行记构建器口径;未走的记消息估算口径
        "tokenizer_version": (recorder.record.context_build or {}).get("tokenizerVersion") or TOKENIZER_VERSION,
    }
    if status == "COMPLETE":
        recorder.record_output(answer_excerpt=answer, audit_codes=audit_codes or [])
    recorder.record_judgment(
        {
            "tool_correct": judgment.tool_correct,
            "hallucinated_tools": judgment.hallucinated_tools,
            "forbidden_leak": judgment.forbidden_leak,
            "number_hallucinations": judgment.number_hallucinations,
            "c1_violations": judgment.c1_violations,
            "c2_violations": judgment.c2_violations,
            "rounds": judgment.rounds,
            "tokens_estimated": judgment.tokens_estimated,
            "error": judgment.error,
            "validity": judgment.validity,
            "error_category": judgment.error_category,
        }
    )
    recorder.complete(status=status, error_category=category or None, error_text=judgment.error)


def _attach_context_build(recorder: RunRecorder, result: AgentResult) -> None:
    """完整模式运行:把循环内真实构建报告挂到运行记录(context_builds + 工件)。"""

    if result.context_build_result is None:
        # 罐头快路径未发生模型输入,无构建;如实记录
        recorder.record_context(
            {"strategy": "fixed-case-input", "status": "SKIPPED", "note": "罐头快路径,无模型输入"}
        )
        return
    build = context_build_payload(
        result.context_build_result,
        list(result.context_items_used),
        duration_ms=result.context_build_ms,
    )
    recorder.attach_context_build(build)
    recorder.record_context(
        {
            "strategy": build["strategy"],
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


async def run_ab_eval(
    runs_per_case: int = 5,
    llm: Any | None = None,
    model: str = "glm-4.7-flash",
    with_react: bool = True,
    cases: list[ABCase] | None = None,
    *,
    catalog: ToolCatalog | None = None,
    frozen: FrozenObservations | None = None,
    retry_delay_s: float = 30.0,
    inter_run_delay_s: float = 1.0,
    interleave_seed: int = DEFAULT_INTERLEAVE_SEED,
    min_valid_samples: int | None = None,
) -> ABReport:
    """跑一轮对照批次;每次执行(case × mode × repeat)产出完整 RunRecord。

    交错运行:题序按 repeat 轮转、三组顺序按 ``interleave_seed`` 确定性洗牌。
    """

    if not cases:
        raise ValueError("cases 为空：固定用例必须由调用方通过 load_cases 从 data 服务加载")
    selected = cases
    if llm is None:
        llm = build_llm_from_env(model)

    if catalog is None or frozen is None:
        data = DataClient()
        catalog = catalog_from_snapshot(load_and_validate_payload(data.get_tool_catalog()))
        frozen = FrozenObservations(data.get_tool_fixtures(FIXTURE_SET_ID))
    catalog_names = {c.name for c in catalog.list()}
    all_cards = [c for c in catalog.list() if c.name != "search_tools"]
    guardrail = OutputGuardrail()
    catalog_hash = _tool_catalog_hash(catalog)
    baseline_prompt_hash = payload_hash(BASELINE_SYSTEM)
    treatment_prompt_hash = payload_hash(load_prompt("system_base.md", "scene_chat.md"))

    def build_executor() -> FrozenToolExecutor:
        return FrozenToolExecutor(frozen)

    def new_recorder(case: ABCase, mode: str, repeat_index: int, *, emit_context: bool = True) -> RunRecorder:
        recorder = RunRecorder(
            run_key=f"{case.id}:{mode}:{repeat_index}",
            case_id=case.id,
            case_version=case.case_version,
            variant_id=case.variant_id,
            snapshot_id=case.snapshot_id,
            snapshot_hash=case.snapshot_hash,
            agent_mode=mode,
            context_strategy="fixed-case-input",
            model=model,
            repeat_index=repeat_index,
            message=case.message,
            category=case.category,
        )
        recorder.record.provenance["tool_catalog_hash"] = catalog_hash
        if emit_context:
            recorder.record_context(
                {
                    "strategy": "fixed-case-input",
                    "itemCount": len(case.history),
                    "historyTurns": len(case.history),
                    "tokenizerVersion": TOKENIZER_VERSION,
                    **({"tokenBudget": case.token_budget} if case.token_budget else {}),
                }
            )
        return recorder

    def is_rate_limited(error: str | None) -> bool:
        return bool(error) and "429" in str(error)

    run_records: list[RunRecord] = []
    case_reports = {
        case.id: CaseReport(case_id=case.id, category=case.category, message=case.message) for case in selected
    }
    rng = random.Random(interleave_seed)
    group_modes = [MODE_BASELINE, MODE_REACT, MODE_TREATMENT] if with_react else [MODE_BASELINE, MODE_TREATMENT]

    async def run_group(mode: str, case: ABCase, repeat_index: int) -> None:
        cr = case_reports[case.id]
        if mode == MODE_BASELINE:
            b_started = time.perf_counter()
            b_recorder: RunRecorder | None = None
            b_result: BaselineResult | None = None
            b_exec: Any = None
            for attempt in range(_RETRY_ATTEMPTS):
                b_recorder = new_recorder(case, MODE_BASELINE, repeat_index)
                b_exec = RecordingExecutor(build_executor(), b_recorder)
                b_result = await naive_run(
                    message=case.message,
                    history=list(case.history),
                    all_cards=all_cards,
                    llm=RecordingLLM(llm, b_recorder, model),
                    executor=b_exec,
                    system_prompt=BASELINE_SYSTEM,
                )
                if is_rate_limited(b_result.error) and attempt < _RETRY_ATTEMPTS - 1:
                    print(f"    baseline 429, retry in {retry_delay_s:.0f}s ({attempt + 1}/{_RETRY_ATTEMPTS})")
                    await asyncio.sleep(retry_delay_s)
                    continue
                break
            b_recorder.mark_judgment_started()
            b_judgment = _judge_baseline(case, b_result, b_exec, catalog_names)
            b_judgment.duration_ms = round((time.perf_counter() - b_started) * 1000)
            _finalize_run(b_recorder, b_judgment, answer=b_result.answer or "", prompt_hash=baseline_prompt_hash)
            cr.baseline_runs.append(b_judgment)
            cr.baseline_answers.append((b_result.answer or "")[:200])
            run_records.append(b_recorder.record)
            return
        if mode == MODE_REACT:
            r_started = time.perf_counter()
            r_recorder: RunRecorder | None = None
            r_result: BaselineResult | None = None
            r_exec: Any = None
            for attempt in range(_RETRY_ATTEMPTS):
                r_recorder = new_recorder(case, MODE_REACT, repeat_index)
                r_exec = RecordingExecutor(build_executor(), r_recorder)
                r_result = await react_official_run(
                    message=case.message,
                    history=list(case.history),
                    all_cards=all_cards,
                    llm=RecordingLLM(llm, r_recorder, model),
                    executor=r_exec,
                    system_prompt=BASELINE_SYSTEM,
                )
                if is_rate_limited(r_result.error) and attempt < _RETRY_ATTEMPTS - 1:
                    print(f"    react 429, retry in {retry_delay_s:.0f}s ({attempt + 1}/{_RETRY_ATTEMPTS})")
                    await asyncio.sleep(retry_delay_s)
                    continue
                break
            r_recorder.mark_judgment_started()
            r_judgment = _judge_react(case, r_result, r_exec, catalog_names)
            r_judgment.duration_ms = round((time.perf_counter() - r_started) * 1000)
            _finalize_run(r_recorder, r_judgment, answer=r_result.answer or "", prompt_hash=baseline_prompt_hash)
            cr.react_runs.append(r_judgment)
            cr.react_answers.append((r_result.answer or "")[:200])
            run_records.append(r_recorder.record)
            return

        # Treatment (with 429 retry)
        t_started = time.perf_counter()
        t_recorder: RunRecorder | None = None
        t_result: AgentResult | None = None
        t_exec: Any = None
        t_error: str | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            t_recorder = new_recorder(case, MODE_TREATMENT, repeat_index, emit_context=False)
            t_exec = RecordingExecutor(build_executor(), t_recorder)
            try:
                t_result, _inner_exec, _loop = await run_treatment(
                    case, RecordingLLM(llm, t_recorder, model), catalog, t_exec
                )
                break
            except Exception as exc:  # noqa: BLE001 —— 异常降级为一次运行,不中断批次
                if "429" in str(exc) and attempt < _RETRY_ATTEMPTS - 1:
                    print(f"    treatment 429, retry in {retry_delay_s:.0f}s ({attempt + 1}/{_RETRY_ATTEMPTS})")
                    await asyncio.sleep(retry_delay_s)
                    continue
                t_error = str(exc)
                break
        t_recorder.mark_judgment_started()
        if t_result is None:
            t_recorder.record_context(
                {
                    "strategy": "fixed-case-input",
                    "status": "FAILED",
                    "note": "运行失败,循环内构建报告不可得",
                    "tokenizerVersion": TOKENIZER_VERSION,
                }
            )
            t_judgment = RunJudgment(
                error=t_error or "treatment 运行失败",
                duration_ms=round((time.perf_counter() - t_started) * 1000),
            )
            _finalize_run(t_recorder, t_judgment, answer="", prompt_hash=treatment_prompt_hash)
            cr.treatment_runs.append(t_judgment)
            cr.treatment_answers.append(f"（失败：{t_error}）")
        else:
            _attach_context_build(t_recorder, t_result)
            record_treatment_audits(t_recorder, t_result.audits, t_result.observations)
            t_guard = guardrail.check(t_result.answer, t_result.observations)
            record_output_guardrail(t_recorder, t_guard)
            t_judgment = _judge_treatment(case, t_result, t_guard, t_exec, catalog_names)
            t_judgment.duration_ms = round((time.perf_counter() - t_started) * 1000)
            _finalize_run(
                t_recorder,
                t_judgment,
                answer=t_guard.fixed_answer,
                prompt_hash=treatment_prompt_hash,
                audit_codes=t_guard.audit_codes,
            )
            cr.treatment_runs.append(t_judgment)
            cr.treatment_answers.append(t_guard.fixed_answer[:200])
            cr.lineage = [
                {
                    "tool": tool_name,
                    "store": "frozen-fixture",
                    "query": args,
                    "result": _lineage_digest(result),
                }
                for tool_name, args, result in t_exec.results
            ]
        run_records.append(t_recorder.record)

    # 交错运行(任务三):题序按 repeat 轮转、三组顺序按确定性种子洗牌,
    # 避免先跑组总是遇到更好的服务状态;同一种子可完整复现执行序
    for repeat_index in range(runs_per_case):
        offset = repeat_index % len(selected)
        rotated = selected[offset:] + selected[:offset] if offset else list(selected)
        for case in rotated:
            order = list(group_modes)
            rng.shuffle(order)
            for mode in order:
                await run_group(mode, case, repeat_index)
                await asyncio.sleep(inter_run_delay_s)

    case_reports_ordered = [case_reports[case.id] for case in selected]
    for cr in case_reports_ordered:
        react_part = ""
        if with_react:
            react_part = f" 官方ReAct={sum(1 for r in cr.react_runs if r.tool_correct)}/{runs_per_case}"
        print(
            f"  {case.id} [{case.category}] "
            f"裸调用={sum(1 for r in cr.baseline_runs if r.tool_correct)}/{runs_per_case}"
            f"{react_part} "
            f"完整模式={sum(1 for r in cr.treatment_runs if r.tool_correct)}/{runs_per_case}"
        )

    all_baseline = [j for cr in case_reports_ordered for j in cr.baseline_runs]
    all_treatment = [j for cr in case_reports_ordered for j in cr.treatment_runs]
    all_react = [j for cr in case_reports_ordered for j in cr.react_runs] if with_react else None
    baseline_summary = _summarize(all_baseline)
    treatment_summary = _summarize(all_treatment)
    react_summary = _summarize(all_react) if all_react else None
    resolved_min_valid = (
        min_valid_samples
        if min_valid_samples is not None
        else int(os.getenv("EVAL_MIN_VALID_SAMPLES", str(DEFAULT_MIN_VALID_SAMPLES)))
    )
    return ABReport(
        case_count=len(selected),
        runs_per_case=runs_per_case,
        baseline=baseline_summary,
        treatment=treatment_summary,
        react=react_summary,
        cases=case_reports_ordered,
        model=model,
        executor="frozen",
        run_records=run_records,
        min_valid_samples=resolved_min_valid,
        validity_threshold=evaluate_validity_threshold(
            baseline_summary, treatment_summary, react_summary, min_valid=resolved_min_valid
        ),
    )


# ── 报告渲染 ────────────────────────────────────────────────────────────


def _pct(rate: float) -> str:
    return f"{rate:.0%}"


def _pp(rate: float) -> str:
    delta = rate * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.0f}pp"


def _pp_guarded(baseline_rate: float, treatment_rate: float) -> str:
    """变化列口径(任务三):0%→0% 不渲染为改善/回归(无有效样本不构成结论)。"""
    if baseline_rate == 0 and treatment_rate == 0:
        return "—"
    return _pp(treatment_rate - baseline_rate)


def _token_pct(baseline: int, treatment: int) -> str:
    if baseline == 0:
        return "—"
    delta = (treatment - baseline) / baseline * 100
    return f"{delta:+.0f}%"


def _invalid_summary(label: str, group: GroupSummary) -> str | None:
    if group.invalid_runs <= 0:
        return None
    reasons = ", ".join(f"{key}×{count}" for key, count in sorted(group.invalid_reasons.items()))
    return f"- {label}:无效 {group.invalid_runs}/{group.total_runs}({reasons})"


def render_markdown(report: ABReport) -> str:
    b, t = report.baseline, report.treatment
    r = report.react
    has_react = r is not None
    lines = [
        f"# 设计模式有效性对照（{date.today().isoformat()}）",
        "",
        "## 实验设置",
        "",
        f"- 模型：{report.model}（temperature=0.1）",
        f"- 题库：{report.case_count} 题 × {report.runs_per_case} 次 = {report.case_count * report.runs_per_case} 次实验/组",
        "- 裸 tool calling（基线）：LLM 原生 tool calling（无 Guardrail / 无 Selective Loading / 无 Fast-Path / 无 Output Guardrail）",
    ]
    if has_react:
        lines.append(
            "- LangGraph 官方 ReAct（对照组）：create_react_agent 框架默认编排（全量工具 + ToolNode 统一执行，无治理；recursion_limit=50）"
        )
    lines += [
        "- 完整工程模式（本系统）：Guardrail Middleware G1-G7 + Selective Tool Loading + Semantic Fast-Path + Output Guardrail",
        "- 工具执行器：冻结数据（各组共用同一份结果，隔离外部服务和数据变化）",
        "- 路由：GoldRouter（金标快路径，隔离路由误差；仅 T 组接入快路径）",
    ]
    invalid_rows = [
        row
        for row in (
            _invalid_summary("裸调用", b),
            _invalid_summary("官方ReAct", r) if has_react else None,
            _invalid_summary("完整模式", t),
        )
        if row is not None
    ]
    if invalid_rows:
        lines.append("")
        lines.append("**无效运行(不进入指标分母)**:")
        lines.extend(invalid_rows)
    lines += [
        "",
        "## 样本口径(总运行 / 有效 / 无效三分)",
        "",
        "| 组 | 总运行 | 有效 | 无效 | 无效原因 |",
        "|---|---:|---:|---:|---|",
    ]

    def _reason_cell(group: GroupSummary) -> str:
        if not group.invalid_reasons:
            return "—"
        return ", ".join(f"{key}×{count}" for key, count in sorted(group.invalid_reasons.items()))

    sample_rows = [("裸调用", b), ("完整模式", t)]
    if has_react:
        sample_rows.insert(1, ("官方ReAct", r))
    for label, group in sample_rows:
        lines.append(
            f"| {label} | {group.total_runs} | {group.valid_runs} | {group.invalid_runs} | {_reason_cell(group)} |"
        )
    threshold = report.validity_threshold or {}
    if threshold:
        verdict = "满足" if threshold.get("met") else "未满足"
        lines.append("")
        lines.append(
            f"**有效样本门槛**:每组 ≥ {threshold.get('min_valid_per_group', report.min_valid_samples)} 个 VALID"
            f"——本批次**{verdict}**(未达门槛可查看但不可认定正式批次)"
        )
    lines += [
        "",
        "## 总表",
        "",
    ]
    if has_react:
        lines += [
            "| 指标 | 裸 tool calling | LangGraph 官方 ReAct | 完整工程模式 | 变化(完整−基线) |",
            "|---|---:|---:|---:|---:|",
            f"| 工具选择准确率 | {_pct(b.tool_selection_rate)} | {_pct(r.tool_selection_rate)} | {_pct(t.tool_selection_rate)} | {_pp_guarded(b.tool_selection_rate, t.tool_selection_rate)} |",
            f"| 幻觉工具率 | {_pct(b.hallucination_rate)} | {_pct(r.hallucination_rate)} | {_pct(t.hallucination_rate)} | {_pp_guarded(b.hallucination_rate, t.hallucination_rate)} |",
            f"| 越权泄漏率 | {_pct(b.forbidden_leak_rate)} | {_pct(r.forbidden_leak_rate)} | {_pct(t.forbidden_leak_rate)} | {_pp_guarded(b.forbidden_leak_rate, t.forbidden_leak_rate)} |",
            f"| 数字幻觉率 | {_pct(b.number_hallucination_rate)} | {_pct(r.number_hallucination_rate)} | {_pct(t.number_hallucination_rate)} | {_pp_guarded(b.number_hallucination_rate, t.number_hallucination_rate)} |",
            f"| 合规违规率(C-1) | {_pct(b.c1_violation_rate)} | {_pct(r.c1_violation_rate)} | {_pct(t.c1_violation_rate)} | {_pp_guarded(b.c1_violation_rate, t.c1_violation_rate)} |",
            f"| 合规违规率(C-2) | {_pct(b.c2_violation_rate)} | {_pct(r.c2_violation_rate)} | {_pct(t.c2_violation_rate)} | {_pp_guarded(b.c2_violation_rate, t.c2_violation_rate)} |",
            f"| 平均轮次 | {b.mean_rounds:.1f} | {r.mean_rounds:.1f} | {t.mean_rounds:.1f} | {t.mean_rounds - b.mean_rounds:+.1f} |",
            f"| 平均 token | {b.mean_tokens} | {r.mean_tokens} | {t.mean_tokens} | {_token_pct(b.mean_tokens, t.mean_tokens)} |",
        ]
    else:
        lines += [
            "| 指标 | 裸 tool calling | 完整工程模式 | 变化(完整−基线) |",
            "|---|---:|---:|---:|",
            f"| 工具选择准确率 | {_pct(b.tool_selection_rate)} | {_pct(t.tool_selection_rate)} | {_pp_guarded(b.tool_selection_rate, t.tool_selection_rate)} |",
            f"| 幻觉工具率 | {_pct(b.hallucination_rate)} | {_pct(t.hallucination_rate)} | {_pp_guarded(b.hallucination_rate, t.hallucination_rate)} |",
            f"| 越权泄漏率 | {_pct(b.forbidden_leak_rate)} | {_pct(t.forbidden_leak_rate)} | {_pp_guarded(b.forbidden_leak_rate, t.forbidden_leak_rate)} |",
            f"| 数字幻觉率 | {_pct(b.number_hallucination_rate)} | {_pct(t.number_hallucination_rate)} | {_pp_guarded(b.number_hallucination_rate, t.number_hallucination_rate)} |",
            f"| 合规违规率(C-1) | {_pct(b.c1_violation_rate)} | {_pct(t.c1_violation_rate)} | {_pp_guarded(b.c1_violation_rate, t.c1_violation_rate)} |",
            f"| 合规违规率(C-2) | {_pct(b.c2_violation_rate)} | {_pct(t.c2_violation_rate)} | {_pp_guarded(b.c2_violation_rate, t.c2_violation_rate)} |",
            f"| 平均轮次 | {b.mean_rounds:.1f} | {t.mean_rounds:.1f} | {t.mean_rounds - b.mean_rounds:+.1f} |",
            f"| 平均 token | {b.mean_tokens} | {t.mean_tokens} | {_token_pct(b.mean_tokens, t.mean_tokens)} |",
        ]
    lines += [
        "",
        "## 模式归因",
        "",
        "| 改善来自 | 证据 |",
        "|---|---|",
        f"| Guardrail G1（可见性） | 幻觉工具率 {_pct(b.hallucination_rate)}→{_pct(t.hallucination_rate)} |",
        f"| Guardrail G3（权限） | 越权泄漏 {_pct(b.forbidden_leak_rate)}→{_pct(t.forbidden_leak_rate)} |",
        f"| Output Guardrail | 数字幻觉 {_pct(b.number_hallucination_rate)}→{_pct(t.number_hallucination_rate)} + C-1 {_pct(b.c1_violation_rate)}→{_pct(t.c1_violation_rate)} + C-2 {_pct(b.c2_violation_rate)}→{_pct(t.c2_violation_rate)} |",
        f"| Selective Loading + Fast-Path | 轮次 {b.mean_rounds:.1f}→{t.mean_rounds:.1f} + token {_token_pct(b.mean_tokens, t.mean_tokens)} |",
    ]
    if has_react:
        lines += [
            "",
            "### LangGraph 官方 ReAct 参照",
            "",
            f"- 框架默认形态 vs 裸 tool calling：工具选择 {_pct(b.tool_selection_rate)} → {_pct(r.tool_selection_rate)}，"
            f"幻觉工具 {_pct(b.hallucination_rate)} → {_pct(r.hallucination_rate)}，"
            f"数字幻觉 {_pct(b.number_hallucination_rate)} → {_pct(r.number_hallucination_rate)}，"
            f"平均 token {b.mean_tokens} → {r.mean_tokens}",
        ]
    lines += [
        "",
        "## 分场景",
        "",
    ]
    if has_react:
        lines += [
            "| 题号 | 场景 | 裸调用准确 | 官方ReAct准确 | 完整模式准确 | 裸调用幻觉 | 完整模式幻觉 |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    else:
        lines += [
            "| 题号 | 场景 | 裸调用准确 | 完整模式准确 | 裸调用幻觉 | 完整模式幻觉 |",
            "|---|---|---:|---:|---:|---:|",
        ]
    for cr in report.cases:
        b_correct = sum(1 for j in cr.baseline_runs if j.tool_correct)
        t_correct = sum(1 for j in cr.treatment_runs if j.tool_correct)
        b_hall = sum(1 for j in cr.baseline_runs if j.hallucinated_tools or j.forbidden_leak)
        t_hall = sum(1 for j in cr.treatment_runs if j.hallucinated_tools or j.forbidden_leak)
        n = len(cr.baseline_runs)
        if has_react:
            r_correct = sum(1 for j in cr.react_runs if j.tool_correct)
            lines.append(
                f"| {cr.case_id} | {cr.category} | {b_correct}/{n} | {r_correct}/{n} | {t_correct}/{n} | {b_hall}/{n} | {t_hall}/{n} |"
            )
        else:
            lines.append(
                f"| {cr.case_id} | {cr.category} | {b_correct}/{n} | {t_correct}/{n} | {b_hall}/{n} | {t_hall}/{n} |"
            )

    # 失败样例
    lines.extend(["", "## 失败样例", ""])
    shown = 0
    for cr in report.cases:
        if shown >= 5:
            break
        b_fail = any(
            not r.tool_correct or r.hallucinated_tools or r.c1_violations or r.c2_violations for r in cr.baseline_runs
        )
        t_ok = all(
            r.tool_correct and not r.hallucinated_tools and not r.c1_violations and not r.c2_violations
            for r in cr.treatment_runs
            if not r.error
        )
        if b_fail and t_ok:
            lines.append(f"### {cr.case_id}「{cr.message}」")
            lines.append(f"- **Baseline 答案**：{cr.baseline_answers[0][:150] if cr.baseline_answers else '—'}")
            lines.append(f"- **Treatment 答案**：{cr.treatment_answers[0][:150] if cr.treatment_answers else '—'}")
            lines.append("")
            shown += 1

    if shown == 0:
        lines.append("（无 Baseline 失败而 Treatment 成功的样例）")

    lines.extend(
        [
            "",
            "## 口径",
            "",
            "- 工具选择准确率：`actual_successful_tools == expected_tools`（集合相等）",
            "- 幻觉工具率：调了目录外工具名的运行比例",
            "- 越权泄漏率：游客题成功调了 absent_tools 的运行比例",
            "- 数字幻觉率：answer 里的非平凡数字不在任何 Observation 中的运行比例",
            "- C-1/C-2 违规率：answer 含交易/适当性语义的运行比例",
            "- token：prompt_tokens + completion_tokens（从 API response 累计）",
            "- 有效样本：仅 VALID 运行进入各组分母；429/余额不足/模型服务不可用等 INVALID 运行单列,不冒充失败样本",
            "- 单次运行追溯:每行指标可经 run_key → run_id 下钻事件流与逐步明细(工件 runs/{run_id}.json)",
        ]
    )
    if has_react:
        lines.extend(
            [
                "- LangGraph 官方 ReAct 组的工具判定取「模型实际发起的 tool_calls」：ToolNode 拦截的非法名计入幻觉工具，不丢失；越权泄漏仍按实际执行计",
                "- LangGraph 官方 ReAct 组 recursion_limit=50（宽于裸调用组的 10 轮 LLM 上限，排除框架步数口径差异）；步数耗尽记为一次运行而非错误",
            ]
        )
    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────────────


def _agg_runs(runs: list[RunJudgment]) -> dict[str, Any]:
    valid = [r for r in runs if r.validity != "INVALID"]
    invalid = [r for r in runs if r.validity == "INVALID"]
    reasons: dict[str, int] = {}
    for run in invalid:
        key = run.error_category or "UNCLASSIFIED"
        reasons[key] = reasons.get(key, 0) + 1
    durations = sorted(r.duration_ms for r in valid)
    p95_index = max(0, min(len(durations) - 1, (95 * len(durations) + 99) // 100 - 1)) if durations else 0
    return {
        "correct": sum(1 for r in valid if r.tool_correct),
        "hallucinated": sum(1 for r in valid if r.hallucinated_tools or r.forbidden_leak),
        "total": len(runs),
        "valid": len(valid),
        "invalid": len(invalid),
        "invalid_reasons": reasons,
        "estimated_token_runs": sum(1 for r in runs if r.tokens_estimated),
        "duration_p50_ms": round(statistics.median(durations)) if durations else 0,
        "duration_p95_ms": durations[p95_index] if durations else 0,
        "runs": [
            {
                "run_key": r.run_key,
                "repeat_index": r.repeat_index,
                "validity": r.validity,
                "tool_correct": r.tool_correct,
                "error_category": r.error_category,
            }
            for r in runs
        ],
    }


def _lineage_digest(result: dict[str, Any], limit: int = 400) -> str:
    """数据链路的返回摘要：截断保留关键数字 / 记录与向量分数。"""
    text = json.dumps(result, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _report_payload(report: ABReport) -> dict[str, Any]:
    """机器可读结果：console 评测结果页（/docs/results）消费 report.json。"""
    has_react = report.react is not None
    cases: list[dict[str, Any]] = []
    for cr in report.cases:
        item: dict[str, Any] = {
            "id": cr.case_id,
            "category": cr.category,
            "message": cr.message,
            "baseline": _agg_runs(cr.baseline_runs),
            "treatment": _agg_runs(cr.treatment_runs),
            "lineage": cr.lineage,
        }
        if has_react:
            item["react"] = _agg_runs(cr.react_runs)
        cases.append(item)
    groups: dict[str, Any] = {
        "baseline": asdict(report.baseline),
        "treatment": asdict(report.treatment),
    }
    if has_react:
        groups["react"] = asdict(report.react)
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": report.model,
        "executor": report.executor,
        "runs_per_case": report.runs_per_case,
        "case_count": report.case_count,
        "groups": groups,
        "cases": cases,
        "validity_threshold": report.validity_threshold,
        "min_valid_samples": report.min_valid_samples,
        "run_records": [
            {
                "run_key": record.run_key,
                "case_id": record.case_id,
                "agent_mode": record.agent_mode,
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
    parser = argparse.ArgumentParser(description="A/B eval: baseline vs treatment")
    parser.add_argument("--runs", type=int, default=5, help="每个 case 跑几次（默认 5）")
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("LLM_MODEL", "glm-4.7-flash"),
        help="模型名（默认取 LLM_MODEL 环境变量，缺省 glm-4.7-flash）",
    )
    parser.add_argument("--no-write-report", action="store_true")
    parser.add_argument(
        "--no-with-react", dest="with_react", action="store_false", help="跳过 LangGraph 官方 ReAct 对照组（默认运行）"
    )
    args = parser.parse_args(argv)

    views = DataClient().list_cases()
    cases = load_cases(views)
    report = asyncio.run(
        run_ab_eval(runs_per_case=args.runs, model=args.model, with_react=args.with_react, cases=cases)
    )
    md = render_markdown(report)

    # Write file first (before printing, to avoid console encoding crash losing the report)
    out = None
    if not args.no_write_report:
        out = _REPO_ROOT / "docs" / "eval" / f"{date.today().strftime('%Y%m%d')}_设计模式有效性对照.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        # 机器可读结果（最近一次，覆盖写）：console /docs/results 页运行时读取
        console_json = _REPO_ROOT / "web" / "public" / "docs" / "report.json"
        console_json.write_text(json.dumps(_report_payload(report), ensure_ascii=False, indent=2), encoding="utf-8")

    # Print (fallback to UTF-8 bytes for GBK consoles)
    try:
        print(md)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(md.encode("utf-8"))

    if out is not None:
        print(f"\nreport written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
