# data

Touchstone 的内部数据服务。它是固定用例、数据快照、运行记录、上下文压缩记录和
评测证据的运行时数据入口，只在私有环境部署。

它不执行 Agent、不调用模型、不选择工具，也不生成公开页面。

## 数据范围

- 固定用例、不可变版本、变体和固定多步输入；
- 冻结数据快照；
- 批次和单次运行；
- 原始上下文条目、处理决定和实际模型消息；
- 运行事件、评测结果和工件元数据。

完整表关系、字段边界、JSONB 使用规则和数据保留策略见
[`db/docs/01-数据库总体设计.md`](../db/docs/01-数据库总体设计.md)。

当前基础设计只依赖 PostgreSQL，不启用向量扩展。固定问题和固定长上下文按版本读取，
不需要使用相似度检索才能运行。

Data 服务不会建表或修改表结构。首次部署前，维护者必须按照
[`db/postgresql/setup/README.md`](../db/postgresql/setup/README.md) 手动初始化数据库；
后续数据库修改也由维护者执行 `db/postgresql/changes/` 中明确选择的脚本。

如果数据库尚未初始化，健康检查仍可能成功，但业务查询会因为缺少表而失败。因此部署
流程必须先准备数据库，再启动 Data、Engine 和私有运行入口。

## 本地测试

```powershell
mvn -B -ntp test
```

## 本地开发（经 SSH 隧道）

数据源配置没有默认值，缺 `DATABASE_URL` / `DATABASE_USER` / `DATABASE_PASSWORD`
任一变量时启动直接失败（fail-fast）。本地开发的标准做法是先开 SSH 隧道连到云端，
再显式传变量启动。

隧道由本机脚本建立（属本机工件，含服务器地址与账号，**不放入仓库**）：
本地 `5432` 转发云端 PostgreSQL、本地 `18080` 转发云端 data 服务 8080。
隧道窗口关闭即断开。

隧道就绪后启动 data：

```powershell
$env:DATABASE_URL = "jdbc:postgresql://127.0.0.1:5432/touchstone"
$env:DATABASE_USER = "touchstone"
$env:DATABASE_PASSWORD = "<隧道目标库密码>"
$env:DATA_INTERNAL_TOKEN = "<内部令牌>"
mvn spring-boot:run
```

engine 本地连云端 data 时设：

```powershell
$env:DATA_API_BASE_URL = "http://127.0.0.1:18080/internal/v1"
$env:DATA_INTERNAL_TOKEN = "<内部令牌>"
```

## 内部鉴权

所有 `/internal/v1/**` 接口都要求 `X-Internal-Token`。未配置
`DATA_INTERNAL_TOKEN` 时接口关闭。健康检查 `/actuator/health` 不需要内部令牌。
