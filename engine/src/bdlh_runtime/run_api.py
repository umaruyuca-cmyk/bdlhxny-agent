"""仅供项目所有者使用的固定用例运行 API。

接口不接受问题正文、系统提示词或工具列表。公开展示部署不包含此服务。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from bdlh_runtime.data_client import DataClient, DataServiceError
from bdlh_runtime.evaluation.ab_eval import DEFAULT_INTERLEAVE_SEED, _report_payload, load_cases, run_ab_eval
from bdlh_runtime.evaluation.context_eval import COMPARISON_VARIANTS
from bdlh_runtime.evaluation.run_telemetry import (
    ARTIFACT_VERSION,
    RunRecord,
    artifact_hash_of,
    build_run_artifact,
    validity_of,
    verify_artifact_hash,
)

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/app/artifacts"))

app = FastAPI(
    title="Touchstone Private Run API",
    version="1",
    # 生产最小暴露：私有服务不开放交互文档与 OpenAPI schema
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# 私有 CORS：仅 /lab 页面跨端口调用需要。RUN_API_ALLOWED_ORIGINS 为空（默认）时
# 不挂中间件、不带任何 CORS 头（fail-closed）；公开部署永不配置该变量。
_allowed_origins = [origin.strip() for origin in os.getenv("RUN_API_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
if _allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
_JOBS: dict[str, dict[str, Any]] = {}
_BATCH_SLOTS = threading.BoundedSemaphore(max(1, int(os.getenv("MAX_CONCURRENT_BATCHES", "1"))))


def require_login(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="未提供会话令牌")
    try:
        account = _data().verify_session(token)
    except DataServiceError:
        raise HTTPException(status_code=503, detail="数据服务不可用") from None
    if account is None:
        raise HTTPException(status_code=401, detail="会话无效或已过期")
    return account


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _data() -> DataClient:
    return DataClient()


class EvalBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_ids: list[str] | None = Field(default=None, max_length=100, description="固定题号子集；空表示全部")
    runs: int = Field(default=1, ge=1, le=5, description="每题每种实现的重复次数")
    include_react: bool = Field(default=True, description="是否包含 LangGraph ReAct 实现")
    model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "glm-4.7-flash"),
        min_length=1,
        max_length=100,
        description="模型名；缺省取 LLM_MODEL 环境变量（唯一请求级可配项，base_url 与密钥只在服务端环境变量）",
    )
    max_total_tokens: int | None = Field(
        default=None,
        ge=1,
        description="批次 token 上限(任务四):累计消耗达到后停止发起新运行;缺省取 EVAL_MAX_TOTAL_TOKENS(未设=不限)",
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ContextBatchRequest(BaseModel):
    """长上下文压缩对照批次:六套 ctx 用例 × (full-raw / budgeted-comp) 两变体。"""

    model_config = ConfigDict(extra="forbid")

    case_ids: list[str] | None = Field(default=None, max_length=100, description="ctx 用例子集;空表示全部对照变体")
    runs: int = Field(default=1, ge=1, le=5, description="每变体重复次数")
    model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "glm-4.7-flash"),
        min_length=1,
        max_length=100,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "touchstone-run-api"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    try:
        count = len(_data().list_cases())
    except DataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ready", "case_count": count}


@app.post("/api/v1/login")
def login(request: LoginRequest, http_request: Request) -> dict[str, Any]:
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    try:
        result = _data().login(
            username=request.username,
            password=request.password,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except DataServiceError as exc:
        raise HTTPException(status_code=exc.status_code or 401, detail=str(exc)) from exc
    return {"token": result["token"], "expires_at": result["expiresAt"]}


@app.post("/api/v1/logout")
def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    token = _bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="未提供会话令牌")
    try:
        _data().logout(token)
    except DataServiceError:
        raise HTTPException(status_code=503, detail="数据服务不可用") from None
    return {"status": "ok"}


@app.get("/api/v1/cases")
def list_cases(account: Annotated[dict[str, Any], Depends(require_login)]) -> list[dict[str, Any]]:
    try:
        return _data().list_cases()
    except DataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/v1/eval-batches")
def start_eval_batch(
    request: EvalBatchRequest,
    account: Annotated[dict[str, Any], Depends(require_login)],
) -> dict[str, str]:
    data = _data()
    try:
        catalog = data.list_cases()
        known = {str(case["id"]) for case in catalog}
        unknown = [case_id for case_id in request.case_ids or [] if case_id not in known]
        if unknown:
            raise HTTPException(status_code=400, detail=f"未知 case_id：{unknown}")
        if not _BATCH_SLOTS.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="已有评测批次在运行，请等待完成后再发起")
        batch_id = data.create_batch(
            name=f"Agent 对照 {datetime.now().astimezone().isoformat(timespec='seconds')}",
            fixed_conditions={
                "caseIds": request.case_ids or sorted(known),
                "runsPerCase": request.runs,
                "includeReact": request.include_react,
                "model": request.model,
                "toolData": "frozen",
                # 门槛配置随批次记录(结果在工件 validity_threshold;任务五消费)
                "minValidSamples": int(os.getenv("EVAL_MIN_VALID_SAMPLES", "5")),
                "interleaveSeed": DEFAULT_INTERLEAVE_SEED,
                "maxTotalTokens": _max_total_tokens(request),
            },
        )
    except DataServiceError as exc:
        with contextlib.suppress(ValueError):
            _BATCH_SLOTS.release()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    job_id = uuid4().hex[:12]
    job: dict[str, Any] = {
        "job_id": job_id,
        "batch_id": batch_id,
        "status": "running",
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "request": request.model_dump(),
        "report": None,
        "error": None,
        "cancel_requested": False,
    }
    _JOBS[job_id] = job

    def task() -> None:
        try:
            payload, run_records = _execute_eval(request, catalog, job=job)
            _persist_runs(data, batch_id, request, payload, run_records)
            _persist_artifact(batch_id, payload)
            batch_status = "CANCELLED" if payload.get("stop_reason") == "CANCELLED" else "COMPLETE"
            data.complete_batch(batch_id, batch_status)
            job["status"] = "cancelled" if batch_status == "CANCELLED" else "done"
            job["report"] = payload
        except Exception as exc:  # 作业失败进入可见状态，不能让服务进程退出
            with contextlib.suppress(DataServiceError):
                data.complete_batch(batch_id, "FAILED")
            job["status"] = "error"
            job["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            _BATCH_SLOTS.release()

    threading.Thread(target=task, daemon=True).start()
    return {"job_id": job_id, "batch_id": batch_id}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, account: Annotated[dict[str, Any], Depends(require_login)]) -> dict[str, Any]:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在；已完成的运行记录请从数据服务读取")
    return job


@app.post("/api/v1/jobs/{job_id}/cancel")
def cancel_job(job_id: str, account: Annotated[dict[str, Any], Depends(require_login)]) -> dict[str, Any]:
    """协作取消(任务四):置停止标志,运行循环在发起新运行前检查;已开始的
    模型调用等待完成,不硬杀。幂等:重复取消与对已结束作业取消均无副作用。"""
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    if job["status"] == "running":
        job["cancel_requested"] = True
    return {
        "job_id": job_id,
        "status": job["status"],
        "cancel_requested": bool(job.get("cancel_requested")),
    }


@app.post("/api/v1/context-batches")
def start_context_batch(
    request: ContextBatchRequest,
    account: Annotated[dict[str, Any], Depends(require_login)],
) -> dict[str, str]:
    """长上下文压缩对照:同一 Agent、同一冻结数据,唯一变量是上下文处理策略。"""
    data = _data()
    try:
        views = data.list_cases()
        known = {
            str(view["id"])
            for view in views
            if any(
                str(item.get("variantId")) in COMPARISON_VARIANTS
                for item in view.get("variants") or []
            )
        }
        unknown = [case_id for case_id in request.case_ids or [] if case_id not in known]
        if unknown:
            raise HTTPException(status_code=400, detail=f"未知或非对照用例：{unknown}")
        if not _BATCH_SLOTS.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="已有评测批次在运行，请等待完成后再发起")
        selected = request.case_ids or sorted(known)
        batch_id = data.create_batch(
            name=f"上下文压缩对照 {datetime.now().astimezone().isoformat(timespec='seconds')}",
            fixed_conditions={
                "caseIds": selected,
                "runsPerVariant": request.runs,
                "variants": list(COMPARISON_VARIANTS),
                "model": request.model,
                "toolData": "frozen",
                # 门槛配置随批次记录(结果在工件 validity_threshold;任务五消费)
                "minValidSamples": int(os.getenv("EVAL_MIN_VALID_SAMPLES", "5")),
                "interleaveSeed": DEFAULT_INTERLEAVE_SEED,
                "maxTotalTokens": _max_total_tokens(request),
            },
        )
    except DataServiceError as exc:
        with contextlib.suppress(ValueError):
            _BATCH_SLOTS.release()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    job_id = uuid4().hex[:12]
    job: dict[str, Any] = {
        "job_id": job_id,
        "batch_id": batch_id,
        "status": "running",
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "request": request.model_dump(),
        "report": None,
        "error": None,
    }
    _JOBS[job_id] = job

    def task() -> None:
        try:
            payload, run_records = _execute_context_eval(request, views, selected)
            _persist_runs(data, batch_id, request, payload, run_records)
            _persist_artifact(batch_id, payload)
            data.complete_batch(batch_id, "COMPLETE")
            job["status"] = "done"
            job["report"] = payload
        except Exception as exc:  # 作业失败进入可见状态，不能让服务进程退出
            with contextlib.suppress(DataServiceError):
                data.complete_batch(batch_id, "FAILED")
            job["status"] = "error"
            job["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            _BATCH_SLOTS.release()

    threading.Thread(target=task, daemon=True).start()
    return {"job_id": job_id, "batch_id": batch_id}


@app.get("/api/v1/batches/{batch_id}")
def get_batch(batch_id: str, account: Annotated[dict[str, Any], Depends(require_login)]) -> dict[str, Any]:
    try:
        return _data().get_batch(batch_id)
    except DataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/runs/{run_id}/detail")
def get_run_detail(run_id: str, account: Annotated[dict[str, Any], Depends(require_login)]) -> dict[str, Any]:
    """单次运行逐步明细:事件流 + 模型/工具/guardrail 明细 + 测量 + 工件登记。"""
    try:
        return _data().get_run_detail(run_id)
    except DataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _execute_eval(
    request: EvalBatchRequest,
    catalog: list[dict[str, Any]],
    job: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[RunRecord]]:
    async def run() -> Any:
        return await run_ab_eval(
            runs_per_case=request.runs,
            model=request.model,
            with_react=request.include_react,
            cases=load_cases(catalog),
            should_stop=(lambda: bool(job.get("cancel_requested"))) if job is not None else None,
            max_total_tokens=_max_total_tokens(request),
        )

    report = asyncio.run(run())
    return _report_payload(report), report.run_records


def _max_total_tokens(request: EvalBatchRequest | ContextBatchRequest) -> int | None:
    requested = getattr(request, "max_total_tokens", None)
    if requested is not None:
        return requested
    raw = os.getenv("EVAL_MAX_TOTAL_TOKENS", "").strip()
    return int(raw) if raw.isdigit() else None


def _execute_context_eval(
    request: ContextBatchRequest,
    views: list[dict[str, Any]],
    selected: list[str],
) -> tuple[dict[str, Any], list[RunRecord]]:
    from bdlh_runtime.evaluation.context_eval import (
        _report_payload as context_report_payload,
    )
    from bdlh_runtime.evaluation.context_eval import (
        load_context_variant_cases,
        run_context_eval,
    )

    data = _data()
    cases = [case for case in load_context_variant_cases(views, data) if case.case_id in set(selected)]
    report = asyncio.run(
        run_context_eval(cases=cases, model=request.model, runs_per_variant=request.runs, data=data)
    )
    return context_report_payload(report), report.run_records


def _persist_runs(
    data: DataClient,
    batch_id: str,
    request: EvalBatchRequest | ContextBatchRequest,
    payload: dict[str, Any],
    run_records: list[RunRecord],
) -> None:
    """逐运行落库(任务一):事件流、明细表、测量、统一工件与有效性分类。"""

    run_ids: dict[str, str] = {}
    for record in run_records:
        run_ids[record.run_key] = _persist_one_run(data, batch_id, request, record)
    for row in payload.get("run_records", []):
        run_id = run_ids.get(str(row.get("run_key")))
        if run_id:
            row["run_id"] = run_id


def _persist_one_run(
    data: DataClient, batch_id: str, request: EvalBatchRequest | ContextBatchRequest, record: RunRecord
) -> str:
    run_id = data.create_run(
        {
            "batchId": batch_id,
            "caseId": record.case_id,
            "caseVersion": record.case_version,
            "variantId": record.variant_id,
            "snapshotId": record.snapshot_id,
            "agentMode": record.agent_mode,
            "contextStrategy": record.context_strategy,
            "model": record.model,
            "gitCommit": str(record.provenance.get("git_commit") or os.getenv("GIT_COMMIT", "unknown")),
            "modelConfig": {
                "runs": request.runs,
                "toolData": "frozen",
                "repeatIndex": record.repeat_index,
            },
        }
    )
    record.run_id = run_id
    record.batch_id = batch_id
    if record.events:
        data.save_events(run_id, record.events)
    if record.model_calls:
        data.save_model_calls(run_id, [row.to_payload() for row in record.model_calls])
    if record.tool_calls:
        data.save_tool_calls(run_id, [row.to_payload() for row in record.tool_calls])
    if record.guardrail_checks:
        data.save_guardrail_checks(run_id, [row.to_payload() for row in record.guardrail_checks])
    if record.measurements:
        data.save_measurements(run_id, record.measurements)
    if record.context_build:
        data.save_context_build(run_id, record.context_build)

    status = record.status
    error_category = record.error_category
    artifact = build_run_artifact(record)
    artifact_error: str | None = None
    try:
        storage_ref = _write_run_artifact_file(run_id, artifact)
    except OSError as exc:
        # 工件写失败 → INVALID(架构文档 §7.1):过程可查,但不进能力统计
        status = "INVALID"
        error_category = "ARTIFACT_WRITE_FAILED"
        artifact_error = f"{type(exc).__name__}: {exc}"
        artifact["status"] = status
        artifact["validity"] = validity_of(status)
        artifact["result"]["error_category"] = error_category
        artifact["artifact_hash"] = artifact_hash_of(artifact)
        storage_ref = ""

    valid_run = validity_of(status) == "VALID"
    data.save_evaluation(
        run_id,
        checks=dict(record.judgment),
        metrics=dict(record.measurements),
        valid_run=valid_run,
        status=status,
    )
    if storage_ref and verify_artifact_hash(artifact):
        data.save_artifact(
            run_id,
            artifact_type="run_full",
            storage_ref=storage_ref,
            content_hash=str(artifact["artifact_hash"]),
            public=False,
        )
    data.complete_run(
        run_id,
        {
            "answer_excerpt": record.answer_excerpt[:200],
            "artifact_version": ARTIFACT_VERSION,
            "artifact_hash": artifact.get("artifact_hash"),
            "artifact_error": artifact_error,
            "error_category": error_category,
            "judgment": record.judgment,
        },
    )
    record.status = status
    record.error_category = error_category
    return run_id


def _write_run_artifact_file(run_id: str, artifact: dict[str, Any]) -> str:
    runs_dir = ARTIFACTS_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    storage_ref = f"runs/{run_id}.json"
    content = json.dumps(artifact, ensure_ascii=False, indent=2)
    (ARTIFACTS_DIR / storage_ref).write_text(content, encoding="utf-8")
    return storage_ref


def _persist_artifact(batch_id: str, payload: dict[str, Any]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    (ARTIFACTS_DIR / f"{batch_id}.json").write_text(content, encoding="utf-8")
    (ARTIFACTS_DIR / "latest.json").write_text(content, encoding="utf-8")
