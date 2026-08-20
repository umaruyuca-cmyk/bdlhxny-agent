# 新数据库初始化

本目录中的六份 SQL 由维护者手动执行，应用启动不会自动运行。

## 执行顺序

| 顺序 | 文件 | 作用 |
|---:|---|---|
| 1 | `01-create-base-tables.sql` | 创建 schema、执行记录表和基础业务表 |
| 2 | `02-seed-fixed-cases.sql` | 写入首批固定用例、默认变体和数据快照 |
| 3 | `03-create-agent-comparison-tables.sql` | 创建 Agent 版本、上下文策略、调用、指标和发布表 |
| 4 | `04-seed-agent-and-context-catalog.sql` | 写入三种 Agent 和四种上下文策略 |
| 5 | `05-create-execution-detail-tables.sql` | 创建守卫拦截明细和模型输入消息快照表 |
| 6 | `06-create-accounts-tables.sql` | 创建所有者账号、登录会话和审计表 |

必须按顺序执行。每份脚本都使用事务，并在成功后写入
`touchstone.database_changes`。执行失败时整份脚本回滚。

## 本地 Docker 执行

先只启动 PostgreSQL：

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d postgres
```

在仓库根目录逐个执行：

```powershell
Get-Content -Raw db/postgresql/setup/01-create-base-tables.sql |
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T postgres `
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

Get-Content -Raw db/postgresql/setup/02-seed-fixed-cases.sql |
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T postgres `
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

Get-Content -Raw db/postgresql/setup/03-create-agent-comparison-tables.sql |
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T postgres `
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

Get-Content -Raw db/postgresql/setup/04-seed-agent-and-context-catalog.sql |
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T postgres `
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

Get-Content -Raw db/postgresql/setup/05-create-execution-detail-tables.sql |
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T postgres `
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

Get-Content -Raw db/postgresql/setup/06-create-accounts-tables.sql |
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T postgres `
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

六份脚本完成后再启动其他私有服务：

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d data engine web
```

## 托管 PostgreSQL 执行

在本机安装 `psql`，把连接串放入本次终端的专用环境变量：

```powershell
$env:TOUCHSTONE_PG_URL = 'postgresql://user:password@host:5432/database?sslmode=require'

psql $env:TOUCHSTONE_PG_URL -v ON_ERROR_STOP=1 -f db/postgresql/setup/01-create-base-tables.sql
psql $env:TOUCHSTONE_PG_URL -v ON_ERROR_STOP=1 -f db/postgresql/setup/02-seed-fixed-cases.sql
psql $env:TOUCHSTONE_PG_URL -v ON_ERROR_STOP=1 -f db/postgresql/setup/03-create-agent-comparison-tables.sql
psql $env:TOUCHSTONE_PG_URL -v ON_ERROR_STOP=1 -f db/postgresql/setup/04-seed-agent-and-context-catalog.sql
psql $env:TOUCHSTONE_PG_URL -v ON_ERROR_STOP=1 -f db/postgresql/setup/05-create-execution-detail-tables.sql
psql $env:TOUCHSTONE_PG_URL -v ON_ERROR_STOP=1 -f db/postgresql/setup/06-create-accounts-tables.sql
```

不要把真实连接串写入仓库文件或命令记录文档。

## 执行后确认

```sql
SELECT script_name, description, applied_at, applied_by
FROM touchstone.database_changes
ORDER BY applied_at;
```

正常结果应该有六行。如果少于六行，先处理失败脚本，不能跳过顺序直接启动 Data 服务。

## 创建初始所有者账号

六份脚本只建表，不写入任何账号或密码。首个所有者账号由维护者在目标数据库上手动
创建，密码通过变量或交互输入，不进入 Git：

```sql
\set owner_password '请替换为强密码'
INSERT INTO touchstone.accounts (id, username, display_name, password_hash)
VALUES (gen_random_uuid(), 'owner', '项目所有者',
        crypt(:'owner_password', gen_salt('bf', 12)));
```

登录由私有运行服务负责：校验 `password_hash`、签发随机会话令牌，数据库只保存令牌
的 `sha256:<hex>` hash。仓库不保存密码、明文令牌或任何账号凭证。

## 注意事项

- 初始化脚本只用于一个尚未建立 Touchstone 表的新数据库；
- 不要重复执行已经登记成功的脚本；
- 不要修改已经在任何环境执行过的脚本；
- 已投入使用的数据库发生变化时，在 `../changes/` 新增脚本；
- 正式环境执行前先备份，并确认连接的是目标数据库。
