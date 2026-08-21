import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

/**
 * /showcase 实证层契约：四页共享壳、与 /docs 双向可达、纯静态零后端、无输入控件。
 */

const SHOWCASE_PAGES = ["index", "results", "runs", "context"];
const SHOWCASE_LINKS = ["/showcase/", "/showcase/results", "/showcase/runs", "/showcase/context"];
const DOCS_PAGES = ["index", "agents", "skill", "tools", "comparison", "eval", "cases", "results"];

async function readShowcase(page) {
  return readFile(new URL(`../public/showcase/${page}.html`, import.meta.url), "utf8");
}

test("实证层四页共享导航壳", async () => {
  for (const page of SHOWCASE_PAGES) {
    const html = await readShowcase(page);
    assert.match(html, /docs\.css/, `${page}.html 必须引用 docs.css`);
    assert.match(html, /docs\.js/, `${page}.html 必须引入共享导航脚本`);
    assert.match(html, /class="topnav"/, `${page}.html 必须有顶栏导航`);
    for (const href of SHOWCASE_LINKS) {
      assert.ok(html.includes(`href="${href}"`), `${page}.html 顶栏缺少 ${href}`);
    }
    assert.ok(html.includes('href="/docs/"'), `${page}.html 必须回链架构讲解层`);
    assert.match(html, /docsSide/, `${page}.html 必须有本页目录侧栏`);
  }
});

test("架构讲解层八页均含实证展示导航组（双向可达）", async () => {
  for (const page of DOCS_PAGES) {
    const html = await readFile(new URL(`../public/docs/${page}.html`, import.meta.url), "utf8");
    assert.ok(html.includes('href="/showcase/"'), `${page}.html 缺少实证概览入口`);
    assert.ok(html.includes('href="/showcase/results"'), `${page}.html 缺少对照结果入口`);
  }
});

test("实证层零后端依赖、无交互输入", async () => {
  for (const page of SHOWCASE_PAGES) {
    const html = await readShowcase(page);
    assert.doesNotMatch(html, /\/api\/v1\//, `${page}.html 不得出现后端 API 调用`);
    assert.doesNotMatch(html, /<input|<form|<textarea/, `${page}.html 不得出现输入控件`);
  }
});

test("实证层数据只读 showcase-data，根路径指向 showcase", async () => {
  for (const page of SHOWCASE_PAGES) {
    const html = await readShowcase(page);
    const fetches = [...html.matchAll(/fetch\((["'])([^"']+)\1/g)].map((m) => m[2]);
    for (const url of fetches) {
      assert.ok(url.startsWith("/showcase-data/"), `${page}.html 的 fetch 只允许 /showcase-data/ 路径：${url}`);
    }
  }
  const root = await readFile(new URL("../public/index.html", import.meta.url), "utf8");
  assert.match(root, /\/showcase\//, "根跳转页必须指向 /showcase/");
});

test("未运行数据渲染为诚实占位而非估算值", async () => {
  const results = await readShowcase("results");
  assert.match(results, /未运行/, "结果页无数据时必须显示未运行");
  const context = await readShowcase("context");
  assert.match(context, /未运行/, "上下文页无数据时必须显示未运行");
});
