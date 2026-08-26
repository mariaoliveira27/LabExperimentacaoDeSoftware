"use strict";

const DATASETS = {
  1000: { folder: "CSV - 1000", label: "1.000 repositórios" },
  100: { folder: "CSV - 100", label: "100 repositórios" },
};

const FILES = {
  repositories: "repositorios_populares.csv",
  languages: "popularidade_linguagem.csv",
  pullRequests: "pull_requests_aceitas.csv",
  releases: "release.csv",
  frequencies: "frequencia_issues.csv",
  issues: "percentual_issues_fechadas.csv",
  bonus: "bonus.csv",
};

const state = {
  sample: "1000",
  language: "__all__",
  search: "",
  data: null,
  visibleRows: 12,
  tableTagRange: null,
  selectedRepository: null,
  repositorySort: { key: "stars", direction: "desc" },
  languageStatsSort: { key: "pullRequests", direction: "desc" },
  languageMetric: "pullRequests",
  showSmallLanguageGroups: false,
};

const TAG_RANGES = [
  { key: "zero", label: "0", description: "sem tags", predicate: (value) => value === 0 },
  { key: "one-five", label: "1–5", description: "entre 1 e 5 tags", predicate: (value) => value >= 1 && value <= 5 },
  { key: "six-twenty-five", label: "6–25", description: "entre 6 e 25 tags", predicate: (value) => value > 5 && value <= 25 },
  { key: "twenty-six-one-hundred", label: "26–100", description: "entre 26 e 100 tags", predicate: (value) => value > 25 && value <= 100 },
  { key: "one-oh-one-five-hundred", label: "101–500", description: "entre 101 e 500 tags", predicate: (value) => value > 100 && value <= 500 },
  { key: "five-hundred-plus", label: "+500", description: "mais de 500 tags", predicate: (value) => value > 500 },
];

const LANGUAGE_METRICS = {
  pullRequests: { title: "PRs médias por linguagem", label: "PRs", format: "compact", direction: "desc", colors: ["#1677c8", "#2385cf", "#3194d6", "#45a3dc", "#5cb2e2", "#75c0e8", "#8acdec", "#a1d9f0"] },
  releases: { title: "Releases médias por linguagem", label: "releases", format: "decimal", direction: "desc", colors: ["#7357d8", "#8468de", "#9578e5", "#a88aed", "#ba9df1", "#cab0f5", "#d9c4f8", "#e7d8fb"] },
  issues: { title: "Atividade média de issues", label: "issues/mês", format: "decimal", direction: "desc", colors: ["#e48d2c", "#e99e40", "#edaf57", "#f1bf70", "#f4ce8a", "#f6dba3", "#f8e7bd", "#fbf1d7"] },
  inactiveDays: { title: "Dias médios sem atualizar", label: "dias sem atualizar", format: "days", direction: "asc", colors: ["#e26c57", "#e98270", "#ee9788", "#f2aca0", "#f5c0b7", "#f8d2ca", "#fae2dc", "#fceedf"] },
};

const formatter = new Intl.NumberFormat("pt-BR");
const compactFormatter = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
const decimalFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'\"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;",
  }[character]));
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const next = text[index + 1];
    if (character === "\"") {
      if (quoted && next === "\"") {
        field += "\"";
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && next === "\n") index += 1;
      row.push(field);
      if (row.some((item) => item.trim() !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }
  row.push(field);
  if (row.some((item) => item.trim() !== "")) rows.push(row);

  if (!rows.length) return [];
  const headers = rows.shift().map((header) => header.trim().replace(/^\uFEFF/, ""));
  return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, (values[index] || "").trim()])));
}

function parseNumber(value, fallback = 0) {
  const match = String(value ?? "").match(/-?[\d.,]+/);
  if (!match) return fallback;
  let normalized = match[0];
  if (normalized.includes(",") && normalized.includes(".")) {
    normalized = normalized.replace(/\./g, "").replace(",", ".");
  } else {
    normalized = normalized.replace(",", ".");
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function optionalNumber(row, field) {
  if (!row || !Object.hasOwn(row, field) || String(row[field]).trim() === "") return null;
  return parseNumber(row[field], null);
}

function parseFrequency(value) {
  const label = String(value ?? "").trim();
  const normalized = label.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  if (!label || normalized.includes("sem issues") || normalized === "n/a") return null;
  if (normalized.includes("multiplas issues")) return 900;
  if (normalized.includes("apenas 1 issue")) return 0.1;
  return parseNumber(label, null);
}

function median(values) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return 0;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function sum(values) {
  return values.reduce((total, value) => total + (Number.isFinite(value) ? value : 0), 0);
}

function average(values) {
  const cleanValues = values.filter(Number.isFinite);
  return cleanValues.length ? sum(cleanValues) / cleanValues.length : 0;
}

function normalizeSearch(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
}

function getMap(rows, key) {
  return new Map(rows.map((row) => [row[key], row]));
}

function yearsSince(dateValue) {
  const date = new Date(dateValue);
  return Number.isNaN(date.getTime()) ? 0 : (Date.now() - date.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
}

async function fetchCsv(folder, filename) {
  const response = await fetch(encodeURI(`../${folder}/${filename}`), { cache: "no-store" });
  if (!response.ok) throw new Error(`Não foi possível abrir ${filename} (${response.status}).`);
  return parseCsv(await response.text());
}

async function loadDataset(sample) {
  const { folder } = DATASETS[sample];
  const entries = await Promise.all(Object.entries(FILES).map(async ([key, filename]) => [key, await fetchCsv(folder, filename)]));
  const rows = Object.fromEntries(entries);
  const languageMap = getMap(rows.languages, "Repositorio");
  const prMap = getMap(rows.pullRequests, "Repositorio");
  const releaseMap = getMap(rows.releases, "Repositorio");
  const frequencyMap = getMap(rows.frequencies, "Repositorio");
  const issueMap = getMap(rows.issues, "Repositorio");

  const repositories = rows.repositories.map((repository) => {
    const name = repository.Repositorio;
    const language = languageMap.get(name) || {};
    const pullRequest = prMap.get(name) || {};
    const release = releaseMap.get(name) || {};
    const frequency = frequencyMap.get(name) || {};
    const issue = issueMap.get(name) || {};
    return {
      name,
      createdAt: repository["Criado Em"],
      stars: parseNumber(repository.Estrelas),
      language: language["Linguagem Primaria"] || "Sem linguagem",
      allLanguages: language.Linguagens || "Sem linguagem",
      pullRequests: optionalNumber(pullRequest, "Pull Requests Aceitas"),
      releases: optionalNumber(release, "Tags"),
      hasFrequency: frequencyMap.has(name),
      frequency: frequencyMap.has(name) ? parseFrequency(frequency["Frequencia issues"]) : null,
      frequencyLabel: frequencyMap.has(name) ? frequency["Frequencia issues"] : "Não informado",
      hasIssuesData: issueMap.has(name),
      totalIssues: optionalNumber(issue, "Total de Issues"),
      closedIssues: optionalNumber(issue, "Issues Fechadas"),
      closedIssuePercent: optionalNumber(issue, "Percentual de Issues Fechadas"),
    };
  });

  return { repositories, bonus: rows.bonus };
}

function getAnalysisRepositories() {
  if (!state.data) return [];
  return state.data.repositories.filter((repository) => (
    (state.language === "__all__" || repository.language === state.language)
  ));
}

function getTagRange() {
  return TAG_RANGES.find((range) => range.key === state.tableTagRange) || null;
}

function getTableRepositories(analysisRepositories = getAnalysisRepositories()) {
  const search = normalizeSearch(state.search);
  const tagRange = getTagRange();
  return analysisRepositories.filter((repository) => (
    (!search || normalizeSearch(repository.name).includes(search))
    && (!tagRange || (Number.isFinite(repository.releases) && tagRange.predicate(repository.releases)))
  ));
}

function groupEntries(items, getKey) {
  const groups = new Map();
  items.forEach((item) => {
    const key = getKey(item);
    groups.set(key, (groups.get(key) || 0) + 1);
  });
  return [...groups.entries()].map(([label, value]) => ({ label, value }));
}

function getDistribution(values, definitions) {
  return definitions.map(({ label, predicate }) => ({ label, value: values.filter(predicate).length }));
}

function topEntries(repositories, key, count = 6) {
  return repositories
    .filter((repository) => Number.isFinite(repository[key]))
    .sort((a, b) => b[key] - a[key])
    .slice(0, count)
    .map((repository) => ({ key: repository.name, label: repository.name, value: repository[key] }));
}

function formatOptional(value, valueFormatter = formatter) {
  return Number.isFinite(value) ? valueFormatter.format(value) : "—";
}

function formatLanguageMetric(value, metric) {
  if (!Number.isFinite(value)) return "—";
  if (metric.format === "compact") return compactFormatter.format(value);
  if (metric.format === "days") return `${decimalFormatter.format(value)} dias`;
  return decimalFormatter.format(value);
}

function repositoryUrl(name) {
  return `https://github.com/${String(name).split("/").map(encodeURIComponent).join("/")}`;
}

function sortRows(rows, sort, fallbackKey) {
  const { key = fallbackKey, direction = "desc" } = sort;
  const multiplier = direction === "asc" ? 1 : -1;
  return [...rows].sort((first, second) => {
    const firstValue = first[key];
    const secondValue = second[key];
    const firstMissing = !Number.isFinite(firstValue) && typeof firstValue !== "string";
    const secondMissing = !Number.isFinite(secondValue) && typeof secondValue !== "string";
    if (firstMissing || secondMissing) return firstMissing === secondMissing ? 0 : (firstMissing ? 1 : -1);
    if (typeof firstValue === "string" || typeof secondValue === "string") return multiplier * String(firstValue).localeCompare(String(secondValue), "pt-BR");
    return multiplier * (firstValue - secondValue);
  });
}

function frequencyBucket(repository) {
  if (!repository.hasFrequency) return "Sem dados";
  const normalized = String(repository.frequencyLabel || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  if (normalized.includes("sem issues")) return "Sem issues";
  if (normalized.includes("multiplas issues")) return "Múltiplas/dia";
  const value = repository.frequency;
  if (!Number.isFinite(value)) return "Sem dados";
  if (value === 0) return "0/mês";
  if (value <= 10) return "1–10/mês";
  if (value <= 100) return "11–100/mês";
  if (value < 300) return "101–299/mês";
  return "≥300/mês";
}

function setChartEmpty(container, message = "Não há dados para este recorte.") {
  container.innerHTML = `<div class="empty-chart">${escapeHtml(message)}</div>`;
}

function renderHorizontalBars(container, entries, options = {}) {
  if (!entries.length || entries.every((entry) => !entry.value)) {
    setChartEmpty(container);
    return;
  }
  const maxValue = Math.max(...entries.map((entry) => entry.value), 1);
  const colors = options.colors || ["#1677c8", "#0f9f8c", "#7357d8", "#ec9b24", "#e36b57", "#4387c2", "#41ae9d", "#9a7bea"];
  const valueFormat = options.format || ((value) => formatter.format(value));
  container.innerHTML = `<div class="horizontal-bars">${entries.map((entry, index) => {
    const width = entry.value ? Math.max(1.5, (entry.value / maxValue) * 100) : 0;
    const key = entry.key ?? entry.label;
    const tooltip = options.tooltip ? options.tooltip(entry) : `${entry.label}: ${valueFormat(entry.value)}`;
    const interactive = Boolean(options.action);
    const selected = options.selectedValue === key;
    const attributes = interactive
      ? `type="button" data-chart-action="${escapeHtml(options.action)}" data-chart-value="${escapeHtml(key)}" aria-pressed="${selected}" aria-controls="repositories-table" aria-label="${escapeHtml(options.ariaLabel ? options.ariaLabel(entry) : tooltip)}"`
      : "";
    const tag = interactive ? "button" : "div";
    return `<${tag} class="bar-row${interactive ? " chart-control" : ""}${selected ? " is-selected" : ""}" data-tooltip="${escapeHtml(tooltip)}" ${attributes}>
      <span class="bar-label">${escapeHtml(entry.label)}</span>
      <span class="bar-track"><span class="bar-fill" style="--bar-width:${width}%;--bar-color:${colors[index % colors.length]}"></span></span>
      <strong class="bar-value">${escapeHtml(valueFormat(entry.value))}</strong>
    </${tag}>`;
  }).join("")}</div>`;
}

function renderVerticalBars(container, entries, options = {}) {
  if (!entries.length || entries.every((entry) => !entry.value)) {
    setChartEmpty(container);
    return;
  }
  const maxValue = Math.max(...entries.map((entry) => entry.value), 1);
  const colors = options.colors || ["#1677c8", "#0f9f8c", "#7357d8", "#ec9b24", "#e36b57", "#4387c2", "#41ae9d"];
  const valueFormat = options.format || ((value) => formatter.format(value));
  container.innerHTML = `<div class="vertical-bars">${entries.map((entry, index) => {
    const height = entry.value ? Math.max(2, (entry.value / maxValue) * 100) : 0;
    const key = entry.key ?? entry.label;
    const tooltip = options.tooltip ? options.tooltip(entry) : `${entry.label}: ${valueFormat(entry.value)}`;
    const interactive = Boolean(options.action);
    const selected = options.selectedValue === key;
    const attributes = interactive
      ? `type="button" data-chart-action="${escapeHtml(options.action)}" data-chart-value="${escapeHtml(key)}" aria-pressed="${selected}" aria-controls="repositories-table" aria-label="${escapeHtml(options.ariaLabel ? options.ariaLabel(entry) : tooltip)}"`
      : "";
    const tag = interactive ? "button" : "div";
    return `<${tag} class="v-bar${interactive ? " chart-control" : ""}${selected ? " is-selected" : ""}" data-tooltip="${escapeHtml(tooltip)}" ${attributes}>
      <div class="v-bar-stack" data-value="${escapeHtml(valueFormat(entry.value))}"><span class="v-bar-fill" style="--bar-height:${height}%;--bar-color:${colors[index % colors.length]}"></span></div>
      <span class="v-bar-label">${escapeHtml(entry.label)}</span>
    </${tag}>`;
  }).join("")}</div>`;
}

function setKpis(repositories) {
  const issueRows = repositories.filter((repository) => repository.hasIssuesData && repository.totalIssues > 0);
  const totalIssues = sum(issueRows.map((repository) => repository.totalIssues));
  const closedIssues = sum(issueRows.map((repository) => repository.closedIssues));
  const cards = [
    { label: "Repositórios", value: formatter.format(repositories.length), foot: "no recorte atual", tone: "" },
    { label: "Estrelas acumuladas", value: compactFormatter.format(sum(repositories.map((repository) => repository.stars))), foot: "popularidade total", tone: "tone-teal" },
    { label: "Idade mediana", value: `${decimalFormatter.format(median(repositories.map((repository) => yearsSince(repository.createdAt))))} anos`, foot: "desde a criação", tone: "tone-violet" },
    { label: "PRs aceitas", value: compactFormatter.format(sum(repositories.map((repository) => repository.pullRequests))), foot: `${formatter.format(Math.round(median(repositories.map((repository) => repository.pullRequests))))} na mediana`, tone: "tone-amber" },
    { label: "Issues fechadas", value: totalIssues ? `${decimalFormatter.format((closedIssues / totalIssues) * 100)}%` : "—", foot: "razão sobre o total", tone: "tone-coral" },
  ];
  $("#kpi-grid").innerHTML = cards.map((card) => `<article class="kpi-card ${card.tone}"><span class="kpi-label">${card.label}</span><strong class="kpi-value">${card.value}</strong><span class="kpi-foot">${card.foot}</span></article>`).join("");
}

function renderOverview(repositories) {
  const ageEntries = getDistribution(repositories.map((repository) => yearsSince(repository.createdAt)), [
    { label: "até 2 anos", predicate: (value) => value <= 2 },
    { label: "2–5 anos", predicate: (value) => value > 2 && value <= 5 },
    { label: "5–8 anos", predicate: (value) => value > 5 && value <= 8 },
    { label: "8–12 anos", predicate: (value) => value > 8 && value <= 12 },
    { label: "12–16 anos", predicate: (value) => value > 12 && value <= 16 },
    { label: "+16 anos", predicate: (value) => value > 16 },
  ]);
  renderVerticalBars($("#age-chart"), ageEntries, { colors: ["#76aee0", "#5599d6", "#337fc2", "#1677c8", "#0e629f", "#084d7d"] });
  $("#age-summary").textContent = `mediana: ${decimalFormatter.format(median(repositories.map((repository) => yearsSince(repository.createdAt))))} anos`;

  const languages = groupEntries(repositories, (repository) => repository.language)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
  renderHorizontalBars($("#language-chart"), languages, {
    action: "language",
    selectedValue: state.language,
    colors: ["#0f9f8c", "#1e9a9d", "#358db1", "#517dc2", "#7357d8", "#a05acc", "#ce6a9d", "#df846a"],
    tooltip: (entry) => `${entry.label}: ${formatter.format(entry.value)} repositórios · clique para filtrar`,
    ariaLabel: (entry) => `Filtrar por ${entry.label}: ${formatter.format(entry.value)} repositórios`,
  });
  $("#language-chart-summary").textContent = state.language === "__all__" ? "clique para filtrar" : `filtro: ${state.language}`;
}

function renderContributions(repositories) {
  const prValues = repositories.map((repository) => repository.pullRequests).filter(Number.isFinite);
  const distribution = getDistribution(prValues, [
    { label: "0", predicate: (value) => value === 0 },
    { label: "1–10", predicate: (value) => value >= 1 && value <= 10 },
    { label: "11–100", predicate: (value) => value > 10 && value <= 100 },
    { label: "101–1 mil", predicate: (value) => value > 100 && value <= 1000 },
    { label: "1–10 mil", predicate: (value) => value > 1000 && value <= 10000 },
    { label: "+10 mil", predicate: (value) => value > 10000 },
  ]);
  renderVerticalBars($("#pr-distribution-chart"), distribution, { colors: ["#b4d4ec", "#8fc0e6", "#62a8dc", "#378dce", "#1677c8", "#0c5f9f"] });
  $("#pr-summary").textContent = `mediana: ${formatter.format(Math.round(median(prValues)))} · ${formatter.format(prValues.length)} com dados`;
  renderHorizontalBars($("#pr-leaders-chart"), topEntries(repositories, "pullRequests"), {
    action: "repository",
    selectedValue: state.selectedRepository,
    format: (value) => compactFormatter.format(value),
    colors: ["#0f9f8c", "#1dab96", "#2bb7a4", "#5ac7b8", "#75d2c5", "#91ddcf"],
    tooltip: (entry) => `${entry.label}: ${compactFormatter.format(entry.value)} PRs aceitas · clique para destacar na tabela`,
    ariaLabel: (entry) => `Destacar ${entry.label} na tabela: ${compactFormatter.format(entry.value)} PRs aceitas`,
  });
}

function renderReleases(repositories) {
  const releaseValues = repositories.map((repository) => repository.releases).filter(Number.isFinite);
  const distribution = TAG_RANGES.map((range) => ({
    key: range.key,
    label: range.label,
    value: releaseValues.filter(range.predicate).length,
  }));
  renderVerticalBars($("#release-distribution-chart"), distribution, {
    action: "table-tag-range",
    selectedValue: state.tableTagRange,
    colors: ["#d8ccfb", "#bcaaf4", "#9c82e8", "#8269dc", "#6850c8", "#503cab"],
    tooltip: (entry) => `${entry.label} tags: ${formatter.format(entry.value)} repositórios · filtrar a tabela`,
    ariaLabel: (entry) => `Filtrar tabela por ${TAG_RANGES.find((range) => range.key === entry.key)?.description}: ${formatter.format(entry.value)} repositórios`,
  });
  const withReleases = releaseValues.filter((value) => value > 0).length;
  $("#release-summary").textContent = `${decimalFormatter.format((withReleases / Math.max(releaseValues.length, 1)) * 100)}% com tags · clique para filtrar a tabela`;
  renderHorizontalBars($("#release-leaders-chart"), topEntries(repositories, "releases"), {
    action: "repository",
    selectedValue: state.selectedRepository,
    colors: ["#7357d8", "#886cdf", "#9b7fe5", "#ad92ec", "#bea4f0", "#d0b7f5"],
    tooltip: (entry) => `${entry.label}: ${formatter.format(entry.value)} tags · clique para destacar na tabela`,
    ariaLabel: (entry) => `Destacar ${entry.label} na tabela: ${formatter.format(entry.value)} tags`,
  });
}

function renderMaintenance(repositories) {
  const categoryOrder = ["Sem issues", "0/mês", "1–10/mês", "11–100/mês", "101–299/mês", "≥300/mês", "Múltiplas/dia", "Sem dados"];
  const categoryCounts = groupEntries(repositories, frequencyBucket);
  const distribution = categoryOrder.map((label) => ({ label, value: categoryCounts.find((entry) => entry.label === label)?.value || 0 }));
  renderVerticalBars($("#issue-frequency-chart"), distribution, { colors: ["#d8dee6", "#f4d7ad", "#efbd72", "#eaa044", "#e2822c", "#cd641d", "#ac4d17", "#b5c4d0"] });
  const frequencyCoverage = repositories.filter((repository) => repository.hasFrequency).length;
  $("#frequency-summary").textContent = `proxy · ${formatter.format(frequencyCoverage)} com dados`;

  const reportedIssueRows = repositories.filter((repository) => repository.hasIssuesData);
  const issueRows = reportedIssueRows.filter((repository) => repository.totalIssues > 0);
  const noIssues = reportedIssueRows.filter((repository) => repository.totalIssues === 0).length;
  const totalIssues = sum(issueRows.map((repository) => repository.totalIssues));
  const closedIssues = sum(issueRows.map((repository) => repository.closedIssues));
  const closedPercent = totalIssues ? (closedIssues / totalIssues) * 100 : 0;
  $("#issue-summary").textContent = `${formatter.format(reportedIssueRows.length)} de ${formatter.format(repositories.length)} com dados`;
  $("#issue-resolution").innerHTML = `<div class="donut" style="--donut-value:${closedPercent.toFixed(2)}"><span class="donut-label">${decimalFormatter.format(closedPercent)}%</span></div><div class="resolution-copy"><strong>${formatter.format(closedIssues)} issues fechadas</strong><p>de ${formatter.format(totalIssues)} issues observadas; ${formatter.format(noIssues)} repos. sem issues.</p></div>`;
  const issueDistribution = getDistribution(issueRows.map((repository) => repository.closedIssuePercent ?? 0), [
    { label: "0–25%", predicate: (value) => value <= 25 },
    { label: "26–50%", predicate: (value) => value > 25 && value <= 50 },
    { label: "51–75%", predicate: (value) => value > 50 && value <= 75 },
    { label: "76–100%", predicate: (value) => value > 75 },
    { label: "sem issues", predicate: () => false },
  ]);
  issueDistribution[issueDistribution.length - 1].value = noIssues;
  renderVerticalBars($("#issue-distribution-chart"), issueDistribution, { colors: ["#e8b9b2", "#e49589", "#dc796a", "#c95a4d"] });
}

function getBonusLanguageRows() {
  return state.data.bonus
    .filter((row) => state.language === "__all__" || row.Linguagem === state.language)
    .map((row) => {
      const rawInactiveDays = parseNumber(row["Media Dias Sem Atualizar"], null);
      return {
        language: row.Linguagem,
        repositories: parseNumber(row["Total de Repositorios"]),
        pullRequests: parseNumber(row["Media PRs"]),
        releases: parseNumber(row["Media Releases"]),
        inactiveDays: Number.isFinite(rawInactiveDays) && rawInactiveDays >= 0 ? rawInactiveDays : null,
        issues: parseNumber(row["Media Frequencia Issues"]),
      };
    });
}

function getVisibleLanguageRows() {
  const allRows = getBonusLanguageRows();
  const reliableRows = allRows.filter((row) => row.repositories >= 10);
  if (state.language !== "__all__" || state.showSmallLanguageGroups || !reliableRows.length) return { allRows, rows: allRows, hiddenCount: 0 };
  return { allRows, rows: reliableRows, hiddenCount: allRows.length - reliableRows.length };
}

function renderLanguageInsights() {
  const { allRows, rows: languageRows, hiddenCount } = getVisibleLanguageRows();
  const metric = LANGUAGE_METRICS[state.languageMetric];
  const metricRows = sortRows(
    languageRows.filter((row) => Number.isFinite(row[state.languageMetric]) && (state.languageMetric !== "inactiveDays" || row.inactiveDays >= 0)),
    { key: state.languageMetric, direction: metric.direction },
    state.languageMetric,
  );
  const graphRows = metricRows.slice(0, 8).map((row) => ({ key: row.language, label: row.language, value: row[state.languageMetric] }));
  $("#language-metric-title").textContent = metric.title;
  $("#language-summary").textContent = state.language === "__all__"
    ? `${formatter.format(languageRows.length)} linguagens${hiddenCount ? ` · ${formatter.format(hiddenCount)} ocultas` : ""}`
    : `${formatter.format(languageRows[0]?.repositories || 0)} repos. na linguagem`;
  $("#toggle-small-languages").textContent = state.showSmallLanguageGroups ? "Ocultar grupos menores" : `Ver todas (${formatter.format(allRows.length)})`;
  $("#toggle-small-languages").hidden = state.language !== "__all__" || allRows.length === languageRows.length;

  renderHorizontalBars($("#language-metric-chart"), graphRows, {
    action: "language",
    selectedValue: state.language,
    format: (value) => formatLanguageMetric(value, metric),
    colors: metric.colors,
    tooltip: (entry) => `${entry.label}: ${formatLanguageMetric(entry.value, metric)} · clique para filtrar`,
    ariaLabel: (entry) => `Filtrar por ${entry.label}: ${formatLanguageMetric(entry.value, metric)}`,
  });

  const tableRows = sortRows(languageRows, state.languageStatsSort, "pullRequests").slice(0, state.showSmallLanguageGroups ? 12 : 8);
  $("#language-stats-table").innerHTML = tableRows.length ? tableRows.map((row) => `<tr>
    <td><button class="table-link-button" type="button" data-chart-action="language" data-chart-value="${escapeHtml(row.language)}" aria-label="Filtrar por ${escapeHtml(row.language)}">${escapeHtml(row.language)}</button></td>
    <td>${formatter.format(row.repositories)}</td>
    <td>${compactFormatter.format(row.pullRequests)}</td>
    <td>${decimalFormatter.format(row.releases)}</td>
    <td>${Number.isFinite(row.inactiveDays) ? `${decimalFormatter.format(row.inactiveDays)} dias` : "—"}</td>
  </tr>`).join("") : `<tr><td colspan="5">Nenhuma linguagem encontrada.</td></tr>`;
  syncLanguageMetricControls();
  syncSortControls();
}

function repositorySortLabel(key) {
  return ({ name: "repositório", language: "linguagem", stars: "estrelas", pullRequests: "PRs", releases: "tags", closedIssuePercent: "issues fechadas" })[key] || key;
}

function renderRepositorySpotlight(analysisRepositories) {
  const spotlight = $("#repository-spotlight");
  const repository = analysisRepositories.find((row) => row.name === state.selectedRepository);
  if (!repository) {
    spotlight.hidden = true;
    spotlight.innerHTML = "";
    return;
  }
  spotlight.hidden = false;
  spotlight.innerHTML = `<div><span class="spotlight-kicker">Projeto selecionado</span><strong>${escapeHtml(repository.name)}</strong><p>${compactFormatter.format(repository.stars)} estrelas · ${formatOptional(repository.pullRequests, compactFormatter)} PRs · ${formatOptional(repository.releases)} tags</p></div><div class="spotlight-actions"><a href="${escapeHtml(repositoryUrl(repository.name))}" target="_blank" rel="noreferrer">Abrir no GitHub <span aria-hidden="true">↗</span></a><button class="text-button" type="button" data-clear-repository-selection>Limpar seleção</button></div>`;
}

function renderRepositoryTable(tableRepositories, analysisRepositories) {
  const sorted = sortRows(tableRepositories, state.repositorySort, "stars");
  const selectedRepository = analysisRepositories.find((repository) => repository.name === state.selectedRepository);
  const displayed = sorted.slice(0, state.visibleRows);
  if (selectedRepository && !displayed.some((repository) => repository.name === selectedRepository.name)) displayed.unshift(selectedRepository);
  $("#repositories-table").innerHTML = displayed.length ? displayed.map((repository) => `<tr class="${repository.name === state.selectedRepository ? "is-selected" : ""}">
    <td><button class="repository-name-button" type="button" data-repository-detail="${escapeHtml(repository.name)}" aria-pressed="${repository.name === state.selectedRepository}">${escapeHtml(repository.name)}</button></td>
    <td><button class="lang-pill lang-pill-button" type="button" data-chart-action="language" data-chart-value="${escapeHtml(repository.language)}" aria-label="Filtrar por ${escapeHtml(repository.language)}">${escapeHtml(repository.language)}</button></td>
    <td>${compactFormatter.format(repository.stars)}</td>
    <td>${formatOptional(repository.pullRequests, compactFormatter)}</td>
    <td>${formatOptional(repository.releases)}</td>
    <td>${Number.isFinite(repository.closedIssuePercent) ? `${decimalFormatter.format(repository.closedIssuePercent)}%` : "—"}</td>
  </tr>`).join("") : `<tr><td colspan="6">Nenhum repositório encontrado com os filtros atuais.</td></tr>`;
  const showing = Math.min(displayed.length, sorted.length + (selectedRepository && !sorted.some((repository) => repository.name === selectedRepository.name) ? 1 : 0));
  const selectedNote = selectedRepository && !sorted.some((repository) => repository.name === selectedRepository.name) ? " Projeto selecionado mantido no topo." : "";
  $("#table-caption").textContent = sorted.length
    ? `Exibindo ${formatter.format(showing)} de ${formatter.format(sorted.length)} repositórios.${selectedNote}`
    : selectedRepository ? "Nenhum repositório corresponde aos filtros; projeto selecionado mantido no topo." : "Sem resultados para exibir.";
  const button = $("#show-more");
  button.hidden = sorted.length <= state.visibleRows;
  button.textContent = `Mostrar mais ${formatter.format(Math.min(12, Math.max(0, sorted.length - state.visibleRows)) || 12)}`;
  syncSortControls();
}

function renderExplorer(analysisRepositories = getAnalysisRepositories()) {
  const tableRepositories = getTableRepositories(analysisRepositories);
  const total = state.data.repositories.length;
  const tableIsFiltered = tableRepositories.length !== analysisRepositories.length;
  $("#result-count").textContent = tableIsFiltered
    ? `Análise: ${formatter.format(analysisRepositories.length)} de ${formatter.format(total)} · tabela: ${formatter.format(tableRepositories.length)}`
    : `Análise: ${formatter.format(analysisRepositories.length)} de ${formatter.format(total)} repositórios`;
  const tagRange = getTagRange();
  const chip = $("#tag-range-chip");
  chip.hidden = !tagRange;
  chip.innerHTML = tagRange ? `Tabela: tags ${escapeHtml(tagRange.label)} <span aria-hidden="true">×</span>` : "";
  const downloadButton = $("#download-results");
  downloadButton.disabled = tableRepositories.length === 0;
  downloadButton.setAttribute("aria-label", tableRepositories.length ? `Baixar ${formatter.format(tableRepositories.length)} resultados em CSV` : "Não há resultados para baixar");
  renderRepositorySpotlight(analysisRepositories);
  renderRepositoryTable(tableRepositories, analysisRepositories);
}

function syncLanguageMetricControls() {
  document.querySelectorAll("[data-language-metric]").forEach((button) => {
    const active = button.dataset.languageMetric === state.languageMetric;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function syncSortControls() {
  const sync = (selector, sort) => document.querySelectorAll(selector).forEach((button) => {
    const active = button.dataset[selector.includes("repository") ? "repositorySort" : "languageSort"] === sort.key;
    const direction = sort.direction === "asc" ? "crescente" : "decrescente";
    button.classList.toggle("is-active", active);
    button.querySelector("span").textContent = active ? (sort.direction === "asc" ? "↑" : "↓") : "↕";
    button.setAttribute("aria-label", `${button.textContent.replace(/[↑↓↕]/g, "").trim()}: ordenar ${active ? direction : ""}`.trim());
    const header = button.closest("th");
    if (header) header.setAttribute("aria-sort", active ? (sort.direction === "asc" ? "ascending" : "descending") : "none");
  });
  sync("[data-repository-sort]", state.repositorySort);
  sync("[data-language-sort]", state.languageStatsSort);
}

function renderDashboard() {
  const repositories = getAnalysisRepositories();
  setKpis(repositories);
  renderOverview(repositories);
  renderContributions(repositories);
  renderReleases(repositories);
  renderMaintenance(repositories);
  renderLanguageInsights();
  renderExplorer(repositories);
}

function populateLanguages() {
  const select = $("#language-filter");
  const languages = [...new Set(state.data.repositories.map((repository) => repository.language))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  select.innerHTML = `<option value="__all__">Todas as linguagens</option>${languages.map((language) => `<option value="${escapeHtml(language)}">${escapeHtml(language)}</option>`).join("")}`;
  select.value = state.language;
}

function announce(message) {
  $("#interaction-status").textContent = message;
}

function escapeCsvValue(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function downloadExplorerResults() {
  const repositories = getTableRepositories();
  if (!repositories.length) {
    announce("Não há resultados para baixar.");
    return;
  }
  const headers = ["Repositorio", "Linguagem primaria", "Criado em", "Estrelas", "PRs aceitas", "Tags", "Frequencia de issues", "Total de issues", "Issues fechadas", "Percentual de issues fechadas"];
  const rows = repositories.map((repository) => [
    repository.name,
    repository.language,
    repository.createdAt,
    repository.stars,
    Number.isFinite(repository.pullRequests) ? repository.pullRequests : "",
    Number.isFinite(repository.releases) ? repository.releases : "",
    repository.frequencyLabel,
    Number.isFinite(repository.totalIssues) ? repository.totalIssues : "",
    Number.isFinite(repository.closedIssues) ? repository.closedIssues : "",
    Number.isFinite(repository.closedIssuePercent) ? repository.closedIssuePercent : "",
  ]);
  const csv = `\uFEFF${[headers, ...rows].map((row) => row.map(escapeCsvValue).join(",")).join("\r\n")}`;
  const languagePart = state.language === "__all__" ? "todas-linguagens" : normalizeSearch(state.language).replace(/[^a-z0-9]+/g, "-");
  const filename = `resultados-repo-radar-${state.sample}-${languagePart}.csv`;
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  announce(`${formatter.format(repositories.length)} resultados baixados em CSV.`);
}

function getReducedMotionPreference() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

function focusActiveLanguageButton(language) {
  requestAnimationFrame(() => {
    const button = [...document.querySelectorAll("[data-chart-action='language']")].find((control) => control.dataset.chartValue === language);
    button?.focus();
  });
}

function setLanguageFilter(language, { toggle = false, restoreFocus = false } = {}) {
  const nextLanguage = toggle && state.language === language ? "__all__" : language;
  state.language = nextLanguage;
  state.visibleRows = 12;
  $("#language-filter").value = nextLanguage;
  renderDashboard();
  announce(nextLanguage === "__all__" ? "Filtro de linguagem removido." : `Filtro de linguagem aplicado: ${nextLanguage}.`);
  if (restoreFocus && nextLanguage !== "__all__") focusActiveLanguageButton(nextLanguage);
}

function setTableTagRange(rangeKey) {
  state.tableTagRange = state.tableTagRange === rangeKey ? null : rangeKey;
  state.visibleRows = 12;
  const analysisRepositories = getAnalysisRepositories();
  renderReleases(analysisRepositories);
  renderExplorer(analysisRepositories);
  const range = getTagRange();
  announce(range ? `Tabela filtrada por ${range.description}.` : "Filtro de tags removido da tabela.");
}

function selectRepository(name, scrollToTable = false) {
  state.selectedRepository = state.selectedRepository === name ? null : name;
  const analysisRepositories = getAnalysisRepositories();
  renderContributions(analysisRepositories);
  renderReleases(analysisRepositories);
  renderExplorer(analysisRepositories);
  const selected = state.selectedRepository;
  announce(selected ? `${selected} selecionado e destacado na tabela.` : "Seleção de repositório removida.");
  if (selected && scrollToTable) $("#repositorios").scrollIntoView({ behavior: getReducedMotionPreference() ? "auto" : "smooth", block: "start" });
}

function toggleSort(sortKey, key) {
  const current = state[sortKey];
  const defaultDirection = ["name", "language", "inactiveDays"].includes(key) ? "asc" : "desc";
  state[sortKey] = current.key === key
    ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
    : { key, direction: defaultDirection };
  const label = sortKey === "repositorySort" ? repositorySortLabel(key) : key === "repositories" ? "repositórios" : key === "pullRequests" ? "PRs" : key === "inactiveDays" ? "dias sem atualizar" : key;
  const directionLabel = state[sortKey].direction === "asc" ? "crescente" : "decrescente";
  announce(`Ordenado por ${label}, ${directionLabel}.`);
}

function setupTooltips() {
  const tooltip = $("#chart-tooltip");
  let activeTarget = null;
  let timer = null;
  let tooltipWasShown = false;

  const placeTooltip = (event, target) => {
    const rect = target.getBoundingClientRect();
    const preferredX = Number.isFinite(event?.clientX) ? event.clientX + 14 : rect.left + (rect.width / 2);
    const preferredY = Number.isFinite(event?.clientY) ? event.clientY + 18 : rect.top - 10;
    const left = Math.max(12, Math.min(preferredX, window.innerWidth - tooltip.offsetWidth - 12));
    const top = Math.max(12, Math.min(preferredY, window.innerHeight - tooltip.offsetHeight - 12));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  };

  const showTooltip = (target, event, delay = tooltipWasShown ? 0 : 150) => {
    clearTimeout(timer);
    activeTarget = target;
    timer = setTimeout(() => {
      if (activeTarget !== target) return;
      tooltip.textContent = target.dataset.tooltip;
      tooltip.classList.toggle("is-instant", tooltipWasShown);
      tooltip.classList.add("is-visible");
      tooltip.setAttribute("aria-hidden", "false");
      placeTooltip(event, target);
      tooltipWasShown = true;
    }, delay);
  };

  const hideTooltip = () => {
    clearTimeout(timer);
    activeTarget = null;
    tooltip.classList.remove("is-visible");
    tooltip.setAttribute("aria-hidden", "true");
  };

  document.addEventListener("pointerover", (event) => {
    const target = event.target.closest?.("[data-tooltip]");
    if (!target || target === activeTarget || target.contains(event.relatedTarget)) return;
    showTooltip(target, event);
  });
  document.addEventListener("pointermove", (event) => {
    if (activeTarget && tooltip.classList.contains("is-visible")) placeTooltip(event, activeTarget);
  });
  document.addEventListener("pointerout", (event) => {
    const target = event.target.closest?.("[data-tooltip]");
    if (target && target === activeTarget && !target.contains(event.relatedTarget)) hideTooltip();
  });
  document.addEventListener("focusin", (event) => {
    const target = event.target.closest?.("[data-tooltip]");
    if (target) showTooltip(target, null, 0);
  });
  document.addEventListener("focusout", (event) => {
    const target = event.target.closest?.("[data-tooltip]");
    if (target && target === activeTarget && !target.contains(event.relatedTarget)) hideTooltip();
  });
}

async function refreshDataset() {
  const loadState = $("#load-state");
  const content = $("#dashboard-content");
  loadState.className = "load-state";
  loadState.innerHTML = `<div class="loading-orbit" aria-hidden="true"></div><p>Preparando a leitura dos CSVs…</p>`;
  loadState.hidden = false;
  content.hidden = true;
  content.setAttribute("aria-busy", "true");
  try {
    state.data = await loadDataset(state.sample);
    state.language = "__all__";
    state.search = "";
    state.visibleRows = 12;
    state.tableTagRange = null;
    state.selectedRepository = null;
    state.showSmallLanguageGroups = false;
    $("#repository-search").value = "";
    populateLanguages();
    renderDashboard();
    const label = DATASETS[state.sample].label;
    $("#source-status").textContent = `${label} disponíveis para exploração`;
    $(".status-dot").classList.add("is-ready");
    $("#data-badge span").textContent = `${label} carregados localmente`;
    loadState.hidden = true;
    content.hidden = false;
    content.setAttribute("aria-busy", "false");
    announce(`${label} carregados. Dashboard pronta para exploração.`);
  } catch (error) {
    loadState.className = "load-state is-error";
    loadState.innerHTML = `<strong>Não foi possível carregar os dados.</strong><p>${escapeHtml(error.message)}</p><p>Abra a dashboard por um servidor local, conforme o README desta pasta.</p>`;
    content.setAttribute("aria-busy", "false");
    console.error(error);
  }
}

function setupNavigation() {
  const navLinks = [...document.querySelectorAll(".nav-link")];
  const sections = [...document.querySelectorAll("[data-section]")];
  if (!("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver((entries) => {
    const active = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!active) return;
    navLinks.forEach((link) => {
      const isActive = link.dataset.target === active.target.id;
      link.classList.toggle("is-active", isActive);
      if (isActive) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }, { rootMargin: "-20% 0px -63% 0px", threshold: [0, .15, .4] });
  sections.forEach((section) => observer.observe(section));
}

function setupEvents() {
  let searchAnnouncementTimer;
  $("#sample-select").addEventListener("change", (event) => {
    state.sample = event.target.value;
    refreshDataset();
  });
  $("#language-filter").addEventListener("change", (event) => {
    setLanguageFilter(event.target.value);
  });
  $("#repository-search").addEventListener("input", (event) => {
    state.search = event.target.value;
    state.visibleRows = 12;
    renderExplorer();
    clearTimeout(searchAnnouncementTimer);
    searchAnnouncementTimer = setTimeout(() => announce(`Tabela atualizada: ${formatter.format(getTableRepositories().length)} repositórios encontrados.`), 200);
  });
  $("#reset-filters").addEventListener("click", () => {
    state.language = "__all__";
    state.search = "";
    state.visibleRows = 12;
    state.tableTagRange = null;
    state.selectedRepository = null;
    $("#language-filter").value = "__all__";
    $("#repository-search").value = "";
    renderDashboard();
    announce("Todos os filtros foram removidos.");
  });
  $("#tag-range-chip").addEventListener("click", () => setTableTagRange(state.tableTagRange));
  $("#download-results").addEventListener("click", downloadExplorerResults);
  $("#show-more").addEventListener("click", () => {
    const previousCount = Math.min(state.visibleRows, getTableRepositories().length);
    state.visibleRows += 12;
    renderExplorer();
    const currentCount = Math.min(state.visibleRows, getTableRepositories().length);
    announce(`${formatter.format(Math.max(0, currentCount - previousCount))} repositórios adicionados à tabela.`);
  });
  $("#toggle-small-languages").addEventListener("click", () => {
    state.showSmallLanguageGroups = !state.showSmallLanguageGroups;
    renderLanguageInsights();
    announce(state.showSmallLanguageGroups ? "Grupos de linguagem menores incluídos." : "Grupos de linguagem menores ocultados.");
  });
  document.querySelectorAll("[data-language-metric]").forEach((button) => button.addEventListener("click", () => {
    state.languageMetric = button.dataset.languageMetric;
    renderLanguageInsights();
    announce(`Métrica de linguagens alterada para ${LANGUAGE_METRICS[state.languageMetric].label}.`);
  }));
  document.querySelectorAll("[data-repository-sort]").forEach((button) => button.addEventListener("click", () => {
    toggleSort("repositorySort", button.dataset.repositorySort);
    renderExplorer();
  }));
  document.querySelectorAll("[data-language-sort]").forEach((button) => button.addEventListener("click", () => {
    toggleSort("languageStatsSort", button.dataset.languageSort);
    renderLanguageInsights();
  }));
  document.addEventListener("click", (event) => {
    const chartAction = event.target.closest?.("[data-chart-action]");
    if (chartAction) {
      if (chartAction.dataset.chartAction === "language") setLanguageFilter(chartAction.dataset.chartValue, { toggle: true, restoreFocus: true });
      if (chartAction.dataset.chartAction === "repository") selectRepository(chartAction.dataset.chartValue, true);
      if (chartAction.dataset.chartAction === "table-tag-range") setTableTagRange(chartAction.dataset.chartValue);
      return;
    }
    const repositoryControl = event.target.closest?.("[data-repository-detail]");
    if (repositoryControl) {
      selectRepository(repositoryControl.dataset.repositoryDetail);
      return;
    }
    if (event.target.closest?.("[data-clear-repository-selection]")) {
      state.selectedRepository = null;
      renderExplorer();
      announce("Seleção de repositório removida.");
    }
  });
}

setupEvents();
setupNavigation();
setupTooltips();
refreshDataset();
