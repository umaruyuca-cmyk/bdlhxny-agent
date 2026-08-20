# Touchstone 部署说明

本目录只包含当前 touchstone 分支实际具备的部署能力，不复用 main 分支的旧聊天系统编排。

## 两种部署边界

### 公开展示

公开环境只部署 sentinel-console。它读取静态展示数据，不连接模型、数据服务或记忆服务，访问页面不会产生 token 消耗。

~~~powershell
docker compose -f deploy/docker-compose.public.yml up -d --build
~~~

### 私有运行依赖

私有环境需要 PostgreSQL、RocketMQ、sentinel-data 和 sentinel-memory，为后续固定用例运行 API 提供数据快照和长期记忆。

~~~powershell
Copy-Item deploy/.env.example deploy/.env
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build
~~~

当前 sentinel-engine 仍是评测和上下文算法库，尚未实现只接受 case_id 的私有运行 API，因此不放入 Compose。等 docs/05 的阶段 5 完成后再增加 engine 服务，不能恢复旧的任意聊天 API。

## 安全要求

- deploy/.env 只保存在本地，不提交 Git；
- 所有对外端口默认绑定 127.0.0.1；
- 公开 Compose 不包含数据库、消息队列、模型密钥或运行后端；
- 示例密码只用于本地开发，正式环境必须替换；
- 数据库首次初始化后，修改密码变量不会自动修改已有数据卷中的角色密码。

## 配置校验

~~~powershell
docker compose --env-file deploy/.env.ci -f deploy/docker-compose.yml config -q
docker compose -f deploy/docker-compose.public.yml config -q
~~~
