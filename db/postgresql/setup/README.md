# 新数据库初始化

本目录的 `init.sql` 是唯一初始化入口，由维护者手动执行一次，应用启动不会自动运行。
它由原 01–08 八份脚本按序合并而成，每段保留独立事务并在成功后写入
`touchstone.database_changes`（共 8 段登记）。使用 `ON_ERROR_STOP=1` 执行时失败即停，
已成功提交的段不会因后续段失败而回滚——重跑前先按登记确认进度。

## 本地 Docker 执行

先只启动 PostgreSQL：

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d postgres
```

在仓库根目录执行：

```powershell
Get-Content -Raw db/postgresql/setup/init.sql |
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T postgres `
    sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

初始化完成后再启动其他私有服务：

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d data engine web
```

## 托管 PostgreSQL 执行

在本机安装 `psql`，把连接串放入本次终端的专用环境变量：

```powershell
$env:TOUCHSTONE_PG_URL = 'postgresql://user:password@host:5432/database?sslmode=require'

psql $env:TOUCHSTONE_PG_URL -v ON_ERROR_STOP=1 -f db/postgresql/setup/init.sql
```

不要把真实连接串写入仓库文件或命令记录文档。

## 执行后确认

```sql
SELECT script_name, description, applied_at, applied_by
FROM touchstone.database_changes
ORDER BY applied_at;
```

正常结果应该有八行（每段一行）。如果不足八行，说明有段未执行成功，
处理失败原因后不能直接启动 Data 服务。

## 脚本分段内容

| 段 | 原脚本 | 作用 |
|---:|---|---|
| 1 | `01-create-base-tables` | 创建 schema、执行记录表和基础业务表 |
| 2 | `02-seed-fixed-cases` | 写入首批固定用例、默认变体和数据快照 |
| 3 | `03-create-agent-comparison-tables` | 创建 Agent 版本、上下文策略、调用、指标和发布表 |
| 4 | `04-seed-agent-and-context-catalog` | 写入三种 Agent 和四种上下文策略 |
| 5 | `05-create-execution-detail-tables` | 创建守卫拦截明细和模型输入消息快照表 |
| 6 | `06-create-accounts-tables` | 创建所有者账号、登录会话和审计表 |
| 7 | `07-create-tool-catalog-tables` | 创建工具目录表并写入操作证、工具集、能力和技能 |
| 8 | `08-seed-tool-fixtures` | 写入 A/B 评测冻结工具返回（ab-eval 数据集） |

## 创建初始所有者账号

`init.sql` 不写入任何账号或密码。首个所有者账号由维护者在目标数据库上手动
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

- `init.sql` 只用于一个尚未建立 Touchstone 表的新数据库；
- 不要在已初始化的数据库上重复执行 `init.sql`；
- 已投入使用的数据库发生变化时，在 `../changes/` 新增脚本，不回改 `init.sql`；
- 正式环境执行前先备份，并确认连接的是目标数据库。
