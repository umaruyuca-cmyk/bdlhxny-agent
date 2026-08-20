# sentinel-console（Touchstone 展示站）

纯静态 Nginx 展示站，无构建工具链、无后端依赖：`/` 重定向到 `/docs/` 文档站（架构概览、Agent 循环、工具目录与治理、三种架构对照、评测口径、固定题库、评测结果）。

> Touchstone 分支只保留实验对照的展示面；Sentinel 完整前端（dashboard / lab / chat）见 `main` 分支。

## 本地预览

```powershell
npm run dev
```

打开 `http://127.0.0.1:8082/docs/`。

## 测试

```bash
npm test
```

## 构建和启动

```bash
docker build -t touchstone-console:1.0.0 .

docker run -d \
  --name touchstone-console \
  --restart unless-stopped \
  --network host \
  touchstone-console:1.0.0
```
