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
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bdlh_runtime.data_client import DataClient, DataServiceError
from bdlh_runtime.evaluation.ab_eval import _report_payload, run_ab_eval

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/app/artifacts"))

app = FastAPI(title="Touchstone Private Run API", version="1")
_JOBS: dict[str, dict[str, Any]] = {}
_BATCH_SLOTS = threading.BoundedSemaphore(max(1, int(os.getenv("MAX_CONCURRENT_BATCHES", "1"))))


def _require_token(authorization: str | None) -> None:
    token = os.getenv("RUN_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="RUN_API_TOKEN 未配置，运行接口关闭")
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="令牌无效")


def _data() -> DataClient:
    return DataClient()


class EvalBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_ids: list[str] | None = Field(default=None, max_length=100, description="固定题号子集；空表示全部")
    runs: int = Field(default=1, ge=1, le=5, description="每题每种实现的重复次数")
    include_react: bool = Field(default=True, description="是否包含 LangGraph ReAct 实现")
    model: str = Field(default="glm-4.7-flash", min_length=1, max_length=100)


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


@app.get("/api/v1/cases")
def list_cases(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    _require_token(authorization)
    try:
        return _data().list_cases()
    except DataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/v1/eval-batches")
def start_eval_batch(request: EvalBatchRequest, authorization: str | None = Header(default=None)) -> dict[str, str]:
    _require_token(authorization)
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
            report = _execute_eval(request)
            _persist_runs(data, batch_id, catalog, request, report)
            _persist_artifact(batch_id, report)
            data.complete_batch(batch_id, "COMPLETE")
            job["status"] = "done"
            job["report"] = report
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
def get_job(job_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_token(authorization)
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在；已完成的运行记录请从数据服务读取")
    return job


@app.get("/api/v1/batches/{batch_id}")
def get_batch(batch_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_token(authorization)
    try:
        return _data().get_batch(batch_id)
    except DataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _execute_eval(request: EvalBatchRequest) -> dict[str, Any]:
    async def run() -> Any:
        return await run_ab_eval(
            runs_per_case=request.runs,
            model=request.model,
            with_react=request.include_react,
            case_ids=request.case_ids,
        )

    return _report_payload(asyncio.run(run()))


def _persist_runs(
    data: DataClient,
    batch_id: str,
    catalog: list[dict[str, Any]],
    request: EvalBatchRequest,
    report: dict[str, Any],
) -> None:
    versions = {str(case["id"]): int(case["version"]) for case in catalog}
    modes = ["baseline-tool-calling", "full-system"]
    if request.include_react:
        modes.insert(1, "langgraph-react")
    result_keys = {
        "baseline-tool-calling": "baseline",
        "langgraph-react": "react",
        "full-system": "treatment",
    }
    for case in report.get("cases", []):
        case_id = str(case["id"])
        for mode in modes:
            aggregate = case.get(result_keys[mode], {})
            run_id = data.create_run(
                {
                    "batchId": batch_id,
                    "caseId": case_id,
                    "caseVersion": versions[case_id],
                    "variantId": "default",
                    "snapshotId": f"{case_id}:fixture-v1",
                    "agentMode": mode,
                    "contextStrategy": "fixed-case-input",
                    "model": request.model,
                    "gitCommit": os.getenv("GIT_COMMIT", "unknown"),
                    "modelConfig": {"runs": request.runs, "toolData": "frozen"},
                }
            )
            data.save_evaluation(run_id, checks=aggregate, metrics=aggregate)
            data.complete_run(run_id, {"aggregate": aggregate, "lineage": case.get("lineage", [])})


def _persist_artifact(batch_id: str, payload: dict[str, Any]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    (ARTIFACTS_DIR / f"{batch_id}.json").write_text(content, encoding="utf-8")
    (ARTIFACTS_DIR / "latest.json").write_text(content, encoding="utf-8")
