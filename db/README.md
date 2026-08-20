# db

本目录是 Touchstone 数据库的唯一来源，保存数据库总体设计、需要人工执行的
PostgreSQL 脚本、只读查询示例和维护规则。

Data 服务不会自动建表或升级数据库。数据库初始化和后续变更必须由维护者明确选择
脚本并手动执行。

## 目录结构

```text
db/
├─ README.md
├─ docs/
│  └─ 01-数据库总体设计.md
└─ postgresql/
   ├─ README.md
   ├─ setup/
   │  ├─ README.md
   │  ├─ 01-create-base-tables.sql
   │  ├─ 02-seed-fixed-cases.sql
   │  ├─ 03-create-agent-comparison-tables.sql
   │  ├─ 04-seed-agent-and-context-catalog.sql
   │  ├─ 05-create-execution-detail-tables.sql
   │  └─ 06-create-accounts-tables.sql
   ├─ changes/
   │  └─ README.md
   ├─ queries/
   │  ├─ README.md
   │  └─ reporting-examples.sql
   └─ maintenance/
      └─ README.md
```

## 目录职责

| 目录 | 用途 |
|---|---|
| `docs/` | 数据边界、表关系、字段规则和数据保留设计 |
| `postgresql/setup/` | 新数据库第一次初始化时按顺序手动执行的 SQL |
| `postgresql/changes/` | 数据库投入使用后的增量修改脚本 |
| `postgresql/queries/` | 报表和排障使用的只读查询 |
| `postgresql/maintenance/` | 备份、恢复、归档和清理规则 |

## 执行边界

- 应用启动不会执行 `db/` 中的任何文件；
- Docker 镜像不包含自动迁移逻辑；
- SQL 不打包到 Data 服务 JAR；
- 只有数据库维护者可以手动执行结构和初始化脚本；
- 公开 Web 服务不连接 PostgreSQL；
- 仓库不保存数据库密码、备份文件或真实用户数据。

具体执行命令见 [`postgresql/setup/README.md`](./postgresql/setup/README.md)。
