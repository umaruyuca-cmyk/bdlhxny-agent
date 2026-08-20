# sentinel-memory

这是独立的长期语义记忆服务，只保存确认过的长期信息，不保存聊天历史、运行记录、
任务数据或完整用户画像。它只部署在 Touchstone 私有运行环境中。

## Data and event ownership

The Java Data Plane accepts a memory candidate and records it in its
transactional outbox. Its `bdlh.memory.commands` RocketMQ event is consumed by
this service as consumer group `bdlh-memory-consumer`. Deduplication is local
to `memory.consumer_inbox`; this service never writes `runtime.consumer_inbox`.

在启动服务前，使用 `bdlh_memory_service` 数据库角色手工执行根目录脚本：

```powershell
psql -v ON_ERROR_STOP=1 -d bdlhRuntime -f ../db/postgresql/schema/memory_service.sql
```

## Required production configuration

`MEM0_CONFIG_JSON` is required in production. It must configure Mem0's
pgvector vector store to use the dedicated `memory` schema and the
`bdlh_memory_service` role. The JSON remains provider-specific intentionally,
because Mem0's provider configuration changes independently of this service.

All internal HTTP calls require both `X-Internal-Token` and
`X-Authenticated-User-Id`. The service rejects a request when its payload or
path user ID differs from the authenticated user scope.

If recall fails, the orchestrator treats it as an empty result. Candidate
ingestion is asynchronous and never blocks answer generation.

上下文构建器接收的是一次运行冻结后的记忆结果，不在压缩过程中重复查询本服务。
公开展示环境不连接本服务。

## 测试与部署

```powershell
uv sync --extra dev
uv run pytest -q
```

本地依赖部署和环境变量见 [deploy/README.md](../deploy/README.md)。
