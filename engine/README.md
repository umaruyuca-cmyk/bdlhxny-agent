# engine

该模块运行固定 Agent 对照实验。私有 API 从 `data` 读取固定题库，只允许提交题号和实验配置，不接受问题正文、系统提示词或自定义工具。

## 正式代码

```text
src/bdlh_runtime/evaluation/  三种 Agent 实现及冻结工具数据对照
src/bdlh_runtime/context/     长上下文选择、压缩、引用、隔离和处理报告
src/bdlh_runtime/run_api.py   私有固定用例运行 API
src/bdlh_runtime/data_client.py  数据服务客户端
src/bdlh_runtime/engine/      Agent 循环、工具装载和输出检查
src/bdlh_runtime/guardrails/  权限、只读、预算、参数和审计检查
```

对照实验默认比较：

- 裸 tool calling；
- LangGraph ReAct；
- 完整工程模式。

三组使用同一个模型、固定题目和冻结工具结果，不连接真实行情、搜索或记忆服务，避免外部数据变化污染 Agent 实现方式对照。

## 命令行运行

```powershell
uv sync --extra dev
$env:LLM_API_KEY = "..."
uv run python -m bdlh_runtime.evaluation.ab_eval --runs 5
```

## 私有 API

```powershell
$env:RUN_API_TOKEN = "..."
$env:DATA_INTERNAL_TOKEN = "..."
$env:DATA_API_BASE_URL = "http://127.0.0.1:8080/internal/v1"
uv run uvicorn bdlh_runtime.run_api:app --host 127.0.0.1 --port 8090
```

创建批次：`POST /api/v1/eval-batches`。请求只允许 `case_ids`、`runs`、`include_react` 和 `model`；额外字段会被拒绝。

## 验证

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q
```
