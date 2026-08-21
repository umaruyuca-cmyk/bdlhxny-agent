import http from "node:http";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const host = process.env.HOST || "127.0.0.1";
const port = Number.parseInt(process.env.PORT || "8082", 10);
const publicDirectory = fileURLToPath(new URL("./public/", import.meta.url));

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".ico", "image/x-icon"]
]);

/**
 * Touchstone 展示站：纯静态 /docs/ 文档页，无后端代理。
 */
const server = http.createServer(async (request, response) => {
  try {
    const requestUrl = new URL(request.url || "/", `http://${request.headers.host || host}`);
    await serveStatic(requestUrl.pathname, request, response);
  } catch (error) {
    console.error("前端开发服务器处理请求失败:", error);
    if (!response.headersSent) {
      response.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    }
    response.end("前端开发服务器内部错误");
  }
});

async function serveStatic(requestPath, request, response) {
  // / 指向实证层索引；/showcase、/docs、/lab 的 {page} 自动补 .html
  if (requestPath === "/docs" || requestPath === "/showcase" || requestPath === "/lab") {
    response.writeHead(302, { Location: requestPath + "/" });
    response.end();
    return;
  }
  let target = requestPath;
  if (requestPath === "/") target = "/showcase/index.html";
  else if (requestPath === "/showcase/" || requestPath === "/docs/") target = requestPath + "index.html";
  else if (requestPath.startsWith("/showcase/") || requestPath.startsWith("/docs/")) {
    const prefix = requestPath.startsWith("/showcase/") ? "/showcase/" : "/docs/";
    const pagePath = requestPath.slice(prefix.length);
    if (!pagePath.includes(".")) target = prefix + pagePath + ".html";
  }
  const decodedPath = decodeURIComponent(target);
  const relativePath = decodedPath.replace(/^[/\\]+/, "");
  const filePath = path.resolve(publicDirectory, relativePath);
  const publicRoot = path.resolve(publicDirectory);

  // 拒绝任何越过 public 目录的路径。
  if (filePath !== publicRoot && !filePath.startsWith(`${publicRoot}${path.sep}`)) {
    response.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("禁止访问");
    return;
  }

  let fileStats;
  try {
    fileStats = await stat(filePath);
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("页面不存在");
    return;
  }
  if (!fileStats.isFile()) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("页面不存在");
    return;
  }

  const contentType = contentTypes.get(path.extname(filePath).toLowerCase()) || "application/octet-stream";
  response.writeHead(200, {
    "Content-Type": contentType,
    "Content-Length": fileStats.size,
    "Cache-Control": "no-store"
  });
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  createReadStream(filePath).pipe(response);
}

server.listen(port, host, () => {
  console.log(`Touchstone 展示站: http://${host}:${port}/showcase/（架构讲解 /docs/）`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
