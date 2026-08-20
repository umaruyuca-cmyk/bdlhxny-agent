import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

/**
 * Touchstone 展示站契约：仅 /docs/ 静态文档页，无交互入口、无后端调用。
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

test("文档站八页齐备且不调用后端 API", async () => {
  for (const page of DOCS_PAGES) {
    const html = await readFile(new URL(`../public/docs/${page}.html`, import.meta.url), "utf8");
    assert.match(html, /docs\.css/, `${page}.html 必须引用 docs.css`);
    assert.doesNotMatch(html, /\/api\/v1\//, `${page}.html 不得出现后端 API 调用`);
  }
});

test("根路径与文档页互相指向", async () => {
  const index = await readFile(new URL("../public/index.html", import.meta.url), "utf8");
  assert.match(index, /\/docs\//);
  const docsIndex = await readFile(new URL("../public/docs/index.html", import.meta.url), "utf8");
  assert.match(docsIndex, /docs\.css/);
});
