import { mkdtemp, mkdir, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { publishBatch } from "../scripts/publish-showcase.mjs";
import { loadSchema, validate, scanForbidden } from "../schema/validate.mjs";

/** v1 发布管线：白名单投影 + schema/禁止字段校验 + UNCLASSIFIED 诚实标注。 */

const ARTIFACT = {
  generated_at: "2026-08-21T14:00:00+08:00",
  model: "glm-4.7-flash",
  executor: "frozen",
  runs_per_case: 1,
  case_count: 2,
  groups: {
    baseline: {
      tool_selection_rate: 0.5, hallucination_rate: 0.1, forbidden_leak_rate: 0,
      number_hallucination_rate: 0.2, c1_violation_rate: 0, c2_violation_rate: 0,
      mean_rounds: 2, mean_tokens: 900, median_duration_ms: 3000, p95_duration_ms: 3500,
      error_count: 1,
    },
    treatment: {
      tool_selection_rate: 1.0, hallucination_rate: 0, forbidden_leak_rate: 0,
      number_hallucination_rate: 0, c1_violation_rate: 0, c2_violation_rate: 0,
      mean_rounds: 1.5, mean_tokens: 700, median_duration_ms: 2500, p95_duration_ms: 2800,
      error_count: 0,
    },
  },
  cases: [
    {
      id: "research-01", category: "金融研究", message: "宁德时代现在什么价",
      baseline: { correct: 0, hallucinated: 1, total: 1, duration_p50_ms: 3000, duration_p95_ms: 3000, estimated_token_runs: 0 },
      treatment: { correct: 1, hallucinated: 0, total: 1, duration_p50_ms: 2000, duration_p95_ms: 2000, estimated_token_runs: 1 },
      lineage: [{ tool: "market.get_realtime_quote", store: "frozen-fixture", query: { symbol: "300750" }, result: { price: 185.5 } }],
    },
    {
      id: "chat-01", category: "闲聊", message: "你好",
      baseline: { correct: 1, hallucinated: 0, total: 1 },
      treatment: { correct: 1, hallucinated: 0, total: 1 },
    },
  ],
};

const BATCH_ID = "01234567-89ab-cdef-0123-456789abcdef";
let workDir;

beforeEach(async () => {
  workDir = await mkdtemp(path.join(tmpdir(), "showcase-publish-"));
  await mkdir(path.join(workDir, "artifacts"), { recursive: true });
  await writeArtifact(ARTIFACT);
});

afterEach(async () => {
  await rm(workDir, { recursive: true, force: true });
});

async function writeArtifact(payload) {
  await writeFile(path.join(workDir, "artifacts", `${BATCH_ID}.json`), JSON.stringify(payload), "utf8");
}

async function runPublish(overrides = {}) {
  return publishBatch({
    artifactsDir: path.join(workDir, "artifacts"),
    gitCommit: "abc1234",
    outputDir: path.join(workDir, "out"),
    ...overrides,
  });
}

test("发布产出 index 与批次报告，均通过 schema 与禁止字段校验", async () => {
  await runPublish();
  const index = JSON.parse(await readFile(path.join(workDir, "out", "index.json"), "utf8"));
  const report = JSON.parse(await readFile(path.join(workDir, "out", "batches", BATCH_ID, "report.json"), "utf8"));
  validate(index, await loadSchema("index"));
  validate(report, await loadSchema("batch-report"));
  assert.deepEqual(scanForbidden(index), []);
  assert.deepEqual(scanForbidden(report), []);
});

test("诚实标注：is_formal=false、validity_gate 未达标、task_success_rate=null", async () => {
  await runPublish();
  const index = JSON.parse(await readFile(path.join(workDir, "out", "index.json"), "utf8"));
  assert.equal(index.latest_batch.is_formal, false);
  assert.equal(index.latest_batch.validity_gate.met, false);
  assert.match(index.latest_batch.validity_gate.reason, /P3-1/);
  assert.deepEqual(index.formal_batches, []);
  const report = JSON.parse(await readFile(path.join(workDir, "out", "batches", BATCH_ID, "report.json"), "utf8"));
  assert.equal(report.groups[0].metrics.task_success_rate, null);
  assert.equal(report.outcome_counts.invalid, null);
});

test("五类结局按题可回算：win=1、tie=1、regress=0、both_fail=0", async () => {
  await runPublish();
  const report = JSON.parse(await readFile(path.join(workDir, "out", "batches", BATCH_ID, "report.json"), "utf8"));
  assert.deepEqual(
    { win: report.outcome_counts.win, regress: report.outcome_counts.regress, tie: report.outcome_counts.tie, both_fail: report.outcome_counts.both_fail },
    { win: 1, regress: 0, tie: 1, both_fail: 0 },
  );
});

test("工件含敏感/未知字段时不泄漏进产物（白名单投影）", async () => {
  const dirty = structuredClone(ARTIFACT);
  dirty.groups.baseline.system_prompt = "内部完整系统提示";
  dirty.groups.baseline.api_key = "sk-secret";
  await writeArtifact(dirty);
  await runPublish();
  const reportText = await readFile(path.join(workDir, "out", "batches", BATCH_ID, "report.json"), "utf8");
  assert.doesNotMatch(reportText, /system_prompt|sk-secret/);
  const indexText = await readFile(path.join(workDir, "out", "index.json"), "utf8");
  assert.doesNotMatch(indexText, /system_prompt|sk-secret/);
});

test("git_commit 或 generated_at 缺失即拒绝发布", async () => {
  await assert.rejects(() => runPublish({ gitCommit: undefined }), /git_commit 缺失/);
  const noTime = structuredClone(ARTIFACT);
  delete noTime.generated_at;
  await writeArtifact(noTime);
  await assert.rejects(() => runPublish(), /generated_at/);
});

test("error_count 映射为 invalid_runs，valid_runs=total-error", async () => {
  await runPublish();
  const report = JSON.parse(await readFile(path.join(workDir, "out", "batches", BATCH_ID, "report.json"), "utf8"));
  const baseline = report.groups.find((g) => g.key === "baseline-tool-calling");
  assert.deepEqual({ valid: baseline.valid_runs, invalid: baseline.invalid_runs }, { valid: 1, invalid: 1 });
});
