/* Touchstone 实证层共享渲染函数（纯函数，无 DOM 依赖，可被 Node 测试加载）。
 * 约定：null 一律渲染为「未运行」；未过有效门槛的批次不做结论性文案。 */
(function (global) {
  "use strict";

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }

  function pct(value) {
    return value == null ? "未运行" : Math.round(value * 100) + "%";
  }

  function num(value, suffix) {
    return value == null ? "未运行" : String(value) + (suffix || "");
  }

  /** 首页状态：无数据 / 最新批次未达门槛 / 正式批次。 */
  function homeState(index) {
    if (!index || !index.latest_batch) return { kind: "nodata" };
    var latest = index.latest_batch;
    if (latest.is_formal && index.formal_batches && index.formal_batches.length > 0) {
      return { kind: "formal", batch: latest };
    }
    return { kind: "gated", batch: latest };
  }

  function renderHomeBanner(state) {
    if (state.kind === "nodata") {
      return '<div class="placeholder-block">等待发布数据：尚无批次发布。发布流程见<a href="/docs/">架构讲解</a>——项目所有者运行对照批次后经发布脚本投影到 showcase-data。</div>';
    }
    if (state.kind === "formal") {
      return '<div class="note"><strong>最新正式批次</strong>：' + esc(state.batch.batch_id.slice(0, 8)) +
        " · " + esc(state.batch.model) + " · " + esc(state.batch.generated_at) + " · commit " + esc(state.batch.git_commit) + "</div>";
    }
    var b = state.batch;
    return '<div class="note"><strong>最新批次未达有效样本门槛（非正式）</strong>：' + esc(b.validity_gate && b.validity_gate.reason || "有效性未分类") +
      '。批次为 ' + esc(b.model) + " · " + esc(b.generated_at) + " · commit " + esc(b.git_commit) +
      '，可前往<a href="/showcase/results">对照结果</a>查看过程数据。</div>';
  }

  function renderStatCards(state, report) {
    var cards = [
      { label: "工具选择准确率", group: "full-system", field: "tool_selection_rate", better: "high" },
      { label: "数字幻觉率", group: "full-system", field: "number_hallucination_rate", better: "low" },
      { label: "无效运行数", value: null, hint: "有效性分类未实现（P3-1）" }
    ];
    if (state.kind !== "formal" || !report) {
      return cards.map(function (c) {
        return '<div class="stat-card"><div class="stat-label">' + c.label + '</div><div class="stat-vals"><span class="stat-now">未运行</span></div><div class="stat-hint">正式批次发布后展示</div></div>';
      }).join("");
    }
    var byKey = {};
    (report.groups || []).forEach(function (g) { byKey[g.key] = g; });
    var base = byKey["baseline-tool-calling"], full = byKey["full-system"];
    return cards.map(function (c) {
      var html = '<div class="stat-card"><div class="stat-label">' + c.label + "</div>";
      if (c.group) {
        var b = base && base.metrics[c.field], t = full && full.metrics[c.field];
        html += '<div class="stat-vals"><span class="stat-base">基线 ' + pct(b) + '</span><span class="stat-arrow">→</span><span class="stat-now">' + pct(t) + "</span></div>";
      } else {
        html += '<div class="stat-vals"><span class="stat-now">' + num(c.value) + "</span></div>";
      }
      html += '<div class="stat-hint">' + esc(c.hint || "完整工程模式 vs 裸 tool calling") + "</div></div>";
      return html;
    }).join("");
  }

  /** 指标定义（评测文档 §7），表头 <details> 就地展开。 */
  var METRIC_DEFS = [
    { field: "tool_selection_rate", label: "工具选择准确率", def: "实际成功工具集合与期望工具集合一致的比例", fmt: pct },
    { field: "hallucination_rate", label: "幻觉工具率", def: "调用了当次工具目录中不存在名称的比例", fmt: pct },
    { field: "forbidden_leak_rate", label: "越权泄漏率", def: "未授权运行成功访问受限工具或数据的比例", fmt: pct },
    { field: "number_hallucination_rate", label: "数字幻觉率", def: "答案中的事实性数字无法在工具结果或数据快照中找到的比例", fmt: pct },
    { field: "c1_violation_rate", label: "C-1 违规率", def: "违反交易边界语义（C-1）的比例", fmt: pct },
    { field: "c2_violation_rate", label: "C-2 违规率", def: "违反适当性结论口径（C-2）的比例", fmt: pct },
    { field: "mean_rounds", label: "平均轮次", def: "每个有效运行的模型调用轮次均值", fmt: function (v) { return num(v == null ? null : Number(v).toFixed(1)); } },
    { field: "mean_tokens", label: "平均 token", def: "prompt + completion 的均值（估算口径运行数见分场景明细）", fmt: function (v) { return num(v); } },
    { field: "median_duration_ms", label: "p50 时长", def: "总时长中位数", fmt: function (v) { return num(v, "ms"); } },
    { field: "p95_duration_ms", label: "p95 时长", def: "总时长 95 分位", fmt: function (v) { return num(v, "ms"); } }
  ];

  var OUTCOME_DEFS = [
    { key: "win", label: "获胜", def: "完整模式正确且基线错误的题数" },
    { key: "regress", label: "退化", def: "基线正确且完整模式错误的题数" },
    { key: "tie", label: "平局", def: "双方都正确的题数" },
    { key: "both_fail", label: "双方失败", def: "双方都错误的题数" },
    { key: "invalid", label: "无效", def: "有效性分类未实现（P3-1）前的诚实占位", def2: null }
  ];

  /** 组指标总表：只列各组实测值，不做组间结论（有效性未分类时尤甚）。 */
  function renderGroupTable(report) {
    if (!report || !report.groups || report.groups.length === 0) {
      return '<div class="placeholder-block">未运行。</div>';
    }
    var head = '<tr><th>指标</th>' + report.groups.map(function (g) {
      return "<th>" + esc(g.label) + '<details class="metric-def"><summary>定义</summary><p>' +
        "组键 " + esc(g.key) + "；有效 " + g.valid_runs + " / 无效 " + g.invalid_runs + " 次运行</p></details></th>";
    }).join("") + "</tr>";
    var rows = METRIC_DEFS.map(function (m) {
      return "<tr><td>" + esc(m.label) + '<details class="metric-def"><summary>定义</summary><p>' + esc(m.def) +
        "</p></details></td>" + report.groups.map(function (g) {
          return "<td>" + m.fmt(g.metrics ? g.metrics[m.field] : null) + "</td>";
        }).join("") + "</tr>";
    }).join("");
    return "<table><thead>" + head + "</thead><tbody>" + rows + "</tbody></table>";
  }

  function renderOutcomeBadges(report) {
    if (!report || !report.outcome_counts) return '<div class="placeholder-block">未运行。</div>';
    return OUTCOME_DEFS.map(function (o) {
      var v = report.outcome_counts[o.key];
      return '<span class="outcome-badge outcome-' + o.key + '" title="' + esc(o.def) + '">' +
        esc(o.label) + " <strong>" + num(v) + "</strong></span>";
    }).join(" ");
  }

  /** 分场景明细：每题每组的 correct/total，可筛场景。 */
  function renderCaseRows(report, categoryFilter) {
    var cases = (report && report.cases) || [];
    var groups = (report && report.groups) || [];
    var rows = cases
      .filter(function (c) { return !categoryFilter || c.category === categoryFilter; })
      .map(function (c) {
        var cells = groups.map(function (g) {
          var agg = c.groups && c.groups[g.key];
          if (!agg) return "<td>未运行</td>";
          var est = agg.estimated_token_runs > 0 ? ' <span class="est-flag" title="其中含 chars/4 估算口径的运行数">≈' + agg.estimated_token_runs + "</span>" : "";
          return "<td>" + agg.correct + "/" + agg.total + est + "</td>";
        }).join("");
        return "<tr><td>" + esc(c.id) + "</td><td>" + esc(c.category) + "</td><td>" + esc(c.message) + "</td>" + cells + "</tr>";
      }).join("");
    if (!rows) return '<tr><td colspan="' + (groups.length + 3) + '">该场景下没有已发布用例。</td></tr>';
    return rows;
  }

  function renderCaseTable(report, categoryFilter) {
    if (!report || !report.cases || report.cases.length === 0) return '<div class="placeholder-block">未运行。</div>';
    var groups = report.groups || [];
    var head = "<tr><th>题号</th><th>场景</th><th>问题</th>" +
      groups.map(function (g) { return "<th>" + esc(g.label) + "</th>"; }).join("") + "</tr>";
    return "<table><thead>" + head + "</thead><tbody>" + renderCaseRows(report, categoryFilter) + "</tbody></table>";
  }

  function categories(report) {
    var seen = {};
    ((report && report.cases) || []).forEach(function (c) { seen[c.category] = true; });
    return Object.keys(seen).sort();
  }

  global.SHOWCASE = {
    esc: esc,
    pct: pct,
    num: num,
    homeState: homeState,
    renderHomeBanner: renderHomeBanner,
    renderStatCards: renderStatCards,
    renderGroupTable: renderGroupTable,
    renderOutcomeBadges: renderOutcomeBadges,
    renderCaseTable: renderCaseTable,
    renderCaseRows: renderCaseRows,
    categories: categories,
    METRIC_DEFS: METRIC_DEFS
  };
})(typeof window !== "undefined" ? window : globalThis);
