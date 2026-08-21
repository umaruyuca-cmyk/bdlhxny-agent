import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";

/** shared.js 以纯脚本挂 globalThis，Node 侧 eval 加载后测纯函数。 */
const source = await readFile(new URL("../public/showcase/shared.js", import.meta.url), "utf8");
(0, eval)(source);
const S = globalThis.SHOWCASE;

const GATED_INDEX = {
  generated_at: "2026-08-21T14:00:00+08:00",
  formal_batches: [],
  latest_batch: {
    batch_id: "fa37d76f-0000-0000-0000-000000000000",
    published_at: "2026-08-21T15:00:00+08:00",
    is_formal: false,
    case_count: 18, runs_per_case: 1,
    model: "glm-4.7-flash", git_commit: "abc1234",
    validity_gate: { met: false, reason: "运行有效性分类未实现（P3-1）" },
  },
};

test("homeState 三态：无数据 / 未达门槛 / 正式批次", () => {
  assert.equal(S.homeState(null).kind, "nodata");
  assert.equal(S.homeState({ latest_batch: null }).kind, "nodata");
  assert.equal(S.homeState(GATED_INDEX).kind, "gated");
  const formal = structuredClone(GATED_INDEX);
  formal.latest_batch.is_formal = true;
  formal.formal_batches = [formal.latest_batch.batch_id];
  assert.equal(S.homeState(formal).kind, "formal");
});

test("未达门槛横幅：明示非正式与原因，不出现结论性改善文案", () => {
  const html = S.renderHomeBanner(S.homeState(GATED_INDEX));
  assert.match(html, /未达有效样本门槛/);
  assert.match(html, /P3-1/);
  assert.match(html, /\/showcase\/results/);
  assert.doesNotMatch(html, /改善|回归/);
});

test("无数据与未达门槛状态：指标卡一律「未运行」", () => {
  for (const state of [{ kind: "nodata" }, S.homeState(GATED_INDEX)]) {
    const html = S.renderStatCards(state, null);
    assert.match(html, /未运行/);
    assert.doesNotMatch(html, /%\d|\d%/);
  }
});

test("正式批次指标卡：基线→对照渲染百分数", () => {
  const state = { kind: "formal", batch: GATED_INDEX.latest_batch };
  const report = {
    groups: [
      { key: "baseline-tool-calling", metrics: { tool_selection_rate: 0.5, number_hallucination_rate: 0.2 } },
      { key: "full-system", metrics: { tool_selection_rate: 1.0, number_hallucination_rate: 0 } },
    ],
  };
  const html = S.renderStatCards(state, report);
  assert.match(html, /基线 50%/);
  assert.match(html, /→<\/span><span class="stat-now">100%/);
  assert.match(html, /未运行/);
});

test("esc 转义 HTML，pct/num 的 null 渲染为未运行", () => {
  assert.equal(S.esc('<a href="x">&'), "&lt;a href=&quot;x&quot;&gt;&amp;");
  assert.equal(S.pct(null), "未运行");
  assert.equal(S.pct(0.651), "65%");
  assert.equal(S.num(null), "未运行");
  assert.equal(S.num(1200, "ms"), "1200ms");
});
