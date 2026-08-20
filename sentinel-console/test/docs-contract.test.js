import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

/**
 * Touchstone 展示站契约：顶栏页面导航 + 侧栏本页目录；纯静态、零后端调用。
 */

const DOCS_PAGES = [
  "index",
  "agents",
  "skill",
  "tools",
  "comparison",
  "eval",
  "cases",
  "results",
];

test("八页共享顶栏导航壳（品牌 + 两组下拉 + GitHub）", async () => {
  for (const page of DOCS_PAGES) {
    const html = await readFile(new URL(`../public/docs/${page}.html`, import.meta.url), "utf8");
    assert.match(html, /docs\.css/, `${page}.html 必须引用 docs.css`);
    assert.match(html, /docs\.js/, `${page}.html 必须引入共享导航脚本`);
    assert.match(html, /class="topnav"/, `${page}.html 必须有顶栏导航`);
    assert.match(html, /Touchstone/, `${page}.html 必须有品牌名`);
    // 两组页面导航的八条链接全部在壳内
    for (const href of ["/docs/", "/docs/comparison", "/docs/eval", "/docs/cases", "/docs/results",
      "/docs/agents", "/docs/skill", "/docs/tools"]) {
      assert.ok(html.includes(`href="${href}"`), `${page}.html 顶栏缺少 ${href}`);
    }
    assert.match(html, /docsSide/, `${page}.html 必须有本页目录侧栏`);
  }
});

test("展示站零后端依赖、无交互输入", async () => {
  for (const page of DOCS_PAGES) {
    const html = await readFile(new URL(`../public/docs/${page}.html`, import.meta.url), "utf8");
    assert.doesNotMatch(html, /\/api\/v1\//, `${page}.html 不得出现后端 API 调用`);
    assert.doesNotMatch(html, /<input|<form/, `${page}.html 不得出现输入控件`);
  }
});

test("根路径与文档页互相指向", async () => {
  const index = await readFile(new URL("../public/index.html", import.meta.url), "utf8");
  assert.match(index, /\/docs\//);
  const docsIndex = await readFile(new URL("../public/docs/index.html", import.meta.url), "utf8");
  assert.match(docsIndex, /docs\.css/);
  // 首页 hero 指标卡读取真实运行工件
  assert.match(docsIndex, /report\.json/, "概览页指标卡必须消费 report.json");
});
