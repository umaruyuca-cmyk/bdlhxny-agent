import { test } from "node:test";
import assert from "node:assert/strict";
import { loadSchema, validate, scanForbidden, ValidationError } from "../schema/validate.mjs";

/** 合法样例（字段值与结构对齐 schema；数值不代表真实实验结果）。 */

const indexSample = {
  generated_at: "2026-08-21T12:00:00+08:00",
  formal_batches: [],
  latest_batch: {
    batch_id: "b1",
    published_at: "2026-08-21T12:00:00+08:00",
    is_formal: false,
    case_count: 18,
    runs_per_case: 1,
    model: "glm-4.7-flash",
    git_commit: "abc1234",
    validity_gate: { met: false, reason: "运行有效性分类未实现（P3-1）" },
  },
};

const batchSample = {
  batch_id: "b1",
  experiment_type: "agent-implementation",
  generated_at: "2026-08-21T12:00:00+08:00",
  git_commit: "abc1234",
  model: "glm-4.7-flash",
  fixed_conditions: { case_ids: ["research-01"], runs_per_case: 1, tool_data: "frozen", variable: "agent_mode" },
  groups: [
    {
      key: "baseline-tool-calling",
      label: "裸 tool calling",
      valid_runs: 1,
      invalid_runs: 0,
      metrics: {
        task_success_rate: null,
        tool_selection_rate: 1.0,
        hallucination_rate: 0,
        forbidden_leak_rate: 0,
        number_hallucination_rate: 0,
        c1_violation_rate: 0,
        c2_violation_rate: 0,
        mean_rounds: 2,
        mean_tokens: 1000,
        median_duration_ms: 3000,
        p95_duration_ms: 3000,
      },
    },
  ],
  outcome_counts: { win: null, regress: null, tie: null, both_fail: null, invalid: null },
  cases: [
    {
      id: "research-01",
      category: "金融研究",
      message: "宁德时代现在什么价",
      groups: {
        "baseline-tool-calling": { correct: 1, hallucinated: 0, total: 1, duration_p50_ms: 3000, estimated_token_runs: 0 },
      },
      run_ids: { "baseline-tool-calling": ["b1-baseline-research-01-1"] },
    },
  ],
};

const runSample = {
  run_id: "b1-baseline-research-01-1",
  batch_id: "b1",
  case_id: "research-01",
  status: "COMPLETE",
  validity: "UNCLASSIFIED",
  experiment: { agent_mode: "baseline-tool-calling", context_strategy: null, model: "glm-4.7-flash", repeat_index: 1 },
  sections: {
    fixed_input: { message: "宁德时代现在什么价", scene: "research", authenticated: false, history_count: 0, allowed_tools: null },
    context: null,
    visible_tools: null,
    model_steps: [{ seq: 1, decision: "call_tool", latency_ms: 800 }],
    code_decisions: null,
    tool_results: [{ seq: 1, name: "market.get_realtime_quote", status: "SUCCESS", summary: { price: 185.5 }, source: "fixture://ab-eval", data_time: "2026-08-19T14:32:00+08:00" }],
    output_checks: null,
    final_result: { answer_excerpt: "现价 185.50 元", citations: null, audit_codes: [], judgment: null },
    cost: { duration_ms: 3000, prompt_tokens: 1000, completion_tokens: 50, tokens_estimated: false },
  },
};

test("三个 schema 的合法样例全部通过", async () => {
  validate(indexSample, await loadSchema("index"));
  validate(batchSample, await loadSchema("batch-report"));
  validate(runSample, await loadSchema("run"));
});

test("缺必填字段被拒绝", async () => {
  const schema = await loadSchema("run");
  const broken = structuredClone(runSample);
  delete broken.sections.cost;
  assert.throws(() => validate(broken, schema), ValidationError);
});

test("越权字段被拒绝（additionalProperties: false）", async () => {
  const schema = await loadSchema("run");
  const broken = structuredClone(runSample);
  broken.extra_field = 1;
  assert.throws(() => validate(broken, schema), /extra_field/);
});

test("禁止字段扫描：系统提示与密钥命中即失败", () => {
  assert.deepEqual(scanForbidden(runSample), []);
  const dirty = structuredClone(runSample);
  dirty.sections.fixed_input.system_prompt = "内部完整提示";
  assert.ok(scanForbidden(dirty).includes("system_prompt"));
  const dirtyKey = structuredClone(batchSample);
  dirtyKey.api_key = "sk-xxx";
  assert.ok(scanForbidden(dirtyKey).includes("api_key"));
});

test("未运行字段 null 合法；非 null 枚举外取值非法", async () => {
  const runSchema = await loadSchema("run");
  const nullable = structuredClone(runSample);
  nullable.sections.context = null;
  validate(nullable, runSchema);

  const badEnum = structuredClone(runSample);
  badEnum.validity = "MAYBE";
  assert.throws(() => validate(badEnum, runSchema), /MAYBE/);
});

test("比率字段越界 [0,1] 被拒绝", async () => {
  const schema = await loadSchema("batch-report");
  const broken = structuredClone(batchSample);
  broken.groups[0].metrics.tool_selection_rate = 1.5;
  assert.throws(() => validate(broken, schema), /最大值/);
});
