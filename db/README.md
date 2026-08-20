# 数据库脚本

本目录保存 sentinel-data 和 sentinel-memory 所需的数据库结构。应用启动时不自动
修改生产数据库；本地 Compose 只在新建数据卷时执行初始化脚本。

## 目录

| 路径 | 用途 |
|---|---|
| `postgresql/bootstrap.sql` | 创建数据服务、记忆服务角色和 schema |
| `postgresql/schema/` | PostgreSQL 全量表结构 |
| `postgresql/seed/` | 合成演示数据和固定目录种子 |
| `mysql/user_schema.sql` | 可选的旧 MySQL 用户表结构 |

Touchstone 默认使用 PostgreSQL。MySQL 脚本仅用于需要兼容旧认证数据的部署，不是
固定用例评测的必需依赖。

## 本地初始化

[deploy/docker-compose.yml](../deploy/docker-compose.yml) 会在新的 PostgreSQL 数据卷
上调用 [deploy/postgres/00-init.sh](../deploy/postgres/00-init.sh)，按固定顺序执行
bootstrap 和 schema 文件。

如果数据卷已经存在，初始化脚本不会再次执行。需要调整结构时，应明确编写迁移或
创建新的开发数据卷，不能依靠重启容器覆盖数据库。

## 数据边界

- 固定评测优先使用合成快照；
- 真实用户数据不能进入公开运行工件；
- memory schema 只允许记忆服务角色访问；
- 公开静态站不连接数据库。
