# 部署

## 本地完整环境

包含 PostgreSQL、`data`、`engine` 和 `web`：

```powershell
Copy-Item deploy/.env.example deploy/.env
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d postgres
```

第一次部署时，按照 [`db/postgresql/setup/README.md`](../db/postgresql/setup/README.md)
手动执行数据库初始化脚本 `init.sql`（单一入口，含全部建表与种子数据）。
数据库准备完成后再启动应用：

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build data engine web
```

Engine 端口默认只绑定 `127.0.0.1`。如果通过网关提供私有运行页面，网关仍需做项目所有者登录；运行接口本身已要求账号会话令牌，不应暴露给浏览器或公开站。

## 云环境

`docker-compose.cloud.yml` 使用已经发布的三个镜像，并连接托管 PostgreSQL。先使用
`psql` 按 [`db/postgresql/setup/README.md`](../db/postgresql/setup/README.md) 初始化托管数据库，
然后启动服务：

```powershell
docker compose --env-file deploy/.env.cloud -f deploy/docker-compose.cloud.yml up -d
```

云环境需要设置 `IMAGE_REGISTRY`、`IMAGE_TAG`、`DATABASE_URL`、`DATABASE_USER`、`DATABASE_PASSWORD`、`DATA_INTERNAL_TOKEN`、`LLM_API_KEY` 和 `GIT_COMMIT`。数据服务和运行服务应放在私有网络；只让展示站或经过登录保护的反向代理暴露公网端口。

## 纯公开展示

```powershell
docker compose -f deploy/docker-compose.public.yml up -d --build
```

这个配置只有静态 Nginx，不含数据库、模型密钥、数据服务或运行 API，因此访问页面不会产生 token 消耗。

## 配置检查

```powershell
docker compose --env-file deploy/.env.ci -f deploy/docker-compose.yml config -q
docker compose --env-file deploy/.env.ci -f deploy/docker-compose.cloud.yml config -q
docker compose -f deploy/docker-compose.public.yml config -q
```
