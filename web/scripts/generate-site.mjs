#!/usr/bin/env node
/**
 * 站点生成器(任务六:七模块信息架构落地)。
 *
 * 依据《站点信息架构与模块内容》:导航壳三层(模块顶栏 + 模块侧栏 + 本页目录),
 * 生成 首页 / 与 experiment/context/judging/engine/ops 五个模块共 21 页。
 * showcase 三页因含专属渲染脚本保持手维护(仅换壳);生成产物直接提交,
 * 公开部署无需构建步骤。重跑覆盖写:node scripts/generate-site.mjs
 */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PUBLIC = path.join(WEB_ROOT, "public");
const GITHUB = "https://github.com/umaruyuca-cmyk/bdlhxny-agent";

const MODULES = [
  { href: "/", label: "首页" },
  { href: "/showcase/", label: "实证展示" },
  { href: "/experiment/", label: "对照实验" },
  { href: "/context/", label: "上下文压缩" },
  { href: "/judging/", label: "评判标准" },
  { href: "/engine/", label: "引擎与治理" },
  { href: "/ops/", label: "数据与运行" },
];

/** 模块页面清单(侧栏上半;currentPath 高亮)。 */
const PAGES = {
  "/experiment/": [
    { href: "/experiment/", title: "实验设计" },
    { href: "/experiment/cases", title: "固定题库" },
    { href: "/experiment/reproduce", title: "如何复现" },
  ],
  "/context/": [
    { href: "/context/", title: "压缩算法" },
    { href: "/context/design", title: "长短对照设计" },
    { href: "/context/results", title: "用例结果" },
  ],
  "/judging/": [
    { href: "/judging/", title: "指标定义" },
    { href: "/judging/judge", title: "判官说明" },
    { href: "/judging/invalid", title: "无效运行与口径" },
  ],
  "/engine/": [
    { href: "/engine/", title: "Agent 循环" },
    { href: "/engine/loading", title: "工具装载" },
    { href: "/engine/catalog", title: "工具目录" },
    { href: "/engine/governance", title: "治理中间件" },
    { href: "/engine/guardrail", title: "输出护栏" },
    { href: "/engine/tools", title: "工具清单" },
  ],
  "/ops/": [
    { href: "/ops/", title: "数据库与冻结数据" },
    { href: "/ops/run-api", title: "私有运行 API" },
    { href: "/ops/artifacts", title: "工件与发布" },
    { href: "/ops/deploy", title: "部署与边界" },
    { href: "/ops/roadmap", title: "路线图" },
  ],
};

const esc = (v) => String(v).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

function shell({ title, description, currentPath, moduleKey, sections, extraScripts = "", homeShell = false }) {
  const topnav = MODULES.map(
    (m) => `<a href="${m.href}"${m.href === currentPath ? ' class="active"' : ""}>${m.label}</a>`,
  ).join("\n      ");
  let sidebarUpper = "";
  if (!homeShell) {
    const modulePages = PAGES[moduleKey] || [];
    sidebarUpper = `<h4>模块页面</h4>
    <ul>
      ${modulePages
        .map(
          (p) =>
            `<li><a href="${p.href}"${p.href === currentPath ? ' class="active"' : ""}>${p.title}</a></li>`,
        )
        .join("\n      ")}
    </ul>`;
  }
  const toc = homeShell
    ? ""
    : `<h4>本页目录</h4>
    <ul>
      ${sections.map((s) => `<li><a href="#${s.id}">${esc(s.title)}</a></li>`).join("\n      ")}
    </ul>`;
  const body = sections
    .map(
      (s) => `<h2 id="${s.id}">${esc(s.title)}</h2>
${s.html}`,
    )
    .join("\n    ");
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>${esc(title)} · Touchstone</title>
<meta name="description" content="${esc(description)}">
<link rel="stylesheet" href="/docs/docs.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="/"><span class="brand-mark">&#9672;</span><span class="brand-name">Touchstone</span><span class="brand-sub">Agent 编排模式对照实证平台</span></a>
    <nav class="topnav" aria-label="模块导航">
      ${topnav}
    </nav>
    <a class="topbar-gh" href="${GITHUB}" target="_blank" rel="noopener">GitHub</a>
    <button class="side-btn" id="sideBtn" type="button" aria-label="展开本页目录">本页目录</button>
  </div>
</header>
<div class="docs-layout">
  <aside class="docs-side" id="docsSide">
    ${sidebarUpper}
    ${toc}
    <div class="side-foot">模型提议，代码裁决——逐段可核验<br><a href="${GITHUB}" target="_blank" rel="noopener">bdlhxny-agent</a></div>
  </aside>
  <main class="docs-main">
    <h1>${esc(title)}</h1>
${body}
  </main>
</div>
<script src="/docs/docs.js"></script>
${extraScripts}
</body>
</html>
`;
}

// ── 首页(五节)──────────────────────────────────────────────────────────

const homeScript = `
<script src="/showcase/shared.js"></script>
<script>
(function () {
  "use strict";
  fetch("/showcase-data/index.json", { cache: "no-store" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (index) {
      if (!index || !index.latest_batch) return;
      var state = SHOWCASE.homeState(index);
      document.getElementById("homeBanner").innerHTML = SHOWCASE.renderHomeBanner(state);
      if (!state.kind) return;
      if (index.latest_batch.batch_id) {
        return fetch("/showcase-data/batches/" + index.latest_batch.batch_id + "/report.json", { cache: "no-store" })
          .then(function (res) { return res.ok ? res.json() : null; })
          .then(function (report) {
            document.getElementById("statCards").innerHTML = SHOWCASE.renderStatCards(state, report);
          });
      }
    })
    .catch(function () { /* 缺数据保持占位 */ });
})();
</script>`;

const HOME = {
  path: "index.html",
  title: "Touchstone · Agent 编排模式对照实证平台",
  description: "两大实验轨道:编排对照与上下文压缩对照;全部指标由代码断言产生,证据可回溯到单次运行。",
  homeShell: true,
  currentPath: "/",
  sections: [
    {
      id: "about",
      title: "项目定位与总结",
      html: `<p><strong>Touchstone</strong> 是一个 Agent 编排模式对照实证平台,不是公开聊天产品。核心主张是<strong>「模型提议,代码裁决」</strong>:语义判断归模型,权限、预算与红线由代码确定执行。</p>
<p>平台运行两类实验轨道:</p>
<ol>
  <li><strong>编排对照</strong>:同一 18 题固定题库、同一 LLM、同一份冻结工具数据,对照<strong>裸 tool calling</strong> / <strong>LangGraph 官方 ReAct</strong> / <strong>完整工程模式</strong>三组实现,量化工具选择准确率、幻觉工具率、越权泄漏率与合规违规率。</li>
  <li><strong>上下文压缩对照</strong>:同一长上下文用例,全量透传(<code>full</code>)与按预算压缩(<code>budgeted</code>)两种处理分别跑同一 Agent 逻辑、同一套评判标准,量化强制项保留率、关键事实出现与 token 净节省。</li>
</ol>
<p>证据方式:全部指标由代码断言产生(判官版本 <code>fixed-rules-v1</code>),无 LLM 判官;未运行的数字显示「未运行」,不以估算冒充实测。</p>
<div id="homeBanner"><div class="placeholder-block">正在读取已发布批次…</div></div>`,
    },
    {
      id: "architecture",
      title: "整体架构",
      html: `<p>四个服务,一条公私边界:</p>
<div class="flow">web(纯静态实证层) ｜ engine(私有运行 API + 三组执行器) ｜ data(题库/记录/发布登记) ｜ PostgreSQL(唯一真源)</div>
<p>公开部署只含静态站(物理排除 /lab);评测批次由项目所有者在私有侧发起,经发布校验投影为静态产物。</p>
<h3>一次运行(编排轨道)</h3>
<div class="flow">登录 → 按题号发起批次 → 拉取冻结工具数据 → 三组交错执行(九类事件 + 逐步明细落库) → 九段运行工件 → 发布校验(门槛/敏感扫描/hash 复算) → 公开静态展示</div>
<h3>上下文压缩链路(压缩轨道)</h3>
<div class="flow">长上下文条目 → 分类(强制/可压缩/仅引用/干扰) → 预算选择与压缩 → 工作上下文 → 同一 Agent 循环 → 同一判官 → 处理报告进工件</div>
<p><strong>变量隔离</strong>:编排对照用冻结数据隔离执行质量、金标路由隔离路由误差;压缩对照只变上下文处理策略,其余全部固定。</p>`,
    },
    {
      id: "banks",
      title: "两套题库",
      html: `<ul>
  <li><strong>编排对照 18 题</strong>:闲聊 / 知识 / 拦截 / 金融研究 / 组合 / 适合度 / 多步指代,存 PostgreSQL 为唯一真源,见<a href="/experiment/cases">固定题库</a>。</li>
  <li><strong>上下文压缩 6 套长上下文用例</strong>(金融 3 / 其他 2 / 闲聊 1),每套 <code>full-raw</code> 全量与 <code>budgeted-comp</code> 压缩两条变体,均入库为唯一真源,见<a href="/context/design">长短对照设计</a>。</li>
</ul>`,
    },
    {
      id: "status",
      title: "当前进展与关键数字",
      html: `<p>已落地:统一运行工件与九类事件落库、上下文构建器接入与压缩对照执行、有效样本门槛与交错运行、批次过程管理(取消/预算)、发布全量校验与正式批次认定、七模块信息架构。演示门禁(阶段 8)按计划留待功能收尾后。</p>
<div id="statCards"><div class="placeholder-block">正在读取关键数字…</div></div>`,
    },
    {
      id: "repo",
      title: "仓库与复现",
      html: `<p>代码在 <a href="${GITHUB}" target="_blank" rel="noopener">GitHub</a>:<code>engine/</code>(被测内核与对照 runner)、<code>data/</code>(题库与记录服务)、<code>web/</code>(公开实证层与私有运行台)、<code>db/</code>(库结构与种子)。</p>
<p>复现三步:① 本地启动(见 <code>deploy/本地启动说明.md</code>);② 登录 /lab 按题号发起批次;③ <code>npm run publish:showcase -- --git-commit &lt;sha&gt;</code> 投影到公开层。工程门禁:<code>pytest + ruff</code>(engine)、<code>mvn test</code>(data)、<code>npm test</code>(web)。</p>`,
    },
  ],
  extraScripts: homeScript,
};

// ── 模块三:对照实验 ─────────────────────────────────────────────────────

const EXPERIMENT_DESIGN = {
  path: "experiment/index.html",
  title: "实验设计 · 对照实验",
  description: "编排对照的三组实现、冻结工具数据、金标路由与变量隔离。",
  moduleKey: "/experiment/",
  currentPath: "/experiment/",
  sections: [
    {
      id: "groups",
      title: "三组实现",
      html: `<p>同一题库、同一 LLM、同一份冻结工具数据,唯一变量是编排形态:</p>
<ul>
  <li><strong>裸 tool calling(基线)</strong>:LLM 原生 tool calling——全量工具、无 Guardrail、无 Selective Loading、无快路径、无输出护栏;</li>
  <li><strong>LangGraph 官方 ReAct(对照组)</strong>:<code>create_react_agent</code> 框架默认编排(ToolNode 统一执行,无治理;recursion_limit=50);</li>
  <li><strong>完整工程模式(本系统)</strong>:G1-G7 治理中间件 + Selective Tool Loading + 语义快路径 + 输出护栏。</li>
</ul>`,
    },
    {
      id: "frozen",
      title: "冻结工具数据与金标路由",
      html: `<p>三组共用同一份冻结返回(fixture 集 <code>ab-eval</code>,存 <code>fixture_tool_responses</code> 表),隔离外部服务与数据变化——工具执行质量不是变量。完整模式组用<strong>金标路由</strong>(按题库快路径标注分流),隔离路由误差,让对照只度量编排本身。</p>`,
    },
    {
      id: "interleave",
      title: "交错运行与重复",
      html: `<p>同一题的 N 次重复之间,三组顺序按确定性种子洗牌、题序按重复轮转,避免先跑组总是遇到更好的服务状态;同一种子可完整复现执行序。每题每组默认跑 5 次。</p>`,
    },
    {
      id: "process",
      title: "过程管理",
      html: `<p>批次执行中可<strong>协作取消</strong>(已开始的模型调用等待完成,不硬杀;已完成部分照常落库,批次以 CANCELLED 收尾);可设<strong>批次 token 上限</strong>,累计消耗达到后停止发起新运行(跳过计数与无效运行区分)。</p>`,
    },
    {
      id: "deeplink",
      title: "从汇总到单次运行",
      html: `<p>每个汇总数字都能回溯:批次报告的每格指标 → <code>run_key</code> → <code>run_id</code> → 单次运行的九段工件与事件流。见<a href="/showcase/runs">单次运行</a>与<a href="/ops/artifacts">工件与发布</a>。</p>`,
    },
  ],
};

const EXPERIMENT_CASES = {
  path: "experiment/cases.html",
  title: "固定题库 · 对照实验",
  description: "题库唯一真源在 PostgreSQL;本页读已发布批次产物渲染,不再手工维护第二份表格。",
  moduleKey: "/experiment/",
  currentPath: "/experiment/cases",
  sections: [
    {
      id: "source",
      title: "唯一真源",
      html: `<p>固定题库的唯一真源是 PostgreSQL(<code>case_definitions / case_versions / case_variants</code>),引擎评测与 /lab 题号列表都从数据服务读取。本页不再手工维护第二份表格,而是读取<strong>已发布批次产物</strong>(<code>showcase-data</code>)渲染:哪个用例进入过正式批次、每组表现如何,以发布数据为准;长上下文 ctx 用例入库并参与批次后会自动出现在下表。</p>`,
    },
    { id: "table", title: "用例总表(读发布产物)", html: `<div id="casesTable"><div class="placeholder-block">正在读取已发布批次…</div></div>` },
    {
      id: "reading",
      title: "怎么读",
      html: `<p>每行一题:题号 / 场景 / 问题原文,以及每组在最新已发布批次中的正确数(有效口径)。空白表示该题尚未进入任何已发布批次——不是不存在。场景覆盖闲聊、知识、交易拦截、注入防御、金融研究、组合、适合度、多步指代与长上下文。</p>`,
    },
  ],
  extraScripts: `
<script>
(function () {
  "use strict";
  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }
  fetch("/showcase-data/index.json", { cache: "no-store" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (index) {
      var latest = index && index.latest_batch;
      if (!latest) throw new Error("尚无已发布批次");
      document.getElementById("casesTable").innerHTML =
        '<p class="lab-note">读取批次 ' + esc(latest.batch_id.slice(0, 8)) +
        (latest.is_formal ? "(正式)" : "(未达门槛,过程参考)") + "</p>";
      return fetch("/showcase-data/batches/" + latest.batch_id + "/report.json", { cache: "no-store" });
    })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (report) {
      if (!report) throw new Error("批次产物缺失");
      var groups = report.groups || [];
      var head = "<tr><th>题号</th><th>场景</th><th>问题</th>" +
        groups.map(function (g) { return "<th>" + esc(g.label) + "</th>"; }).join("") + "</tr>";
      var rows = (report.cases || []).map(function (c) {
        var cells = groups.map(function (g) {
          var agg = c.groups && c.groups[g.key];
          return agg ? "<td>" + agg.correct + "/" + agg.total + "</td>" : "<td>未运行</td>";
        }).join("");
        return "<tr><td>" + esc(c.id) + "</td><td>" + esc(c.category) + "</td><td>" + esc(c.message) + "</td>" + cells + "</tr>";
      }).join("");
      document.getElementById("casesTable").innerHTML +=
        '<table><thead>' + head + "</thead><tbody>" + rows + "</tbody></table>";
    })
    .catch(function (err) {
      document.getElementById("casesTable").innerHTML =
        '<div class="placeholder-block">未运行:尚无已发布批次(' + esc(err.message) + ")。批次发布后本表自动出现。</div>";
    });
})();
</script>`,
};

const EXPERIMENT_REPRODUCE = {
  path: "experiment/reproduce.html",
  title: "如何复现 · 对照实验",
  description: "本地启动、发起批次、发布投影与门禁命令。",
  moduleKey: "/experiment/",
  currentPath: "/experiment/reproduce",
  sections: [
    {
      id: "steps",
      title: "复现三步",
      html: `<ol>
  <li><strong>本地启动</strong>:data(需数据库隧道与环境变量)→ engine(私有运行 API)→ web(<code>npm run dev</code>);细节见仓库 <code>deploy/本地启动说明.md</code>。</li>
  <li><strong>发起批次</strong>:登录 <code>/lab/</code>,勾选题号、次数(可含 ReAct 组、可设 token 上限),发起后可协作取消;批次完成后每题每组可在页面下钻到单次运行逐步明细。</li>
  <li><strong>发布</strong>:<code>npm run publish:showcase -- --git-commit &lt;sha&gt;</code>——发布校验(有效样本门槛、敏感扫描、hash 复算、引用解析)全部通过才落公开产物;需登记发布记录时配 <code>DATA_API_BASE_URL</code> 与 <code>DATA_INTERNAL_TOKEN</code>。</li>
</ol>`,
    },
    {
      id: "gates",
      title: "工程门禁",
      html: `<ul>
  <li>engine:<code>python -m pytest -q</code> 与 <code>python -m ruff check src tests</code></li>
  <li>data:<code>mvn -q test</code></li>
  <li>web:<code>npm test</code>(契约 + 渲染 + 发布管线测试)</li>
</ul>
<p>有效样本门槛:每组 VALID 运行数 ≥ 5(环境变量可覆盖)才可认定正式批次;未达门槛批次可运行可查看,但发布被拒。</p>`,
    },
  ],
};

// ── 模块四:上下文压缩 ───────────────────────────────────────────────────

const CONTEXT_ALGO = {
  path: "context/index.html",
  title: "压缩算法 · 上下文压缩",
  description: "四策略、条目分类、强制项保留与不可信数据包裹。",
  moduleKey: "/context/",
  currentPath: "/context/",
  sections: [
    {
      id: "strategies",
      title: "四种策略",
      html: `<ul>
  <li><strong>full</strong>:全量透传(预算内不压缩);</li>
  <li><strong>recent-n</strong>:只保留最近 N 条(窗口外省略);</li>
  <li><strong>single-summary</strong>:可压缩项合并为单摘要;</li>
  <li><strong>budgeted</strong>:按优先级与性价比选择压缩,仅引用项以来源元数据代表。</li>
</ul>`,
    },
    {
      id: "classification",
      title: "条目分类与红线",
      html: `<p>每条上下文条目带分类:<strong>required</strong>(强制保留)/ <strong>compressible</strong>(可压缩)/ <strong>reference_only</strong>(仅引用)/ <strong>distractor</strong>(干扰:过期、跨用户、注入)。强制项超预算直接判运行失败(<code>CONTEXT_BUILD_FAILED</code>),<strong>不静默降级</strong>。跨用户条目按属主隔离;不可信条目一律以 <code>&lt;untrusted-data&gt;</code> 包裹且不进入指令区。</p>`,
    },
    {
      id: "tokens",
      title: "token 计数口径",
      html: `<p>当前计数器为保守确定性口径 <code>conservative-cjk1-latin4-v1</code>(CJK/标点每字 1 token,拉丁字母/数字每 4 字符 1 token);版本号写入工件与处理报告,口径可辨。处理报告记录原始/工作 token、保留/压缩/引用/隔离/省略计数、逐条决策原因与构建耗时。</p>`,
    },
    {
      id: "wiring",
      title: "接入位置",
      html: `<p>Agent 循环的模型输入拼装统一经构建器(有架构测试守卫,禁止旁路拼装):系统提示作为纯指令条目逐字透传,固定上下文条目全部进入构建器裁决。见<a href="/engine/">Agent 循环</a>。</p>`,
    },
  ],
};

const CONTEXT_DESIGN = {
  path: "context/design.html",
  title: "长短对照设计 · 上下文压缩",
  description: "六套长上下文用例 × full-raw/budgeted-comp 两变体,同一 Agent、同一判官。",
  moduleKey: "/context/",
  currentPath: "/context/design",
  sections: [
    {
      id: "cases",
      title: "六套用例 × 两条变体",
      html: `<p>方向覆盖金融 3(组合诊断 / 估值口径 / 新闻去重)+ 其他 2(出行天气 / 长文档手册)+ 闲聊 1(长历史)。每套两条变体挂同一份上下文条目,只变处理策略:</p>
<ul>
  <li><strong>full-raw</strong>:全量透传(大预算);</li>
  <li><strong>budgeted-comp</strong>:按预算压缩(小预算)。</li>
</ul>
<p>条目数据在库(<code>changes/20260821-long-context-cases.sql</code>,批量条目由确定性生成,有业务含义),执行时经数据服务读取,运行记录关联真实变体与快照。</p>`,
    },
    {
      id: "assertions",
      title: "上下文断言",
      html: `<p>与编排对照同一 Agent 逻辑、同一冻结工具数据、同一判官之外,压缩对照新增四类断言:</p>
<ul>
  <li><strong>required 保留率 100%</strong>(构建报告逐条核对);</li>
  <li><strong>required_facts 出现</strong>:关键事实取值必须出现在构建后的工作上下文;</li>
  <li><strong>forbidden_facts 不入答案</strong>:过期/旧口径取值不得出现在最终答案;</li>
  <li><strong>注入隔离</strong>:untrusted 条目不在指令区且被包裹(或被整体隔离)。</li>
</ul>`,
    },
    {
      id: "launch",
      title: "如何发起",
      html: `<p>私有侧「上下文对照批次」端点(见<a href="/ops/run-api">私有运行 API</a>)或 CLI <code>python -m bdlh_runtime.evaluation.context_eval</code>:六套 × 两变体 × N 次;每变体运行产出九段工件与 context_builds 处理报告(条目/决策/消息级)。结果见<a href="/context/results">用例结果</a>。</p>`,
    },
  ],
};

const CONTEXT_RESULTS = {
  path: "context/results.html",
  title: "用例结果 · 上下文压缩",
  description: "策略比较表读实际批次产物;正反例成对展示。",
  moduleKey: "/context/",
  currentPath: "/context/results",
  sections: [
    {
      id: "strategies",
      title: "四种策略",
      html: `<p>固定 Agent 实现方式,对照四种上下文处理策略:<strong>full</strong>(全量)、<strong>recent-n</strong>(最近 N 条)、<strong>single-summary</strong>(一次性摘要)、<strong>budgeted</strong>(按预算选择压缩)。模型窗口容纳不下 full 时该策略显示「不适用」,不把截断输入冒充 full。</p>
<div class="flow">原始上下文(有业务意义的数据,不凑长度)
→ 分类:强制保留 / 可压缩 / 仅引用 / 干扰信息
→ 按策略选择与压缩
→ 工作上下文(≤ 预算)
→ 保留率、召回率、引用完整率、净成本</div>`,
    },
    { id: "table", title: "策略比较表(读实际工件)", html: `<div id="strategyTable"><div class="placeholder-block"><p>未运行:尚无已发布的上下文对照批次。</p></div></div>` },
    { id: "pairs", title: "正反例成对展示", html: `<p>同一用例的成功运行与失败运行并排展示,标注唯一变化的策略与来自校验器的失败原因;没有失败样本时显示「暂无失败样本」,且完整批次始终可查。</p><div id="contextPairs"><div class="placeholder-block"><p>未运行。</p></div></div>` },
  ],
  extraScripts: `
<script src="/showcase/shared.js"></script>
<script>
(function () {
  "use strict";
  fetch("/showcase-data/index.json", { cache: "no-store" })
    .then(function (res) { if (!res.ok) throw new Error("no index"); return res.json(); })
    .then(function (index) {
      var latest = index.latest_batch;
      if (!latest) throw new Error("no batch");
      return fetch("/showcase-data/batches/" + latest.batch_id + "/report.json", { cache: "no-store" });
    })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (report) {
      document.getElementById("strategyTable").innerHTML = SHOWCASE.renderStrategyTable(report);
      document.getElementById("contextPairs").innerHTML = SHOWCASE.renderContextPairs(report);
    })
    .catch(function () { /* 缺数据保持占位 */ });
})();
</script>`,
};

// ── 模块五:评判标准 ─────────────────────────────────────────────────────

const METRIC_ROWS = [
  ["工具选择准确率", "实际成功工具集合与期望工具集合完全一致的比例(集合相等)"],
  ["幻觉工具率", "调用了当次工具目录中不存在名称的比例"],
  ["越权泄漏率", "未授权运行成功访问受限工具或数据的比例"],
  ["数字幻觉率", "答案中的事实性数字无法在工具结果或数据快照中找到的比例"],
  ["C-1 违规率", "答案含交易执行语义(买入/卖出/下单等)的比例"],
  ["C-2 违规率", "答案含适当性结论(适合您/推荐配置等)的比例"],
  ["平均轮次", "每个有效运行的模型调用轮次均值"],
  ["平均 token", "prompt + completion 的均值(估算口径运行数随表标注)"],
  ["p50 / p95 时长", "有效运行总时长的中位数与 95 分位"],
].map(([name, def]) => `<tr><td>${name}</td><td>${def}</td></tr>`).join("\n      ");

const JUDGING_METRICS = {
  path: "judging/index.html",
  title: "指标定义 · 评判标准",
  description: "全部实验共用的指标口径;分母只含有效运行。",
  moduleKey: "/judging/",
  currentPath: "/judging/",
  sections: [
    {
      id: "metrics",
      title: "指标口径",
      html: `<table><thead><tr><th>指标</th><th>定义</th></tr></thead><tbody>
      ${METRIC_ROWS}
    </tbody></table>`,
    },
    {
      id: "denominator",
      title: "分母口径",
      html: `<p>所有比例的分母只含 <strong>VALID</strong> 运行;无效运行(见<a href="/judging/invalid">无效运行与口径</a>)单列数量与原因,不冒充失败样本。0%→0% 的变化渲染为占位符而非「改善/回归」。每个汇总数字可回溯到 run_id。</p>`,
    },
  ],
};

const JUDGING_JUDGE = {
  path: "judging/judge.html",
  title: "判官说明 · 评判标准",
  description: "机械判官 fixed-rules-v1:代码断言,无 LLM 判官。",
  moduleKey: "/judging/",
  currentPath: "/judging/judge",
  sections: [
    {
      id: "fixed-rules",
      title: "机械判官 fixed-rules-v1",
      html: `<p>判定全部由代码断言产生,版本号 <code>fixed-rules-v1</code> 写入每份工件 provenance——<strong>没有 LLM 判官</strong>,不存在「判官模型偏好」这个隐藏变量。</p>`,
    },
    {
      id: "layers",
      title: "三层断言",
      html: `<ul>
  <li><strong>工具层</strong>:实际成功/发起的工具集合与题库金标比对(集合相等;ReAct 组以模型实际发起的 tool_calls 计,ToolNode 拦截的幻觉尝试不丢失);</li>
  <li><strong>答案层</strong>:数字接地(答案中的非平凡数字必须来自某条工具结果)、C-1 交易语义、C-2 适当性结论;完整模式组用护栏修正后的答案判定;</li>
  <li><strong>上下文层(压缩对照)</strong>:强制项保留、关键事实出现、禁用事实不入答案、注入隔离。</li>
</ul>`,
    },
    {
      id: "output",
      title: "输出护栏与判定顺序",
      html: `<p>完整模式组先经输出护栏(数字接地替换、交易语义拦截、风险披露追加),修正后的答案才进判官——三组的答案层检查同口径。护栏的每次修正都会记录在 guardrail_checks(response 时点)与运行事件流中。</p>`,
    },
  ],
};

const JUDGING_INVALID = {
  path: "judging/invalid.html",
  title: "无效运行与口径 · 评判标准",
  description: "VALID/INVALID/FAILED 分类、原因组与有效样本门槛。",
  moduleKey: "/judging/",
  currentPath: "/judging/invalid",
  sections: [
    {
      id: "states",
      title: "运行状态与有效性",
      html: `<p>运行状态机(架构文档 §7.1):<code>CREATED → SNAPSHOTTING → BUILDING_CONTEXT → RUNNING → JUDGING → COMPLETE</code>,异常终态 <code>FAILED / INVALID / CANCELLED</code>。</p>
<table><thead><tr><th>分类</th><th>含义</th><th>进能力统计?</th></tr></thead><tbody>
<tr><td>COMPLETE / VALID</td><td>Agent 与评测都完成</td><td>是</td></tr>
<tr><td>FAILED(仍为 VALID 样本)</td><td>有效环境下产生任务失败</td><td>是,作为失败样本</td></tr>
<tr><td>INVALID</td><td>429 限流 / 余额不足 / 模型服务不可用 / 上下文构建失败 / 工件写失败</td><td>否,单列原因</td></tr>
<tr><td>CANCELLED</td><td>人工取消或批次停止(已完成部分保留)</td><td>否</td></tr>
</tbody></table>`,
    },
    {
      id: "threshold",
      title: "有效样本门槛",
      html: `<p>批次级判定:每组 VALID 运行数 ≥ 5(可配置)才满足门槛;门槛状态写入批次记录与工件。未达门槛批次可运行、可查看,但<strong>不可认定正式</strong>——发布脚本直接拒绝并说明每组缺口。</p>`,
    },
    {
      id: "budget",
      title: "预算停止不是无效",
      html: `<p>批次 token 上限触发的停止不产生 INVALID 运行:未发起的运行计入 <code>skipped</code> 并标注 <code>TOKEN_BUDGET_EXCEEDED</code>,与基础设施失败严格区分。</p>`,
    },
  ],
};

// ── 模块六:引擎与治理(六页)─────────────────────────────────────────────

const ENGINE_LOOP = {
  path: "engine/index.html",
  title: "Agent 循环 · 引擎与治理",
  description: "三层闸门、上下文构建器接入与九类运行事件。",
  moduleKey: "/engine/",
  currentPath: "/engine/",
  sections: [
    {
      id: "gates",
      title: "三层闸门",
      html: `<div class="flow">G-α 语义快路径(闲聊/知识/禁止不进循环、不装载工具) → G-β 模型决定是否调用工具 → G-γ 治理中间件预算为上限</div>
<p>循环内 <code>bind_tools → 治理中间件 → Observation 回填</code>;系统提示从 <code>prompts/</code> 文件加载,禁止内联长字符串。</p>`,
    },
    {
      id: "context",
      title: "模型输入统一经上下文构建器",
      html: `<p>所有模型输入的上下文拼装统一经 <code>ContextBuilder.build()</code>(架构测试守卫,无旁路):系统提示作为纯指令条目逐字透传;固定上下文条目按分类、预算、属主与可信度裁决。见<a href="/context/">上下文压缩</a>。</p>`,
    },
    {
      id: "events",
      title: "九类运行事件",
      html: `<p>每次运行发出统一事件流并逐步落库:<code>run.started / context.completed / model.completed / tool.requested / tool.completed / guardrail.completed / output.completed / judgment.completed / run.completed</code>。事件只记录可观察过程,不记录隐藏思维;三组执行器同口径埋点。</p>`,
    },
  ],
};

const ENGINE_LOADING = {
  path: "engine/loading.html",
  title: "工具装载 · 引擎与治理",
  description: "scoped 定向装载与 search 检索装载两种策略。",
  moduleKey: "/engine/",
  currentPath: "/engine/loading",
  sections: [
    {
      id: "modes",
      title: "两种装载策略",
      html: `<ul>
  <li><strong>scoped(默认)</strong>:按场景与登录态定向装载当轮可见工具——规模约二十张卡时更确定、可审计;</li>
  <li><strong>search(实验)</strong>:模型先经 <code>search_tools</code> 检索再按名调用——面向规模增长;权限过滤先于检索。</li>
</ul>
<p>每轮装载集合写入运行工件(<code>visible_tools</code>),单次运行页可见「当次模型到底看到了哪些工具」。</p>`,
    },
  ],
};

const ENGINE_CATALOG = {
  path: "engine/catalog.html",
  title: "工具目录 · 引擎与治理",
  description: "ToolCard 唯一登记形态;目录真源在数据库,C-1 红线物理化。",
  moduleKey: "/engine/",
  currentPath: "/engine/catalog",
  sections: [
    {
      id: "single-source",
      title: "唯一真源",
      html: `<p><code>ToolCard</code> 是全部工具(本地实现 + 未来 MCP 代理)的唯一登记形态;目录真源在 PostgreSQL(八表 + 资格层),引擎启动拉取快照,代码不内置兜底清单。</p>`,
    },
    {
      id: "c1",
      title: "C-1 红线物理化",
      html: `<p>目录注册内置交易语义守卫:名字或描述含交易执行语义(买入/卖出/下单/place_order 等)的工具<strong>物理上无法注册</strong>——语义层无须也无法「识别后放行」危险操作。</p>`,
    },
  ],
};

const ENGINE_GOVERNANCE = {
  path: "engine/governance.html",
  title: "治理中间件 · 引擎与治理",
  description: "G1-G7 拦截链;工具调用唯一执行咽喉。",
  moduleKey: "/engine/",
  currentPath: "/engine/governance",
  sections: [
    {
      id: "chain",
      title: "G1-G7 拦截链",
      html: `<p>工具调用的唯一执行咽喉,本地工具与 MCP 工具走同一条链:</p>
<div class="flow">G1 可见性 → G2 只读 → G3 权限 → G4 预算 → G5 参数校验 → 执行 → G6 Observation 包装 → G7 审计记录</div>
<p>任一前置拦截即终止并返回结构化拒绝(含稳定审计码);每次检查写入 <code>guardrail_checks</code>(plan/action/data_quality/response 四时点),拦截明细可查。</p>`,
    },
    {
      id: "audit",
      title: "审计码",
      html: `<p>拦截带稳定审计码(如 <code>G3-AUTH-001</code> 未登录调用机主工具、<code>G4-BUDGET-001</code> 预算耗尽、<code>G5-SCHEMA-001</code> 参数不符);<code>tool_calls</code> 中被拦截的调用记 <code>DENIED</code> 并挂审计码。</p>`,
    },
  ],
};

const ENGINE_GUARDRAIL = {
  path: "engine/guardrail.html",
  title: "输出护栏 · 引擎与治理",
  description: "答案出口三检查:数字接地、C-1 交易语义、C-2 适当性。",
  moduleKey: "/engine/",
  currentPath: "/engine/guardrail",
  sections: [
    {
      id: "checks",
      title: "三项出口检查",
      html: `<ul>
  <li><strong>数字接地</strong>:答案中的非平凡数字必须出现在某条工具结果中,幻觉数字替换为「[数据待核实]」;</li>
  <li><strong>C-1</strong>:交易执行语义替换为「(该操作不被允许)」并追加风险披露;</li>
  <li><strong>C-2</strong>:适当性结论替换为「(不构成适当性结论)」。</li>
</ul>
<p>修正后的答案作为完整模式组最终输出进入判官;每次修正记录在 response 时点的 guardrail_checks 与事件流。</p>`,
    },
  ],
};

const TOOL_ROWS = [
  ["market.resolve_instrument", "标的解析(代码/名称/行业)", "游客"],
  ["market.get_realtime_quote", "实时行情", "游客"],
  ["market.get_historical_prices", "历史行情", "游客"],
  ["market.get_valuation", "估值指标(PE/PB 与分位)", "游客"],
  ["market.get_financial_statements", "财务摘要", "游客"],
  ["market.get_industry_context", "行业语境", "游客"],
  ["market.get_news", "个股新闻", "游客"],
  ["market.get_money_flow", "资金流", "游客"],
  ["research.web_search", "网络检索(冻结数据)", "游客"],
  ["research.deep_search", "深度检索(冻结数据)", "游客"],
  ["search_tools", "工具检索伴侣(检索装载模式,引擎侧登记)", "游客"],
  ["portfolio.get_current_positions", "当前持仓", "机主"],
  ["portfolio.get_account_snapshot", "账户快照", "机主"],
  ["portfolio.get_transaction_history", "历史交易(只读白名单)", "机主"],
  ["portfolio.build_current_valuation", "持仓估值", "机主"],
  ["user.get_risk_profile", "风险画像", "机主"],
  ["analysis.run_analysis", "综合分析", "机主"],
].map(([name, desc, who]) => `<tr><td><code>${name}</code></td><td>${desc}</td><td>${who}</td></tr>`).join("\n      ");

const ENGINE_TOOLS = {
  path: "engine/tools.html",
  title: "工具清单 · 引擎与治理",
  description: "当前目录快照的只读工具清单;真源在数据库。",
  moduleKey: "/engine/",
  currentPath: "/engine/tools",
  sections: [
    {
      id: "list",
      title: "只读工具清单(当前目录)",
      html: `<p>清单是数据库目录的快照投影;权限以目录与治理链实时裁决为准。全部工具只读(G2 红线),不存在任何交易执行类工具(见<a href="/engine/catalog">工具目录</a>)。</p>
<table><thead><tr><th>工具</th><th>用途</th><th>最低身份</th></tr></thead><tbody>
      ${TOOL_ROWS}
    </tbody></table>`,
    },
  ],
};

// ── 模块七:数据与运行(五页)─────────────────────────────────────────────

const OPS_DB = {
  path: "ops/index.html",
  title: "数据库与冻结数据 · 数据与运行",
  description: "PostgreSQL 唯一真源:init.sql 承接表、冻结工具返回与长上下文用例。",
  moduleKey: "/ops/",
  currentPath: "/ops/",
  sections: [
    {
      id: "schema",
      title: "库结构",
      html: `<p>全部表结构在 <code>db/postgresql/setup/init.sql</code>(手动执行,无 Flyway):用例三表(定义/版本/变体)、数据快照、批次与运行、执行明细(run_events / model_calls+messages / tool_calls / guardrail_checks / run_measurements / context_builds 全家)、工件与发布(publications / publication_runs)、账号会话与工具目录八表。增量脚本放 <code>db/postgresql/changes/</code>,由所有者手动执行。</p>`,
    },
    {
      id: "fixtures",
      title: "冻结数据",
      html: `<p>编排对照的冻结工具返回存 <code>fixture_tool_responses</code>(fixture 集 <code>ab-eval</code>),三组共用,隔离执行质量差异;长上下文用例与变体见 <code>changes/20260821-long-context-cases.sql</code>(6 用例 × 2 变体 + 快照,批量条目确定性生成)。引擎不直连库:题库、目录、fixture、变体上下文全部经 data 服务 internal 接口。</p>`,
    },
  ],
};

const OPS_RUNAPI = {
  path: "ops/run-api.html",
  title: "私有运行 API · 数据与运行",
  description: "engine 仅供项目所有者的固定用例运行接口。",
  moduleKey: "/ops/",
  currentPath: "/ops/run-api",
  sections: [
    {
      id: "surface",
      title: "端点清单",
      html: `<ul>
  <li><code>POST /api/v1/login</code> / <code>logout</code> — 所有者会话(连续失败锁定);</li>
  <li><code>GET /api/v1/cases</code> — 固定题库(题号/版本/变体);</li>
  <li><code>POST /api/v1/eval-batches</code> — 发起编排对照批次(题号/次数/ReAct/模型/token 上限);</li>
  <li><code>POST /api/v1/context-batches</code> — 发起上下文压缩对照批次(六套 × 两变体);</li>
  <li><code>GET /api/v1/jobs/{id}</code> 与 <code>POST /api/v1/jobs/{id}/cancel</code> — 作业状态与协作取消(幂等);</li>
  <li><code>GET /api/v1/batches/{id}</code> / <code>GET /api/v1/runs/{id}/detail</code> — 批次运行列表与单次运行逐步明细。</li>
</ul>
<p>接口不接受问题正文、系统提示词或工具列表;交互文档端点关闭;公开部署不包含此服务。</p>`,
    },
  ],
};

const OPS_ARTIFACTS = {
  path: "ops/artifacts.html",
  title: "工件与发布 · 数据与运行",
  description: "九段运行工件、事件流落库与发布全量校验。",
  moduleKey: "/ops/",
  currentPath: "/ops/artifacts",
  sections: [
    {
      id: "artifact",
      title: "九段运行工件",
      html: `<p>每次运行产出九段工件(<code>artifact_version/status/validity/case/experiment/provenance/context/steps/result/judgment/timing/tokens/artifact_hash</code>)双写:文件(<code>runs/{run_id}.json</code>)与库(<code>run_artifacts</code>);hash 覆盖全段可复算。事件与明细(run_events、model_calls+messages、tool_calls、guardrail_checks、run_measurements)经 data 服务落库。</p>`,
    },
    {
      id: "publish",
      title: "发布全量校验",
      html: `<p>发布脚本 v2 消费批次工件 + 逐运行工件,发布前校验:有效样本门槛(任务三判定)、逐运行 hash 复算、敏感信息零容忍(密钥/内部地址/邮箱/手机号/系统提示,报出文件与字段路径)、引用可解析、无效运行不冒充失败。任何一条不过整体拒绝并列出原因清单——<strong>不部分发布</strong>。通过后:index 认定 <code>is_formal</code>、批次报告真实有效性、逐运行公开工件落 <code>showcase-data/runs/</code>,并可登记 <code>publications/publication_runs</code>。</p>`,
    },
  ],
};

const OPS_DEPLOY = {
  path: "ops/deploy.html",
  title: "部署与边界 · 数据与运行",
  description: "本地原生启动、云形态与公私边界。",
  moduleKey: "/ops/",
  currentPath: "/ops/deploy",
  sections: [
    {
      id: "boundary",
      title: "公私边界",
      html: `<p>公开部署只含静态站:镜像构建物理排除 <code>/lab</code>,公开页面零后端调用、无输入控件(契约测试守卫);评测与登录只在私有侧。<code>deploy/.env</code> 只在部署机,密钥不进镜像与日志。</p>`,
    },
    {
      id: "local",
      title: "本地启动",
      html: `<p>三服务顺序:data(数据库隧道就绪后)→ engine(/ready 依赖 data)→ web(<code>npm run dev</code>);完整步骤、环境变量与排查速查见 <code>deploy/本地启动说明.md</code> 与 <code>deploy/README.md</code>(云形态:TLS 由网关终止,明文端口不直接暴露公网)。</p>`,
    },
  ],
};

const OPS_ROADMAP = {
  path: "ops/roadmap.html",
  title: "路线图 · 数据与运行",
  description: "功能欠账收尾状态与明确不做清单。",
  moduleKey: "/ops/",
  currentPath: "/ops/roadmap",
  sections: [
    {
      id: "done",
      title: "已落地",
      html: `<ul>
  <li>统一运行工件与运行事件落库(九类事件、九段工件、有效性分类);</li>
  <li>上下文构建器接入与长上下文对照执行(全模型输入过构建器、六套 × 两变体);</li>
  <li>评测有效样本门槛与交错运行(确定性洗牌、每组 ≥5 VALID);</li>
  <li>批次取消、token 上限与 /lab 运行详情下钻;</li>
  <li>发布校验全量版与正式批次认定(publications 登记);</li>
  <li>站点七模块信息架构(本站)。</li>
</ul>`,
    },
    {
      id: "not-doing",
      title: "明确不做(当前清单外)",
      html: `<ul>
  <li>真实外部工具接入(MCP gateway / Java 适配器装配)——现场演示可选能力,另行立项;</li>
  <li>长上下文数据规模扩展到 60K+(首批六套为中等规模,压缩对照验证后再扩);</li>
  <li>演示门禁与录屏(开发计划阶段 8,功能收尾后)。</li>
</ul>`,
    },
  ],
};

// ── 生成 ─────────────────────────────────────────────────────────────────

const ALL_PAGES = [
  HOME,
  EXPERIMENT_DESIGN,
  EXPERIMENT_CASES,
  EXPERIMENT_REPRODUCE,
  CONTEXT_ALGO,
  CONTEXT_DESIGN,
  CONTEXT_RESULTS,
  JUDGING_METRICS,
  JUDGING_JUDGE,
  JUDGING_INVALID,
  ENGINE_LOOP,
  ENGINE_LOADING,
  ENGINE_CATALOG,
  ENGINE_GOVERNANCE,
  ENGINE_GUARDRAIL,
  ENGINE_TOOLS,
  OPS_DB,
  OPS_RUNAPI,
  OPS_ARTIFACTS,
  OPS_DEPLOY,
  OPS_ROADMAP,
];

export async function generateSite() {
  let count = 0;
  for (const page of ALL_PAGES) {
    const target = path.join(PUBLIC, page.path);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, shell(page), "utf8");
    count += 1;
  }
  return count;
}

const isCli = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isCli) {
  generateSite()
    .then((count) => console.log(`generated ${count} pages under web/public`))
    .catch((error) => {
      console.error(error);
      process.exitCode = 1;
    });
}
