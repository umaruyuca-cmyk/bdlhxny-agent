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

数据库结构由 `src/main/resources/db/migration/` 中的 Flyway 迁移维护。

## 本地测试

```powershell
mvn -B -ntp test
```

## 内部鉴权

所有 `/internal/v1/**` 接口都要求 `X-Internal-Token`。未配置
`DATA_INTERNAL_TOKEN` 时接口关闭。健康检查 `/actuator/health` 不需要内部令牌。
