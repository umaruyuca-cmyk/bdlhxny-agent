# sentinel-data

sentinel-data 是 Touchstone 私有运行环境的数据服务，负责认证、当前用户范围、
持仓、账户、风险画像和运行数据。它不部署到公开展示环境。

## 与上下文构建的关系

上下文构建器不直接查询业务表。一次固定用例运行先通过本服务取得数据，再生成带
snapshot_id、时间和 hash 的冻结快照；同一组对照必须复用同一快照。

sentinel-data 只提供事实和权限边界，不负责摘要、token 预算或模型调用。

## 本地测试

~~~powershell
Copy-Item src/main/resources/application.example.yml src/main/resources/application.yml
mvn -B -ntp test
~~~

application.yml 是本地文件，不进入 Git。部署变量和数据库初始化见
[deploy/README.md](../deploy/README.md) 与 [db/README.md](../db/README.md)。

## 安全边界

- 客户端不能自行指定任意用户身份；
- Python 服务到 Java 服务使用独立内部凭证；
- 公开静态站不能访问本服务；
- 固定评测默认读取合成快照，不能混用真实用户数据。
