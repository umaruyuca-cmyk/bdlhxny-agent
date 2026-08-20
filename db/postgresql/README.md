# PostgreSQL

Touchstone 私有环境只使用 PostgreSQL，当前不需要 `pgvector`。固定用例、固定上下文和
工具返回都通过明确编号与版本读取，保证不同 Agent 使用相同输入。

阅读顺序：

1. [`../docs/01-数据库总体设计.md`](../docs/01-数据库总体设计.md)
2. [`setup/README.md`](./setup/README.md)
3. [`changes/README.md`](./changes/README.md)
4. [`queries/README.md`](./queries/README.md)
5. [`maintenance/README.md`](./maintenance/README.md)

所有业务对象放在 `touchstone` schema 中。时间使用 `TIMESTAMPTZ`，耗时使用毫秒，
内容 hash 使用 `sha256:<hex>` 格式。

Data 服务只连接和读写已经准备好的数据库，不负责执行这些 SQL。
