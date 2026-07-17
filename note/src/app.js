import {
  baselineGroups,
  checklistSections,
  currentMdp,
  initialDecisions,
  initialExperiments,
  referenceRepos,
} from "./data.js";
import {
  AlertTriangle,
  Bot,
  Boxes,
  BrainCircuit,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  ClipboardCheck,
  Clock3,
  createIcons,
  Database,
  Download,
  ExternalLink,
  FileCode2,
  FlaskConical,
  Gauge,
  GitCompareArrows,
  LayoutDashboard,
  Library,
  Menu,
  PencilLine,
  Plus,
  RotateCcw,
  Ruler,
  Save,
  Search,
  SlidersHorizontal,
  Trash2,
  Upload,
  X,
} from "lucide";
import "./styles.css";

const STORAGE_KEY = "swingboy-rl-notes-v1";
const iconSet = {
  AlertTriangle,
  Bot,
  Boxes,
  BrainCircuit,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  ClipboardCheck,
  Clock3,
  Database,
  Download,
  ExternalLink,
  FileCode2,
  FlaskConical,
  Gauge,
  GitCompareArrows,
  LayoutDashboard,
  Library,
  Menu,
  PencilLine,
  Plus,
  RotateCcw,
  Ruler,
  Save,
  Search,
  SlidersHorizontal,
  Trash2,
  Upload,
  X,
};

const navItems = [
  ["overview", "LayoutDashboard", "准备总览"],
  ["checklist", "ClipboardCheck", "前期检查"],
  ["baseline", "Bot", "机器人基线"],
  ["mdp", "BrainCircuit", "MDP 设计"],
  ["references", "Library", "参考仓库"],
  ["experiments", "FlaskConical", "实验记录"],
];

const app = document.querySelector("#app");
let activePage = window.location.hash.replace("#", "") || "overview";
let checklistFilter = "all";
let mdpTab = "observations";
let referenceView = "detail";
let selectedReference = referenceRepos[0].id;
let referenceQuery = "";
let selectedExperiment = null;
let toastTimer;

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function icon(name, className = "") {
  const iconName = name.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
  return `<i data-lucide="${iconName}" class="${className}" aria-hidden="true"></i>`;
}

function defaultState() {
  const checklist = {};
  checklistSections.forEach((section) => {
    section.items.forEach((item) => {
      checklist[item.id] = { done: item.done, note: "" };
    });
  });
  const baseline = {};
  baselineGroups.forEach((group) => {
    group.fields.forEach((field) => {
      baseline[field.id] = field.value;
    });
  });
  return {
    schema: 1,
    checklist,
    baseline,
    mdpNotes: "",
    experiments: structuredClone(initialExperiments),
    decisions: structuredClone(initialDecisions),
  };
}

function loadState() {
  const defaults = defaultState();
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (!stored || stored.schema !== 1) return defaults;
    return {
      ...defaults,
      ...stored,
      checklist: { ...defaults.checklist, ...stored.checklist },
      baseline: { ...defaults.baseline, ...stored.baseline },
      experiments: Array.isArray(stored.experiments) ? stored.experiments : defaults.experiments,
      decisions: Array.isArray(stored.decisions) ? stored.decisions : defaults.decisions,
    };
  } catch {
    return defaults;
  }
}

let state = loadState();

function saveState(message = "") {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  if (message) showToast(message);
}

function showToast(message, tone = "normal") {
  const toast = document.querySelector("#toast");
  if (!toast) return;
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.dataset.tone = tone;
  toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2400);
}

function activateIcons() {
  createIcons({ icons: iconSet, attrs: { "stroke-width": 1.8 } });
}

function checklistStats(section = null) {
  const items = section ? section.items : checklistSections.flatMap((entry) => entry.items);
  const done = items.filter((item) => state.checklist[item.id]?.done).length;
  return { done, total: items.length, percent: Math.round((done / items.length) * 100) };
}

function statusTone(percent) {
  if (percent >= 80) return "good";
  if (percent >= 50) return "warning";
  return "danger";
}

function renderShell() {
  app.innerHTML = `
    <div class="app-shell">
      <div class="mobile-topbar">
        <button class="icon-button" id="mobile-menu" title="打开导航" aria-label="打开导航">${icon("Menu")}</button>
        <strong>Swingboy RL Notes</strong>
        <span class="mobile-page-name"></span>
      </div>
      <div class="sidebar-backdrop" id="sidebar-backdrop"></div>
      <aside class="sidebar" id="sidebar">
        <div class="brand-block">
          <div class="brand-mark">SB</div>
          <div><strong>Swingboy RL</strong><span>Research Notebook</span></div>
          <button class="icon-button sidebar-close" id="sidebar-close" title="关闭导航" aria-label="关闭导航">${icon("X")}</button>
        </div>
        <nav class="primary-nav" aria-label="主要页面">
          ${navItems.map(([id, iconName, label]) => `
            <button class="nav-button" data-page="${id}">${icon(iconName)}<span>${label}</span></button>
          `).join("")}
        </nav>
        <div class="workflow-rail">
          <div class="rail-heading">训练准入</div>
          ${checklistSections.map((section, index) => {
            const stats = checklistStats(section);
            return `
              <button class="rail-step" data-page="checklist" data-section="${section.id}">
                <span class="rail-index ${stats.percent === 100 ? "is-done" : ""}">${stats.percent === 100 ? icon("CheckCircle2") : index + 1}</span>
                <span><strong>${section.title}</strong><small>${stats.done} / ${stats.total}</small></span>
              </button>`;
          }).join("")}
        </div>
        <div class="sidebar-spacer"></div>
        <div class="repo-state">
          <span>LOCAL NOTE</span>
          <strong>schema / v1</strong>
          <small>2026-07-17</small>
        </div>
      </aside>
      <main class="workspace">
        <div id="page-content" class="page-content"></div>
      </main>
      <div class="toast" id="toast" role="status" aria-live="polite"></div>
      <input type="file" id="import-file" accept="application/json" hidden />
    </div>`;

  document.querySelector("#mobile-menu").addEventListener("click", openSidebar);
  document.querySelector("#sidebar-close").addEventListener("click", closeSidebar);
  document.querySelector("#sidebar-backdrop").addEventListener("click", closeSidebar);
  document.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      activePage = button.dataset.page;
      window.location.hash = activePage;
      renderPage();
      closeSidebar();
      if (button.dataset.section) {
        requestAnimationFrame(() => document.querySelector(`#section-${button.dataset.section}`)?.scrollIntoView());
      }
    });
  });
  document.querySelector("#import-file").addEventListener("change", importData);
  renderPage();
}

function openSidebar() {
  document.querySelector("#sidebar").classList.add("is-open");
  document.querySelector("#sidebar-backdrop").classList.add("is-visible");
}

function closeSidebar() {
  document.querySelector("#sidebar").classList.remove("is-open");
  document.querySelector("#sidebar-backdrop").classList.remove("is-visible");
}

function pageHeader(eyebrow, title, subtitle, actions = "") {
  return `
    <header class="page-header">
      <div>
        <div class="eyebrow">${eyebrow}</div>
        <h1>${title}</h1>
        <p>${subtitle}</p>
      </div>
      <div class="header-actions">${actions}</div>
    </header>`;
}

function globalActions() {
  return `
    <button class="button secondary" id="import-button">${icon("Upload")}<span>导入</span></button>
    <button class="button primary" id="export-button">${icon("Download")}<span>导出记录</span></button>`;
}

function bindGlobalActions() {
  document.querySelector("#export-button")?.addEventListener("click", exportData);
  document.querySelector("#import-button")?.addEventListener("click", () => document.querySelector("#import-file").click());
}

function renderPage() {
  if (!navItems.some(([id]) => id === activePage)) activePage = "overview";
  const renderers = {
    overview: renderOverview,
    checklist: renderChecklist,
    baseline: renderBaseline,
    mdp: renderMdp,
    references: renderReferences,
    experiments: renderExperiments,
  };
  document.querySelector("#page-content").innerHTML = renderers[activePage]();
  document.querySelectorAll(".nav-button").forEach((button) => button.classList.toggle("is-active", button.dataset.page === activePage));
  document.querySelector(".mobile-page-name").textContent = navItems.find(([id]) => id === activePage)?.[2] || "";
  bindPageEvents();
  activateIcons();
}

function renderOverview() {
  const total = checklistStats();
  const pending = total.total - total.done;
  const unresolved = state.decisions.filter((decision) => decision.state === "未解决").length;
  const latest = state.experiments.slice().sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3);
  return `
    ${pageHeader("SWINGBOY / READINESS", "训练准备总览", "机器人建模、MDP 设计和实验证据", globalActions())}
    <div class="page-divider"></div>
    <div class="scroll-area overview-page">
      <section class="project-strip">
        <div class="project-image-wrap"><img src="/assets/swingboy-sim.png" alt="Swingboy 机器人 MuJoCo 仿真外观" /></div>
        <div class="project-summary">
          <div class="summary-kicker">CURRENT BASELINE</div>
          <h2>DDT Tita 结构 / Swingboy 平地任务</h2>
          <p class="mono">DDT-Velocity-Flat-Swingboy-v0</p>
          <div class="summary-specs">
            <span><small>仿真器</small>Isaac Sim 5.1</span>
            <span><small>算法</small>NP3O / PPO</span>
            <span><small>控制</small>50 Hz</span>
            <span><small>总质量</small>6.419 kg</span>
          </div>
        </div>
        <div class="readiness-dial" style="--progress:${total.percent * 3.6}deg">
          <div><strong>${total.percent}%</strong><span>准备度</span></div>
        </div>
      </section>

      <section class="metric-row">
        <article class="metric"><span>已核对</span><strong>${total.done}</strong><small>/ ${total.total} 项</small></article>
        <article class="metric"><span>待核对</span><strong class="warning-text">${pending}</strong><small>前期项</small></article>
        <article class="metric"><span>未解决风险</span><strong class="danger-text">${unresolved}</strong><small>决策项</small></article>
        <article class="metric"><span>参考基线</span><strong>${referenceRepos.length}</strong><small>个仓库</small></article>
      </section>

      <section class="content-section">
        <div class="section-title"><div><span>READINESS BY DOMAIN</span><h2>分项准备度</h2></div><button class="text-button" data-go="checklist">查看全部 ${icon("ChevronRight")}</button></div>
        <div class="readiness-table">
          ${checklistSections.map((section) => {
            const stats = checklistStats(section);
            return `<button class="readiness-row" data-go="checklist" data-scroll="${section.id}">
              <span class="domain-icon">${icon(section.icon)}</span>
              <span class="domain-name"><strong>${section.title}</strong><small>${stats.done} / ${stats.total} 已核对</small></span>
              <span class="progress-track"><i style="width:${stats.percent}%" data-tone="${statusTone(stats.percent)}"></i></span>
              <strong class="mono">${stats.percent}%</strong>
              ${icon("ChevronRight", "row-chevron")}
            </button>`;
          }).join("")}
        </div>
      </section>

      <div class="overview-columns">
        <section class="content-section risk-section">
          <div class="section-title"><div><span>OPEN RISKS</span><h2>未闭环问题</h2></div></div>
          <div class="decision-list compact">
            ${state.decisions.filter((decision) => decision.state === "未解决").map(decisionRow).join("") || '<div class="empty-state">暂无未解决项</div>'}
          </div>
        </section>
        <section class="content-section">
          <div class="section-title"><div><span>RECENT EXPERIMENTS</span><h2>最近实验</h2></div><button class="text-button" data-go="experiments">全部记录 ${icon("ChevronRight")}</button></div>
          <div class="recent-experiments">
            ${latest.map((experiment) => `<button data-experiment="${experiment.id}" class="recent-row">
              <span class="status-dot" data-status="${experiment.status}"></span>
              <span><strong>${escapeHtml(experiment.name)}</strong><small>${escapeHtml(experiment.task)}</small></span>
              <time class="mono">${experiment.date}</time>
            </button>`).join("") || '<div class="empty-state">暂无实验记录</div>'}
          </div>
        </section>
      </div>
    </div>`;
}

function decisionRow(decision) {
  const tone = decision.type === "风险" ? "danger" : "info";
  return `<article class="decision-row">
    <span class="decision-icon" data-tone="${tone}">${icon(decision.type === "风险" ? "AlertTriangle" : "PencilLine")}</span>
    <div><div><strong>${escapeHtml(decision.title)}</strong><span class="status-label" data-state="${decision.state}">${decision.state}</span></div><p>${escapeHtml(decision.detail)}</p><small class="mono">${decision.date}</small></div>
  </article>`;
}

function renderChecklist() {
  const total = checklistStats();
  return `
    ${pageHeader("PRE-FLIGHT / CHECKLIST", "前期检查", `${total.done} / ${total.total} 项已核对，完成度 ${total.percent}%`, `
      <div class="segmented-control" role="group" aria-label="检查项筛选">
        <button data-check-filter="all">全部</button><button data-check-filter="pending">待核对</button><button data-check-filter="done">已完成</button>
      </div>`)}
    <div class="page-divider"></div>
    <div class="checklist-summary-bar">
      <span class="progress-track large"><i style="width:${total.percent}%" data-tone="${statusTone(total.percent)}"></i></span>
      <strong class="mono">${total.percent}%</strong>
      <span>${total.total - total.done} 项尚未闭环</span>
    </div>
    <div class="scroll-area checklist-page">
      ${checklistSections.map((section) => {
        const stats = checklistStats(section);
        const visibleItems = section.items.filter((item) => checklistFilter === "all" || (checklistFilter === "done" ? state.checklist[item.id]?.done : !state.checklist[item.id]?.done));
        if (!visibleItems.length) return "";
        return `<section class="check-section" id="section-${section.id}">
          <header><span class="domain-icon">${icon(section.icon)}</span><div><h2>${section.title}</h2><p>${stats.done} / ${stats.total} 已核对</p></div><span class="progress-track"><i style="width:${stats.percent}%" data-tone="${statusTone(stats.percent)}"></i></span><strong class="mono">${stats.percent}%</strong></header>
          <div class="check-items">
            ${visibleItems.map((item) => {
              const itemState = state.checklist[item.id] || { done: false, note: "" };
              return `<article class="check-item ${itemState.done ? "is-done" : ""}">
                <label class="check-control"><input type="checkbox" data-check-id="${item.id}" ${itemState.done ? "checked" : ""} /><span>${icon("CheckCircle2")}</span></label>
                <div class="check-copy"><strong>${item.title}</strong><p>${item.detail}</p></div>
                <label class="check-note"><span>记录</span><input data-check-note="${item.id}" value="${escapeHtml(itemState.note)}" placeholder="实测值 / 文件 / 结论" /></label>
              </article>`;
            }).join("")}
          </div>
        </section>`;
      }).join("") || '<div class="empty-state page-empty">当前筛选下没有检查项</div>'}
    </div>`;
}

function renderBaseline() {
  return `
    ${pageHeader("ROBOT / BASELINE", "机器人基线", "实测值、URDF 值与训练假设", `<button class="button primary" id="save-baseline">${icon("Save")}<span>保存基线</span></button>`)}
    <div class="page-divider"></div>
    <div class="scroll-area baseline-page">
      <section class="mismatch-banner">
        <span>${icon("AlertTriangle")}</span>
        <div><strong>Reset 契约尚未闭环</strong><p>实机校准 knee = 5°，当前训练默认 knee = 35.3°，reset 只在训练默认值的 95%–100% 范围。</p></div>
        <span class="severity">HIGH</span>
      </section>
      <section class="robot-visual-band">
        <div class="robot-image"><img src="/assets/swingboy-sim.png" alt="Swingboy MuJoCo 仿真模型" /></div>
        <div class="robot-facts">
          <div><span>机器人</span><strong>Swingboy</strong></div>
          <div><span>构型</span><strong>双轮腿 / 6 DoF</strong></div>
          <div><span>URDF 质量</span><strong class="mono">6.419 kg</strong></div>
          <div><span>目标高度</span><strong class="mono">0.300 m</strong></div>
        </div>
      </section>
      ${baselineGroups.map((group) => `<section class="baseline-section">
        <div class="section-title"><div><span>${group.id.toUpperCase()}</span><h2>${group.title}</h2></div></div>
        <div class="baseline-grid">
          ${group.fields.map((field) => `<label class="baseline-field">
            <span>${field.label}</span>
            <div><input data-baseline="${field.id}" value="${escapeHtml(state.baseline[field.id] ?? field.value)}" /><em>${field.unit}</em></div>
            <small>${field.source}</small>
          </label>`).join("")}
        </div>
      </section>`).join("")}
      <section class="source-map">
        <div class="section-title"><div><span>SOURCE OF TRUTH</span><h2>配置来源</h2></div></div>
        <div class="source-rows">
          <div><span>URDF</span><code>sim/isaaclab/robot/robot.urdf</code><strong>质量 / 惯量 / 限位</strong></div>
          <div><span>Asset cfg</span><code>sim/isaaclab/.../assets/ddt_robot.py</code><strong>默认姿态 / 电机 / PD</strong></div>
          <div><span>Task cfg</span><code>sim/isaaclab/.../swingboy/flat_env_cfg.py</code><strong>MDP / reset / randomization</strong></div>
          <div><span>ROS 2</span><code>ros2_ws/src/swingboy_description</code><strong>部署模型</strong></div>
        </div>
      </section>
    </div>`;
}

function tabButton(id, label) {
  return `<button data-mdp-tab="${id}" class="${mdpTab === id ? "is-active" : ""}">${label}</button>`;
}

function renderKeyValueRows(rows) {
  return rows.map(([name, value, note = ""]) => `<div class="kv-row"><code>${escapeHtml(name)}</code><strong class="mono">${escapeHtml(value)}</strong><span>${escapeHtml(note)}</span></div>`).join("");
}

function renderMdp() {
  const summary = currentMdp.summary;
  let body = "";
  if (mdpTab === "observations") {
    body = `<div class="mdp-columns"><section><div class="subsection-heading"><span>ACTOR</span><h2>策略观测</h2></div><div class="kv-table">${renderKeyValueRows(currentMdp.actorObservations)}</div></section><section><div class="subsection-heading"><span>ASYMMETRIC</span><h2>Critic 额外信息</h2></div><ul class="plain-list">${currentMdp.criticAdditions.map((item) => `<li>${icon("ChevronRight")}<span>${item}</span></li>`).join("")}</ul><div class="contract-note"><strong>部署契约</strong><p>Actor 不使用 base linear velocity 和 height scan。当前每帧 22 维本体感观测，使用 10 帧历史。</p></div></section></div>`;
  } else if (mdpTab === "actions") {
    body = `<div class="mdp-columns"><section><div class="subsection-heading"><span>ACTION SPACE</span><h2>动作映射</h2></div><div class="kv-table">${renderKeyValueRows(currentMdp.actions)}</div></section><section><div class="subsection-heading"><span>COMMAND</span><h2>指令范围</h2></div><div class="kv-table">${renderKeyValueRows(currentMdp.commands)}</div></section></div>`;
  } else if (mdpTab === "rewards") {
    body = `<section><div class="subsection-heading"><span>REWARD TERMS</span><h2>奖励与惩罚</h2></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>Term</th><th>Weight</th><th>参数 / 目标</th></tr></thead><tbody>${currentMdp.rewards.map(([name, weight, note]) => `<tr><td><code>${name}</code></td><td class="mono ${weight.startsWith("+") ? "positive" : "negative"}">${weight}</td><td>${note}</td></tr>`).join("")}</tbody></table></div></section>`;
  } else {
    body = `<div class="mdp-columns"><section><div class="subsection-heading"><span>TERMINATION</span><h2>终止条件</h2></div><div class="kv-table">${renderKeyValueRows(currentMdp.terminations)}</div><div class="contract-note danger"><strong>探索风险</strong><p>hip_knee_link 接触立即终止可能会让从低姿态起立的轨迹无法获得长时域回报。</p></div></section><section><div class="subsection-heading"><span>RESET</span><h2>初始状态</h2></div><div class="kv-table">${renderKeyValueRows(currentMdp.reset)}</div></section></div>`;
  }
  return `
    ${pageHeader("POLICY / CONTRACT", "MDP 设计", summary.task, `<span class="status-pill warning">${summary.status}</span>`)}
    <div class="mdp-summary">
      ${Object.entries(summary).filter(([key]) => !["task", "status"].includes(key)).map(([key, value]) => `<div><span>${({ simulator: "仿真器", algorithm: "算法", environments: "环境", controlRate: "控制频率", episode: "Episode" })[key] || key}</span><strong>${value}</strong></div>`).join("")}
    </div>
    <div class="tab-bar">${tabButton("observations", "Observation")}${tabButton("actions", "Action / Command")}${tabButton("rewards", "Reward")}${tabButton("termination", "Terminal / Reset")}</div>
    <div class="scroll-area mdp-page">
      <div class="mdp-content">${body}</div>
      <section class="mdp-notes"><label><span>${icon("PencilLine")} MDP 审核记录</span><textarea id="mdp-notes" placeholder="记录假设、疑问、单元测试结果和下一次修改...">${escapeHtml(state.mdpNotes)}</textarea></label></section>
    </div>`;
}

function filteredReferences() {
  const query = referenceQuery.trim().toLowerCase();
  if (!query) return referenceRepos;
  return referenceRepos.filter((repo) => [repo.name, repo.robot, repo.simulator, repo.algorithm, repo.terrain].join(" ").toLowerCase().includes(query));
}

function renderReferences() {
  const repos = filteredReferences();
  const selected = referenceRepos.find((repo) => repo.id === selectedReference) || repos[0] || referenceRepos[0];
  const actions = `<div class="search-box">${icon("Search")}<input id="reference-search" value="${escapeHtml(referenceQuery)}" placeholder="搜索机器人、算法或仿真器" /></div>`;
  let content;
  if (referenceView === "matrix") {
    const rows = [
      ["仿真器", "simulator"], ["算法", "algorithm"], ["地形", "terrain"], ["Action", "actions"], ["Observation", "observations"], ["Command", "commands"], ["Reward", "rewards"], ["Terminal", "terminal"], ["Initial state", "initialState"], ["Randomization", "randomization"]
    ];
    content = `<div class="comparison-wrap"><table class="comparison-table"><thead><tr><th>对比项</th>${repos.map((repo) => `<th><a href="${repo.url}" target="_blank" rel="noreferrer">${repo.name} ${icon("ExternalLink")}</a><small>${repo.revision}</small></th>`).join("")}</tr></thead><tbody>${rows.map(([label, key]) => `<tr><th>${label}</th>${repos.map((repo) => `<td>${escapeHtml(repo[key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  } else {
    content = `<div class="reference-layout">
      <aside class="reference-list">${repos.map((repo) => `<button data-reference="${repo.id}" class="${repo.id === selected.id ? "is-active" : ""}"><span><strong>${repo.name}</strong><small>${repo.robot}</small></span><span class="relevance" data-level="${repo.relevance}">${repo.relevance}</span></button>`).join("") || '<div class="empty-state">无匹配仓库</div>'}</aside>
      <article class="reference-detail">
        <header><div><span class="eyebrow">REFERENCE / ${selected.revision}</span><h2>${selected.name}</h2><p>${selected.robot}</p></div><a class="button secondary" href="${selected.url}" target="_blank" rel="noreferrer">${icon("ExternalLink")}<span>仓库</span></a></header>
        <div class="reference-meta"><span>${selected.simulator}</span><span>${selected.algorithm}</span><span>${selected.status}</span></div>
        <div class="reference-sections">
          ${referenceField("SlidersHorizontal", "Action", selected.actions)}
          ${referenceField("Database", "Observation / Critic", `${selected.observations}\n\nCritic: ${selected.critic}`)}
          ${referenceField("Gauge", "Command", selected.commands)}
          ${referenceField("ChartNoAxesCombined", "Reward", selected.rewards)}
          ${referenceField("CircleDashed", "Terminal / Reset", `${selected.terminal}\n\nInitial: ${selected.initialState}`)}
          ${referenceField("Boxes", "Terrain / Randomization", `${selected.terrain}\n\n${selected.randomization}`)}
        </div>
        <section class="takeaways"><h3>可迁移结论</h3><ul>${selected.lessons.map((lesson) => `<li>${icon("CheckCircle2")}<span>${lesson}</span></li>`).join("")}</ul></section>
        <section class="implementation-result"><h3>实现与效果</h3><p>${selected.result}</p></section>
        <footer class="source-files"><span>${icon("FileCode2")} 核对来源</span>${selected.sourceFiles.map((source) => source.startsWith("http") ? `<a href="${source}" target="_blank" rel="noreferrer">${escapeHtml(source)} ${icon("ExternalLink")}</a>` : `<code>${escapeHtml(source)}</code>`).join("")}</footer>
      </article>
    </div>`;
  }
  return `
    ${pageHeader("REFERENCE / REVIEW", "参考仓库", `${referenceRepos.length} 个已核对基线`, actions)}
    <div class="reference-toolbar"><div class="segmented-control"><button data-reference-view="detail">详细分析</button><button data-reference-view="matrix">对比矩阵</button></div><span>代码核对日期 <strong class="mono">2026-07-17</strong></span></div>
    <div class="scroll-area references-page">${content}</div>`;
}

function referenceField(iconName, title, content) {
  return `<section><h3>${icon(iconName)} ${title}</h3>${content.split("\n").map((line) => line ? `<p>${escapeHtml(line)}</p>` : "<br>").join("")}</section>`;
}

function renderExperiments() {
  const experiments = state.experiments.slice().sort((a, b) => b.date.localeCompare(a.date));
  const selected = state.experiments.find((item) => item.id === selectedExperiment) || experiments[0];
  return `
    ${pageHeader("EXPERIMENT / LOG", "实验记录", `${state.experiments.length} 条实验 / ${state.decisions.length} 条决策`, `
      <button class="button secondary" id="add-decision">${icon("PencilLine")}<span>新建决策</span></button>
      <button class="button primary" id="add-experiment">${icon("Plus")}<span>新建实验</span></button>`)}
    <div class="page-divider"></div>
    <div class="scroll-area experiments-page">
      <section class="experiment-section">
        <div class="section-title"><div><span>RUNS</span><h2>训练与评估</h2></div></div>
        <div class="experiment-layout">
          <div class="data-table-wrap"><table class="data-table experiment-table"><thead><tr><th>日期</th><th>名称</th><th>仿真器</th><th>Run / Checkpoint</th><th>状态</th><th></th></tr></thead><tbody>
            ${experiments.map((experiment) => `<tr data-experiment-row="${experiment.id}" class="${selected?.id === experiment.id ? "is-selected" : ""}"><td class="mono">${experiment.date}</td><td><strong>${escapeHtml(experiment.name)}</strong><small>${escapeHtml(experiment.task)}</small></td><td>${escapeHtml(experiment.simulator)}</td><td class="mono">${escapeHtml(experiment.run)}</td><td><span class="status-label" data-state="${experiment.status}">${experiment.status}</span></td><td><button class="icon-button delete-experiment" data-delete-experiment="${experiment.id}" title="删除实验" aria-label="删除实验">${icon("Trash2")}</button></td></tr>`).join("") || '<tr><td colspan="6" class="empty-state">暂无实验记录</td></tr>'}
          </tbody></table></div>
          ${selected ? `<article class="experiment-detail">
            <header><div><span class="eyebrow">${selected.date} / SEED ${escapeHtml(selected.seed)}</span><h3>${escapeHtml(selected.name)}</h3><p class="mono">${escapeHtml(selected.task)}</p></div><span class="status-label" data-state="${selected.status}">${selected.status}</span></header>
            ${experimentDetailField("假设", selected.hypothesis)}
            ${experimentDetailField("修改", selected.changes)}
            ${experimentDetailField("结果", selected.result)}
            ${experimentDetailField("下一步", selected.next)}
            <footer>${icon("FileCode2")}<code>${escapeHtml(selected.evidence)}</code></footer>
          </article>` : ""}
        </div>
      </section>
      <section class="experiment-section">
        <div class="section-title"><div><span>DECISIONS</span><h2>决策与风险</h2></div></div>
        <div class="decision-list">${state.decisions.slice().sort((a, b) => b.date.localeCompare(a.date)).map((decision) => `<div class="decision-entry">${decisionRow(decision)}<button class="icon-button delete-decision" data-delete-decision="${decision.id}" title="删除决策" aria-label="删除决策">${icon("Trash2")}</button></div>`).join("") || '<div class="empty-state">暂无决策记录</div>'}</div>
      </section>
    </div>
    ${experimentDialog()}
    ${decisionDialog()}`;
}

function experimentDetailField(label, value) {
  return `<section><span>${label}</span><p>${escapeHtml(value)}</p></section>`;
}

function experimentDialog() {
  return `<dialog id="experiment-dialog" class="record-dialog"><form method="dialog" id="experiment-form">
    <header><div><span class="eyebrow">NEW RUN</span><h2>新建实验</h2></div><button class="icon-button" value="cancel" title="关闭" aria-label="关闭">${icon("X")}</button></header>
    <div class="dialog-grid">
      ${inputField("date", "日期", "date", new Date().toISOString().slice(0, 10), true)}
      ${inputField("name", "实验名称", "text", "", true, "wide")}
      ${inputField("simulator", "仿真器", "text", "Isaac Lab", true)}
      ${inputField("task", "Task", "text", "DDT-Velocity-Flat-Swingboy-v0", true, "wide mono-input")}
      ${inputField("run", "Run / Checkpoint", "text", "", true, "mono-input")}
      ${inputField("seed", "Seed", "number", "42", true)}
      <label class="form-field"><span>状态</span><select name="status"><option>计划中</option><option>训练中</option><option>待复盘</option><option>已验收</option><option>已失败</option></select></label>
      ${textareaField("hypothesis", "假设", true)}
      ${textareaField("changes", "修改", true)}
      ${textareaField("result", "结果")}
      ${textareaField("next", "下一步")}
      ${inputField("evidence", "证据路径", "text", "logs/", false, "wide mono-input")}
    </div>
    <footer><button class="button secondary" value="cancel">取消</button><button class="button primary" value="default" id="submit-experiment">${icon("Save")}<span>保存实验</span></button></footer>
  </form></dialog>`;
}

function decisionDialog() {
  return `<dialog id="decision-dialog" class="record-dialog small-dialog"><form method="dialog" id="decision-form">
    <header><div><span class="eyebrow">DECISION LOG</span><h2>新建决策</h2></div><button class="icon-button" value="cancel" title="关闭" aria-label="关闭">${icon("X")}</button></header>
    <div class="dialog-grid">
      ${inputField("date", "日期", "date", new Date().toISOString().slice(0, 10), true)}
      <label class="form-field"><span>类型</span><select name="type"><option>决策</option><option>风险</option><option>结论</option></select></label>
      ${inputField("title", "标题", "text", "", true, "wide")}
      ${textareaField("detail", "详细记录", true)}
      <label class="form-field"><span>状态</span><select name="state"><option>未解决</option><option>进行中</option><option>已采用</option><option>已关闭</option></select></label>
    </div>
    <footer><button class="button secondary" value="cancel">取消</button><button class="button primary" value="default" id="submit-decision">${icon("Save")}<span>保存决策</span></button></footer>
  </form></dialog>`;
}

function inputField(name, label, type = "text", value = "", required = false, className = "") {
  return `<label class="form-field ${className}"><span>${label}</span><input name="${name}" type="${type}" value="${escapeHtml(value)}" ${required ? "required" : ""} /></label>`;
}

function textareaField(name, label, required = false) {
  return `<label class="form-field full"><span>${label}</span><textarea name="${name}" ${required ? "required" : ""}></textarea></label>`;
}

function bindPageEvents() {
  bindGlobalActions();
  document.querySelectorAll("[data-go]").forEach((button) => button.addEventListener("click", () => {
    activePage = button.dataset.go;
    selectedExperiment = button.dataset.experiment || selectedExperiment;
    window.location.hash = activePage;
    renderPage();
    if (button.dataset.scroll) requestAnimationFrame(() => document.querySelector(`#section-${button.dataset.scroll}`)?.scrollIntoView());
  }));
  document.querySelectorAll("[data-experiment]").forEach((button) => button.addEventListener("click", () => {
    selectedExperiment = button.dataset.experiment;
    activePage = "experiments";
    window.location.hash = activePage;
    renderPage();
  }));

  document.querySelectorAll("[data-check-filter]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.checkFilter === checklistFilter);
    button.addEventListener("click", () => { checklistFilter = button.dataset.checkFilter; renderPage(); });
  });
  document.querySelectorAll("[data-check-id]").forEach((input) => input.addEventListener("change", () => {
    state.checklist[input.dataset.checkId].done = input.checked;
    saveState();
    renderPage();
  }));
  document.querySelectorAll("[data-check-note]").forEach((input) => input.addEventListener("change", () => {
    state.checklist[input.dataset.checkNote].note = input.value.trim();
    saveState("检查记录已保存");
  }));

  document.querySelector("#save-baseline")?.addEventListener("click", () => {
    document.querySelectorAll("[data-baseline]").forEach((input) => { state.baseline[input.dataset.baseline] = input.value.trim(); });
    saveState("机器人基线已保存");
  });

  document.querySelectorAll("[data-mdp-tab]").forEach((button) => button.addEventListener("click", () => { mdpTab = button.dataset.mdpTab; renderPage(); }));
  document.querySelector("#mdp-notes")?.addEventListener("change", (event) => { state.mdpNotes = event.target.value; saveState("MDP 审核记录已保存"); });

  document.querySelectorAll("[data-reference-view]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.referenceView === referenceView);
    button.addEventListener("click", () => { referenceView = button.dataset.referenceView; renderPage(); });
  });
  document.querySelectorAll("[data-reference]").forEach((button) => button.addEventListener("click", () => { selectedReference = button.dataset.reference; renderPage(); }));
  document.querySelector("#reference-search")?.addEventListener("input", (event) => {
    referenceQuery = event.target.value;
    window.clearTimeout(event.target._renderTimer);
    event.target._renderTimer = window.setTimeout(renderPage, 180);
  });

  document.querySelectorAll("[data-experiment-row]").forEach((row) => row.addEventListener("click", (event) => {
    if (event.target.closest("button")) return;
    selectedExperiment = row.dataset.experimentRow;
    renderPage();
  }));
  document.querySelectorAll("[data-delete-experiment]").forEach((button) => button.addEventListener("click", () => {
    if (!window.confirm("确定删除这条实验记录？")) return;
    state.experiments = state.experiments.filter((item) => item.id !== button.dataset.deleteExperiment);
    if (selectedExperiment === button.dataset.deleteExperiment) selectedExperiment = null;
    saveState("实验记录已删除");
    renderPage();
  }));
  document.querySelectorAll("[data-delete-decision]").forEach((button) => button.addEventListener("click", () => {
    if (!window.confirm("确定删除这条决策记录？")) return;
    state.decisions = state.decisions.filter((item) => item.id !== button.dataset.deleteDecision);
    saveState("决策记录已删除");
    renderPage();
  }));
  document.querySelector("#add-experiment")?.addEventListener("click", () => document.querySelector("#experiment-dialog").showModal());
  document.querySelector("#add-decision")?.addEventListener("click", () => document.querySelector("#decision-dialog").showModal());
  document.querySelector("#submit-experiment")?.addEventListener("click", (event) => {
    const form = document.querySelector("#experiment-form");
    if (!form.reportValidity()) { event.preventDefault(); return; }
    const values = Object.fromEntries(new FormData(form));
    const item = { id: `exp-${Date.now()}`, ...values };
    state.experiments.push(item);
    selectedExperiment = item.id;
    saveState("实验记录已保存");
    window.setTimeout(renderPage, 0);
  });
  document.querySelector("#submit-decision")?.addEventListener("click", (event) => {
    const form = document.querySelector("#decision-form");
    if (!form.reportValidity()) { event.preventDefault(); return; }
    const values = Object.fromEntries(new FormData(form));
    state.decisions.push({ id: `decision-${Date.now()}`, ...values });
    saveState("决策记录已保存");
    window.setTimeout(renderPage, 0);
  });
}

function exportData() {
  saveState();
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `swingboy-rl-notes-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  showToast("记录已导出");
}

function importData(event) {
  const [file] = event.target.files;
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const imported = JSON.parse(reader.result);
      if (imported.schema !== 1) throw new Error("schema");
      state = { ...defaultState(), ...imported };
      saveState();
      renderPage();
      showToast("记录已导入");
    } catch {
      showToast("导入失败：文件格式不匹配", "danger");
    }
    event.target.value = "";
  });
  reader.readAsText(file);
}

window.addEventListener("hashchange", () => {
  const requested = window.location.hash.replace("#", "");
  if (requested && requested !== activePage) {
    activePage = requested;
    renderPage();
  }
});

renderShell();
