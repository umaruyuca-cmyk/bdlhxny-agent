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

/* ── 结果页渲染 ─────────────────────────────────────────── */

const REPORT = {
  batch_id: "fa37d76f-0000-0000-0000-000000000000",
  experiment_type: "agent-implementation",
  generated_at: "2026-08-21T14:00:00+08:00",
  git_commit: "abc1234",
  model: "glm-4.7-flash",
  fixed_conditions: { case_ids: ["a", "b"], runs_per_case: 1, tool_data: "frozen", variable: "agent_mode" },
  groups: [
    { key: "baseline-tool-calling", label: "裸 tool calling", valid_runs: 1, invalid_runs: 0,
      metrics: { tool_selection_rate: 0.5, hallucination_rate: null, forbidden_leak_rate: 0, number_hallucination_rate: 0.2, c1_violation_rate: 0, c2_violation_rate: 0, mean_rounds: 2, mean_tokens: 900, median_duration_ms: 3000, p95_duration_ms: 3500, task_success_rate: null } },
    { key: "full-system", label: "完整工程模式", valid_runs: 1, invalid_runs: 0,
      metrics: { tool_selection_rate: 1, hallucination_rate: 0, forbidden_leak_rate: 0, number_hallucination_rate: 0, c1_violation_rate: 0, c2_violation_rate: 0, mean_rounds: 1.5, mean_tokens: 700, median_duration_ms: 2500, p95_duration_ms: 2800, task_success_rate: null } },
  ],
  outcome_counts: { win: 3, regress: 1, tie: 6, both_fail: 8, invalid: null },
  cases: [
    { id: "research-01", category: "金融研究", message: "宁德时代现在什么价",
      groups: { "baseline-tool-calling": { correct: 0, hallucinated: 1, total: 1, estimated_token_runs: 0 }, "full-system": { correct: 1, hallucinated: 0, total: 1, estimated_token_runs: 1 } } },
    { id: "chat-01", category: "闲聊", message: "你好",
      groups: { "baseline-tool-calling": { correct: 1, hallucinated: 0, total: 1, estimated_token_runs: 0 }, "full-system": { correct: 1, hallucinated: 0, total: 1, estimated_token_runs: 0 } } },
  ],
};

test("组指标总表：null 指标渲染未运行，不出现改善/回归结论词", () => {
  const html = S.renderGroupTable(REPORT);
  assert.match(html, /工具选择准确率/);
  assert.match(html, /未运行/);
  assert.match(html, /metric-def/); // 指标定义就地展开
  assert.doesNotMatch(html, /改善|回归/);
});

test("五类结局徽章齐全，无效显示未运行", () => {
  const html = S.renderOutcomeBadges(REPORT);
  for (const label of ["获胜", "退化", "平局", "双方失败", "无效"]) assert.match(html, new RegExp(label));
  assert.match(html, /无效 <strong>未运行<\/strong>/);
});

test("分场景明细支持场景筛选", () => {
  assert.equal(S.categories(REPORT).join(","), "金融研究,闲聊");
  const all = S.renderCaseRows(REPORT, null);
  assert.match(all, /research-01/);
  assert.match(all, /chat-01/);
  const filtered = S.renderCaseRows(REPORT, "闲聊");
  assert.match(filtered, /chat-01/);
  assert.doesNotMatch(filtered, /research-01/);
  assert.match(all, /≈1/); // 估算口径运行数标记
});
