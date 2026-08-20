# 后续数据库变更

数据库初始化完成后，新增字段、索引、约束或数据修复脚本放在本目录，由维护者手动执行。

文件名使用日期和普通说明：

```text
20260821-add-run-cancel-reason.sql
20260825-add-context-cache-index.sql
```

每份脚本必须：

1. 使用 `BEGIN` 和 `COMMIT`；
2. 设置合理的 `lock_timeout` 和 `statement_timeout`；
3. 在成功结束前写入 `touchstone.database_changes`；
4. 明确对现有数据的处理方式；
5. 说明是否需要先停止 Data 或 Engine 服务；
6. 执行前完成备份，失败后不得直接修改已执行脚本。

示例登记语句：

```sql
INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('20260821-add-run-cancel-reason.sql', '为运行记录增加取消原因');
```

本目录不使用 Flyway 版本号，也不会被应用自动扫描。
