# sentinel-engine（Touchstone 被测引擎）

Touchstone 用于对照实验的 Python Agent 内核，保留固定题库运行需要的能力：

- 语义快路径和 Agent tool calling 循环；
- `scoped | search` 工具装载；
- 工具目录、代码拦截和 Observation 标准化；
- 强制项保留、预算选择、压缩、引用、用户隔离和上下文处理报告；
- 裸 tool calling、LangGraph ReAct 和完整工程模式对照。

新版设计从 [`docs/README.md`](../docs/README.md) 开始阅读；上下文压缩规则见
[`docs/03-上下文压缩设计.md`](../docs/03-上下文压缩设计.md)。

> 当前代码仍保留任意 `message` 和历史消息结构；目标产品只允许登录用户通过固定
> `case_id` 创建运行。迁移步骤见 `docs/05-实施计划与验收标准.md`。

## 架构分层

```text
engine/               Agent 循环、工具装载、快路径和输出检查
tools/                工具目录和工具检索
guardrails/           权限、只读、预算、参数与审计检查
observations/         工具结果标准化
memory/               记忆接口与召回基础
registry/             工具资格和目录基础
tests/eval/           固定题库和三种 Agent 实现方式对照
context/              上下文收集、预算选择、压缩、引用、隔离和校验
artifacts/            目标新增：统一运行工件和公开发布数据
```

核心原则：**模型提议，代码裁决**——意图理解与工具选择由模型完成（快路径 + 原生
tool calling）；只读、权限、预算等不可挽回决策由治理中间件以代码强制。

## 边界

- Mock 数据只用于开发 / 测试（带 `is_mock` 标记），不得用于任何真实市场结论；
- 不具备任何交易执行能力（设计文档 C-1）；
- 适合度输出仅为风险匹配筛查草稿（DRAFT），不出具适当性结论（C-2）；
- 真实模型评测需要 `LLM_API_KEY`；单元测试和确定性回归不应依赖外部模型服务。

## 运行评测

```powershell
uv sync --extra dev
uv run python -m tests.eval.ab_eval --runs 5
```

## 测试

```powershell
uv run pytest -q
```

覆盖：Agent 循环、语义路由、工具装载、治理中间件、工具结果标准化、工具目录、
上下文构建、内核边界和评测器。固定题库与对照 runner 位于 `tests/eval/`。

当前 Dockerfile 只构建可复用的引擎库镜像，不启动旧聊天服务。只接受固定
`case_id` 的私有运行 API 完成后，才会加入 `deploy/docker-compose.yml`。
