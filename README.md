# Touchstone —— Agent 编排模式对照实证平台

> 试金石（touchstone）：检验黄金成色的石头。本仓库不宣称哪种编排模式更好，
> 只提供检验模式成色的装置——同一题库、同一 LLM、同一 canned 数据，
> 对照裸 tool calling / LangGraph 官方 ReAct / 完整工程模式三组编排，
> 量化工具选择准确率、幻觉率、越权泄漏、轮次与 token 消耗。
> 核心原则：**模型提议，代码裁决**——语义判断交给模型，边界由代码强制。

本分支（`touchstone`）是实验对照的最小切片：被测的「完整工程模式」（treatment）
来自 Sentinel（`main` 分支的主动式持仓看护 Agent，含 watch-first 事件驱动看护环、
Java 数据面、MCP 接入等完整系统）；本分支只保留对照实验所需的可运行内核与展示面。

## 保留了什么

```text
sentinel-engine/            对照实验引擎（Python 3.11+ / LangGraph）
├─ engine/                  Agent 循环 + 语义快路径 + scoped|search 工具装载 + 输出护栏
├─ guardrails/              G1–G7 治理中间件（可见性/只读/权限/预算/校验/观察包装/审计）
├─ tools/                   ToolCard 统一目录 + embedding 工具检索
├─ registry/                资格与工具目录真源（种子行内嵌于测试）
├─ memory/                  MemoryStore 端口 + 语义召回
├─ tests/eval/              对照 runner：18 题固定题库 × 三组编排 × 可复判官
└─ tests/                   内核单测（循环/装载/治理/纯净度门禁）

sentinel-console/           /docs/ 纯静态展示站（架构、对照、题库、结果）
docs/                       Touchstone 目标设计（README + 产品目标 / 系统架构 / 压缩 / 评测 / 实施计划）
```

## 运行对照实验

```powershell
Set-Location sentinel-engine
uv sync --extra dev
$env:LLM_API_KEY = "sk-..."   # OpenAI 兼容接口（默认智谱 GLM）
uv run python -m tests.eval.ab_eval --runs 5            # 裸调用 vs 完整模式
uv run python -m tests.eval.ab_eval --runs 5 --with-react   # 加 LangGraph 官方 ReAct 组
```

评测机器可读结果落 `sentinel-console/public/docs/report.json`（展示站消费）；固定题库与判官口径见 `tests/eval/ab_eval.py`。

## 门禁

```powershell
# 引擎
cd sentinel-engine; uv run ruff check .; uv run python -m pytest -q
# 展示站
cd sentinel-console; npm test
```

## 与 main 分支的关系

- `main`：Sentinel 完整系统（看护环、Java 数据面、记忆服务、检索封装、部署编排）
- `touchstone`：对照实验切片（本分支）——目标设计见 [docs/README.md](docs/README.md)（Touchstone 设计文档：产品目标、系统架构、上下文压缩、评测与证据展示、实施计划）

## 已知问题（评测本身的 bug，修复后再产出工件）

- 2026-08-20 报告中 9/15 题因 LLM 429 限流两组全挂，携带零信息；
- 语义快路径把部分 research 题误路由为直答（平均轮次 1.1→0.1 即证据），待修阈值；
- 归因表存在过度归因（0%→0% 列为改善），应只保留数据支撑的结论。
