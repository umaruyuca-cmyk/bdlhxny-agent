#!/usr/bin/env node
/**
 * 发布脚本 v1（薄版，P3-5 首版）：engine 批次工件 → showcase-data 静态产物。
 *
 * 只做两件事：字段白名单投影 + schema/禁止字段校验。
 * 诚实约束：
 * - 运行有效性分类未实现（P3-1）→ validity 一律 UNCLASSIFIED，
 *   index.latest_batch.is_formal 恒 false，首页不把批次当正式结果；
 * - task_success_rate 与 invalid 分类不可得 → null（页面显示「未运行」）；
 * - 单次运行工件（runs/{id}.json）本版不产出：现有批次工件不含逐运行时间线，
 *   伪造单次运行身份不诚实；待 P3-1 统一工件落地后接入。
 * 幂等：重跑覆盖写，不修改源工件。
 */

import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadSchema, validate, scanForbidden } from "../schema/validate.mjs";

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = path.resolve(WEB_ROOT, "..");
const DEFAULT_ARTIFACTS = path.join(REPO_ROOT, "engine", "var", "artifacts");
const OUTPUT_DIR = path.join(WEB_ROOT, "public", "showcase-data");

const GROUP_KEYS = {
  baseline: { key: "baseline-tool-calling", label: "裸 tool calling" },
  react: { key: "langgraph-react", label: "LangGraph 官方 ReAct" },
  treatment: { key: "full-system", label: "完整工程模式" },
};
const METRIC_FIELDS = [
  "tool_selection_rate", "hallucination_rate", "forbidden_leak_rate", "number_hallucination_rate",
  "c1_violation_rate", "c2_violation_rate", "mean_rounds", "mean_tokens",
  "median_duration_ms", "p95_duration_ms",
];

export async function publishBatch({ artifactsDir = DEFAULT_ARTIFACTS, batchId, gitCommit, outputDir = OUTPUT_DIR }) {
  if (!gitCommit) throw new Error("git_commit 缺失：发布必须携带代码版本（--git-commit 或 GIT_COMMIT）");
  const id = batchId ?? (await latestBatchId(artifactsDir));
  const artifact = JSON.parse(await readFile(path.join(artifactsDir, `${id}.json`), "utf8"));
  if (!artifact.generated_at) throw new Error("工件缺少 generated_at，拒绝发布");

  const publishedAt = new Date().toISOString();
  const batch = projectBatchReport(artifact, id, gitCommit);
  const index = projectIndex(artifact, id, gitCommit, publishedAt);

  for (const [name, payload] of [["index", index], ["batch-report", batch]]) {
    validate(payload, await loadSchema(name));
    const forbidden = scanForbidden(payload);
    if (forbidden.length > 0) throw new Error(`公开工件含禁止字段：${forbidden.join(", ")}`);
  }

  const batchDir = path.join(outputDir, "batches", id);
  await mkdir(batchDir, { recursive: true });
  await writeJson(path.join(batchDir, "report.json"), batch);
  await writeJson(path.join(outputDir, "index.json"), index);

  // 写后回读复验（磁盘态与内存态一致才算发布成功）
  for (const [file, name] of [
    [path.join(outputDir, "index.json"), "index"],
    [path.join(batchDir, "report.json"), "batch-report"],
  ]) {
    validate(JSON.parse(await readFile(file, "utf8")), await loadSchema(name));
  }
  return { batchId: id, files: 2 };
}

async function latestBatchId(artifactsDir) {
  const entries = await readdir(artifactsDir);
  const batchFiles = entries.filter((name) => /^[0-9a-f-]{36}\.json$/.test(name));
  if (batchFiles.length === 0) throw new Error(`工件目录无批次文件：${artifactsDir}（先运行评测批次）`);
  let newest = { name: "", mtime: 0 };
  for (const name of batchFiles) {
    const mtime = (await stat(path.join(artifactsDir, name))).mtimeMs;
    if (mtime > newest.mtime) newest = { name, mtime };
  }
  return newest.name.replace(/\.json$/, "");
}

function projectBatchReport(artifact, batchId, gitCommit) {
  const groups = Object.entries(artifact.groups ?? {})
    .filter(([source]) => GROUP_KEYS[source])
    .map(([source, metrics]) => {
      const total = artifact.case_count * artifact.runs_per_case;
      const errored = Math.min(Number.isFinite(metrics.error_count) ? metrics.error_count : 0, total);
      const projected = { task_success_rate: null };
      for (const field of METRIC_FIELDS) projected[field] = num(metrics[field]);
      return {
        key: GROUP_KEYS[source].key,
        label: GROUP_KEYS[source].label,
        valid_runs: total - errored,
        invalid_runs: errored,
        metrics: pick(projected, ["task_success_rate", ...METRIC_FIELDS]),
      };
    });

  const cases = (artifact.cases ?? []).map((item) => {
    const groupsOut = {};
    for (const [source, agg] of Object.entries(item)) {
      if (!GROUP_KEYS[source]) continue;
      groupsOut[GROUP_KEYS[source].key] = {
        correct: int(agg.correct),
        hallucinated: int(agg.hallucinated),
        total: int(agg.total),
        duration_p50_ms: num(agg.duration_p50_ms),
        duration_p95_ms: num(agg.duration_p95_ms),
        estimated_token_runs: agg.estimated_token_runs === undefined ? 0 : int(agg.estimated_token_runs),
      };
    }
    return { id: str(item.id), category: str(item.category), message: str(item.message), groups: groupsOut };
  });

  return {
    batch_id: batchId,
    experiment_type: "agent-implementation",
    generated_at: artifact.generated_at,
    git_commit: gitCommit,
    model: str(artifact.model),
    fixed_conditions: {
      case_ids: cases.map((c) => c.id),
      runs_per_case: int(artifact.runs_per_case),
      tool_data: artifact.executor === "frozen" ? "frozen" : "live",
      variable: "agent_mode",
    },
    groups,
    outcome_counts: outcomeCounts(cases),
    cases,
  };
}

/** 五类结局：按题比较裸调用 vs 完整模式的 correct 计数（确定性可回算）。 */
function outcomeCounts(cases) {
  let win = 0, regress = 0, tie = 0, bothFail = 0;
  for (const item of cases) {
    const base = item.groups["baseline-tool-calling"];
    const full = item.groups["full-system"];
    if (!base || !full) continue;
    const b = base.correct > 0, t = full.correct > 0;
    if (b && t) tie += 1;
    else if (t) win += 1;
    else if (b) regress += 1;
    else bothFail += 1;
  }
  return { win, regress, tie, both_fail: bothFail, invalid: null };
}

function projectIndex(artifact, batchId, gitCommit, publishedAt) {
  return {
    generated_at: artifact.generated_at,
    formal_batches: [],
    latest_batch: {
      batch_id: batchId,
      published_at: publishedAt,
      is_formal: false,
      case_count: int(artifact.case_count),
      runs_per_case: int(artifact.runs_per_case),
      model: str(artifact.model),
      git_commit: gitCommit,
      validity_gate: {
        met: false,
        reason: "运行有效性分类未实现（P3-1）：本批次仅作过程参考，不构成正式基准",
      },
    },
  };
}

async function writeJson(file, payload) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, JSON.stringify(payload, null, 2) + "\n", "utf8");
}

const num = (v) => (Number.isFinite(v) ? v : null);
const int = (v) => (Number.isFinite(v) ? Math.trunc(v) : 0);
const str = (v) => (v === null || v === undefined ? "" : String(v));
const pick = (obj, keys) => Object.fromEntries(keys.map((k) => [k, obj[k]]));

// ── CLI ────────────────────────────────────────────────────────────────

function arg(name) {
  const index = process.argv.indexOf(`--${name}`);
  return index > -1 ? process.argv[index + 1] : undefined;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  publishBatch({
    artifactsDir: arg("artifacts") ? path.resolve(arg("artifacts")) : DEFAULT_ARTIFACTS,
    batchId: arg("batch"),
    gitCommit: arg("git-commit") ?? process.env.GIT_COMMIT,
  })
    .then((result) => {
      console.log(`published: batch=${result.batchId} files=${result.files} → ${path.relative(REPO_ROOT, OUTPUT_DIR)}`);
    })
    .catch((error) => {
      console.error(`发布失败: ${error.message}`);
      process.exitCode = 1;
    });
}
