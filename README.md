# Touchstone —— Agent 编排模式对照实证平台

> 试金石（touchstone）：检验黄金成色的石头。本仓库不宣称哪种编排模式更好，
> 只提供检验模式成色的装置——同一题库、同一 LLM、同一 canned 数据，
> 对照裸 tool calling / LangGraph 官方 ReAct / 完整工程模式三组编排，
> 量化工具选择准确率、幻觉率、越权泄漏、轮次与 token 消耗。
> 核心原则：**模型提议，代码裁决**——语义判断交给模型，边界由代码强制。

本分支（`touchstone`）是固定用例评测与证据展示切片：被测的「完整工程模式」
来自 Sentinel（`main` 分支的主动式持仓看护 Agent）。分支保留评测引擎和静态
展示面，同时保留私有运行所需的数据服务、记忆服务、数据库脚本和部署配置；不恢复
公开聊天入口、看护环和搜索服务。

## 保留了什么

```text
sentinel-engine/            对照实验引擎（Python 3.11+ / LangGraph）
├─ engine/                  Agent 循环 + 语义快路径 + scoped|search 工具装载 + 输出护栏
├─ context/                 上下文预算、压缩、引用、隔离与处理报告
├─ guardrails/              G1–G7 治理中间件（可见性/只读/权限/预算/校验/观察包装/审计）
├─ tools/                   ToolCard 统一目录 + embedding 工具检索
├─ registry/                资格与工具目录真源（种子行内嵌于测试）
├─ memory/                  MemoryStore 端口 + 语义召回
├─ tests/eval/              对照 runner：18 题固定题库 × 三组编排 × 可复判官
└─ tests/                   内核单测（循环/装载/治理/纯净度门禁）

sentinel-console/           /docs/ 纯静态展示站（架构、对照、题库、结果）
sentinel-data/              私有数据服务（认证、持仓、风险画像和快照数据）
sentinel-memory/            私有长期记忆服务（用户范围隔离、召回和候选写入）
db/                         数据服务和记忆服务所需的数据库 schema
deploy/                     公开静态站与私有依赖的独立 Compose 配置
docs/                       六份 Touchstone 目标设计文档
```

## 运行对照实验

```powershell
Set-Location sentinel-engine
uv sync --extra dev
$env:LLM_API_KEY = "sk-..."   # OpenAI 兼容接口（默认智谱 GLM）
uv run python -m tests.eval.ab_eval --runs 5               # 默认运行三组
uv run python -m tests.eval.ab_eval --runs 5 --no-with-react  # 只运行裸调用与完整模式
```

当前 runner 的输出位置仍是迁移前实现；新版设计要求运行产物移出 `docs/`，详见
[`docs/05-实施计划与验收标准.md`](docs/05-实施计划与验收标准.md)。固定题库与当前判官口径见 `tests/eval/ab_eval.py`。

## 门禁

```powershell
# 引擎
cd sentinel-engine; uv run ruff check .; uv run python -m pytest -q
# 数据服务
cd sentinel-data; mvn -B -ntp test
# 记忆服务
cd sentinel-memory; uv run pytest -q
# 展示站
cd sentinel-console; npm test
# 部署配置
docker compose --env-file deploy/.env.ci -f deploy/docker-compose.yml config -q
docker compose -f deploy/docker-compose.public.yml config -q
```

## 与 main 分支的关系

- `main`：Sentinel 完整产品系统（看护环、聊天 API、搜索服务和业务页面）
- `touchstone`：固定用例评测切片（本分支），数据与记忆服务仅供登录后的私有运行使用；公开站仍是零后端静态展示。目标设计见 [docs/README.md](docs/README.md)。

## 已知问题（评测本身的 bug，修复后再产出工件）

- 2026-08-20 报告中 9/15 题因 LLM 429 限流两组全挂，携带零信息；
- 语义快路径把部分 research 题误路由为直答（平均轮次 1.1→0.1 即证据），待修阈值；
- 归因表存在过度归因（0%→0% 列为改善），应只保留数据支撑的结论。
