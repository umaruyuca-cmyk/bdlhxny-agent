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

  global.SHOWCASE = {
    esc: esc,
    pct: pct,
    num: num,
    homeState: homeState,
    renderHomeBanner: renderHomeBanner,
    renderStatCards: renderStatCards
  };
})(typeof window !== "undefined" ? window : globalThis);
