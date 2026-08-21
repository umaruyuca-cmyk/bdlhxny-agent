import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

/**
 * /lab 私有侧契约：页面存在且可调用运行 API；但公开镜像物理排除 lab/，
 * 公开页面（/showcase、/docs）不得链接 /lab、不得出现后端调用。
 */

const PUBLIC_PAGES = [
  ["", "index"],
  ["showcase", "index"], ["showcase", "results"], ["showcase", "runs"],
  ["experiment", "index"], ["experiment", "cases"], ["experiment", "reproduce"],
  ["context", "index"], ["context", "design"], ["context", "results"],
  ["judging", "index"], ["judging", "judge"], ["judging", "invalid"],
  ["engine", "index"], ["engine", "loading"], ["engine", "catalog"],
  ["engine", "governance"], ["engine", "guardrail"], ["engine", "tools"],
  ["ops", "index"], ["ops", "run-api"], ["ops", "artifacts"], ["ops", "deploy"], ["ops", "roadmap"],
];

async function readPublicPage(dir, page) {
  const rel = dir ? `../public/${dir}/${page}.html` : `../public/${page}.html`;
  return readFile(new URL(rel, import.meta.url), "utf8");
}

test("/lab 登录页与批次页存在，只在此处允许表单与运行 API 调用", async () => {
  const login = await readFile(new URL("../public/lab/login.html", import.meta.url), "utf8");
  const index = await readFile(new URL("../public/lab/index.html", import.meta.url), "utf8");
  for (const html of [login, index]) {
    assert.match(html, /\/api\/v1\//, "lab 页面需要调用运行 API");
  }
  assert.match(login, /sessionStorage/, "登录令牌只进 sessionStorage");
  assert.match(index, /case_ids/, "批次页只提交题号与实验配置");
  // 提交体只允许五个键（与 EvalBatchRequest 对齐），不得夹带问题正文
  const literal = index.match(/payload = \{([^}]*)\}/);
  const literalKeys = literal ? [...literal[1].matchAll(/\b([a-z_]+)\s*:/g)].map((m) => m[1]) : [];
  const assignKeys = [...index.matchAll(/payload\.([a-z_]+)\s*=/g)].map((m) => m[1]);
  assert.deepEqual(
    [...new Set([...literalKeys, ...assignKeys])].sort(),
    ["case_ids", "include_react", "max_total_tokens", "model", "runs"],
  );
  assert.doesNotMatch(index, /payload\.?(message|prompt|system_prompt|tools)/, "不得提交问题正文、提示词或自定义工具");
});

test("/lab 批次过程管理（任务四）：取消、预算与运行详情下钻均已接线", async () => {
  const index = await readFile(new URL("../public/lab/index.html", import.meta.url), "utf8");
  assert.match(index, /\/api\/v1\/jobs\/" \+ jobId \+ "\/cancel/, "取消按钮需调用协作取消端点");
  assert.match(index, /max_total_tokens/, "表单需提供批次 token 上限");
  assert.match(index, /\/api\/v1\/batches\//, "批次完成后可下钻运行列表");
  assert.match(index, /\/api\/v1\/runs\/" \+ runId \+ "\/detail/, "运行列表可下钻单次运行逐步明细");
  for (const table of ["modelCalls", "toolCalls", "guardrailChecks", "events", "measurements"]) {
    assert.ok(index.includes(table), `运行详情需渲染 ${table}`);
  }
});

test("公开页面（/showcase、/docs）不链接 /lab、不出现后端调用", async () => {
  for (const [dir, page] of PUBLIC_PAGES) {
    const html = await readPublicPage(dir, page);
    assert.ok(!html.includes('href="/lab'), `${dir || "root"}/${page}.html 不得链接私有运行台`);
    if (`${dir}/${page}` === "ops/run-api") {
      // 私有 API 的文档页:正文列出端点是职责,但不得发起任何真实调用
      assert.doesNotMatch(html, /fetch\(|XMLHttpRequest|axios/, "ops/run-api 文档页不得发起真实后端调用");
    } else {
      assert.doesNotMatch(html, /\/api\/v1\//, `${dir}/${page}.html 不得出现后端 API`);
    }
    assert.doesNotMatch(html, /<input|<form|<textarea/, `${dir}/${page}.html 不得出现输入控件`);
  }
});

test("公开镜像构建物理排除 lab/，私有镜像保留", async () => {
  const dockerfilePublic = await readFile(new URL("../Dockerfile.public", import.meta.url), "utf8");
  assert.match(dockerfilePublic, /rm -rf public\/lab/, "公开构建必须删除 lab 目录");
  const dockerfilePrivate = await readFile(new URL("../Dockerfile", import.meta.url), "utf8");
  assert.match(dockerfilePrivate, /COPY public\//, "私有镜像照常复制 public/");
  assert.doesNotMatch(dockerfilePrivate, /rm -rf/, "私有镜像不得排除 lab");

  const publicCompose = await readFile(new URL("../../deploy/docker-compose.public.yml", import.meta.url), "utf8");
  assert.match(publicCompose, /Dockerfile\.public/, "公开 compose 必须使用排除版 Dockerfile");
});

test("登录令牌不出现在公开数据契约的禁止字段清单之外的页面脚本中", async () => {
  // showcase-data 由发布脚本做 FORBIDDEN_KEYS 扫描；这里守页面侧：
  // 公开页面脚本不读 sessionStorage/localStorage（无会话概念）
  for (const [dir, page] of PUBLIC_PAGES) {
    const html = await readPublicPage(dir, page);
    assert.doesNotMatch(html, /sessionStorage|localStorage/, `${dir || "root"}/${page}.html 无会话概念`);
  }
});
