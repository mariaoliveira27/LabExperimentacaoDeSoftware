"use strict";

const state = { manifest: null, participant: "all", kata: "all" };
const $ = (selector) => document.querySelector(selector);
const decimal = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const chartLabels = {
  tempo: "Distribuição do tempo registrado em minutos, por tratamento",
  sucesso: "Taxa de sucesso nos testes em percentual, por kata e tratamento",
  complexidade: "Distribuição da complexidade ciclomática média por solução e tratamento",
  loc: "Distribuição das linhas de código por tratamento",
  relacao: "Relação entre o tamanho em linhas de código (LOC) e a complexidade ciclomática média das soluções",
};
const kpis = [
  { key: "tempo", label: "Tempo registrado", kind: "Mediana · minutos", statistic: "median", unit: "min", foot: "Mediana dos tempos das rodadas." },
  { key: "sucesso", label: "Sucesso nos testes", kind: "Média das taxas por rodada", statistic: "mean", unit: "%", foot: "Cada rodada tem o mesmo peso na média." },
  { key: "complexidade", label: "Complexidade", kind: "Mediana da CC média", statistic: "median", unit: "", foot: "Complexidade ciclomática média por solução." },
  { key: "loc", label: "Linhas de código", kind: "Mediana · LOC", statistic: "median", unit: "linhas", foot: "Inclui comentários e linhas em branco." },
];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
}

function isNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function format(value, whole = false) {
  return isNumber(value) ? (whole ? integer : decimal).format(value) : "Não disponível";
}

function labelFor(items, value) {
  return items.find((item) => item.value === value)?.label || value;
}

function assetPath(value) {
  if (typeof value !== "string" || !value || value.includes("\\") || value.startsWith("/") || /^[a-z][a-z\d+.-]*:/i.test(value) || value.split("/").includes("..")) {
    throw new Error("O manifesto contém um caminho de arquivo inválido.");
  }
  return `./${value.replace(/^\.\//, "")}`;
}

function validateManifest(data) {
  if (data?.schema_version !== 1 || !Array.isArray(data.rows) || !Array.isArray(data.participants) || !Array.isArray(data.katas) || !Array.isArray(data.treatments) || !data.views?.all__all) {
    throw new Error("O arquivo de dados não corresponde ao formato esperado pela dashboard.");
  }
  const rowIds = new Set(data.rows.map((row) => row.trial_id));
  if (rowIds.size !== data.rows.length) throw new Error("Foram encontradas rodadas duplicadas no arquivo de dados.");
  for (const participant of data.participants) {
    for (const kata of data.katas) {
      const view = data.views[`${participant.value}__${kata.value}`];
      if (!view || !Array.isArray(view.row_ids) || !view.counts || !view.stats || !view.charts || view.row_ids.some((id) => !rowIds.has(id))) {
        throw new Error("Um dos recortes do experimento não está disponível no arquivo de dados.");
      }
      assetPath(view.csv);
      for (const key of Object.keys(chartLabels)) {
        assetPath(view.charts[key]?.svg);
        assetPath(view.charts[key]?.png);
        assetPath(view.charts[key]?.display);
        assetPath(view.charts[key]?.mobile);
      }
    }
  }
}

function currentView() {
  return state.manifest.views[`${state.participant}__${state.kata}`];
}

function configureFilters() {
  const parameters = new URLSearchParams(window.location.search);
  const participant = parameters.get("integrante") || "all";
  const kata = parameters.get("kata") || "all";
  state.participant = state.manifest.participants.some((item) => item.value === participant) ? participant : "all";
  state.kata = state.manifest.katas.some((item) => item.value === kata) ? kata : "all";
  for (const [selector, items, selected] of [
    ["#participant-filter", state.manifest.participants, state.participant],
    ["#kata-filter", state.manifest.katas, state.kata],
  ]) {
    const select = $(selector);
    select.replaceChildren(...items.map((item) => {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      return option;
    }));
    select.value = selected;
  }
}

function updateUrl() {
  const url = new URL(window.location.href);
  for (const [key, value] of [["integrante", state.participant], ["kata", state.kata]]) {
    if (value === "all") url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  }
  window.history.replaceState(null, "", url);
}

function renderKpis(view) {
  $("#kpi-grid").innerHTML = kpis.map((metric) => {
    const values = state.manifest.treatments.map((treatment) => {
      const stats = view.stats[treatment.value]?.[metric.key];
      const value = stats?.[metric.statistic];
      const valid = (stats?.n || 0) > 0 && isNumber(value);
      const sample = `${format(stats?.n ?? 0, true)} ${stats?.n === 1 ? "observação" : "observações"}`;
      const detail = !valid ? "" : metric.key === "sucesso"
        ? `${format(stats.complete, true)}/${format(stats.n, true)} rodadas com 100%`
        : `Q1–Q3: ${format(stats.q1)}–${format(stats.q3)}`;
      return `<div><span class="kpi-treatment"><span class="treatment-dot ${escapeHtml(treatment.value)}" aria-hidden="true"></span>${escapeHtml(treatment.label)}</span><strong class="kpi-value ${escapeHtml(treatment.value)}${valid ? "" : " is-missing"}">${valid ? `${format(value)}${metric.unit ? `<small>${metric.unit}</small>` : ""}` : "Sem observações"}</strong><span class="kpi-n">${sample}</span><span class="kpi-detail">${detail}</span></div>`;
    }).join("");
    return `<article class="kpi-card"><h3 class="kpi-label">${metric.label}</h3><span class="kpi-kind">${metric.kind}</span><div class="kpi-values">${values}</div><p class="kpi-foot">${metric.foot}</p></article>`;
  }).join("");
}

function renderCharts(view, context) {
  for (const [key, label] of Object.entries(chartLabels)) {
    const image = $(`#chart-${key}`);
    const frame = image.closest(".chart-frame");
    frame.querySelector(".chart-error")?.remove();
    image.hidden = false;
    image.alt = `${label}. Recorte: ${context}. Manual: ${view.counts.manual} rodadas; Com IA: ${view.counts.ia} rodadas. Os valores individuais estão na tabela de rodadas.`;
    image.previousElementSibling.srcset = assetPath(view.charts[key].mobile);
    image.src = assetPath(view.charts[key].display);
    for (const link of document.querySelectorAll(`[data-download="${key}"]`)) {
      const extension = link.dataset.format;
      link.href = assetPath(view.charts[key][extension]);
      link.download = `lab02-${key}-${state.participant}-${state.kata}.${extension}`;
      link.setAttribute("aria-label", `Baixar gráfico ${label.toLocaleLowerCase("pt-BR")} em ${extension.toUpperCase()}`);
    }
  }
}

function configureChartControls() {
  for (const [key, label] of Object.entries(chartLabels)) {
    const image = $(`#chart-${key}`);
    const picture = document.createElement("picture");
    const source = document.createElement("source");
    source.media = ["loc", "complexidade"].includes(key) ? "(min-width: 0px)" : "(max-width: 660px)";
    image.before(picture);
    picture.append(source, image);
    image.removeAttribute("width");
    image.removeAttribute("height");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "expand-chart";
    button.dataset.expand = key;
    button.textContent = "Ampliar ↗";
    button.setAttribute("aria-label", `Ampliar gráfico: ${label.toLocaleLowerCase("pt-BR")}`);
    button.setAttribute("aria-haspopup", "dialog");
    button.addEventListener("click", () => {
      $("#chart-dialog-title").textContent = image.closest(".chart-panel").querySelector("h3").textContent;
      const expanded = $("#expanded-chart");
      expanded.src = assetPath(currentView().charts[key].svg);
      expanded.alt = image.alt;
      expanded.hidden = false;
      $("#expanded-error").hidden = true;
      $("#chart-dialog").showModal();
      document.body.classList.add("dialog-open");
    });
    image.closest(".chart-panel").querySelector(".chart-downloads").prepend(button);
  }
  const dialog = $("#chart-dialog");
  $("#close-chart-dialog").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => document.body.classList.remove("dialog-open"));
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  $("#expanded-chart").addEventListener("error", () => {
    $("#expanded-chart").hidden = true;
    $("#expanded-error").hidden = false;
  });
}

function numberCell(value, whole = false) {
  return isNumber(value) ? format(value, whole) : '<span class="missing-value">Não disponível</span>';
}

function renderRows(view) {
  const rowMap = new Map(state.manifest.rows.map((row) => [row.trial_id, row]));
  const rows = view.row_ids.map((id) => rowMap.get(id));
  $("#trials-table").innerHTML = rows.length ? rows.map((row) => {
    const participant = labelFor(state.manifest.participants, row.integrante);
    const treatment = labelFor(state.manifest.treatments, row.tratamento);
    const report = row.fonte_testes === "relatorio";
    const hasCounts = isNumber(row.aprovados) && isNumber(row.total_testes);
    const evidence = hasCounts ? `${format(row.aprovados, true)}/${format(row.total_testes, true)} testes aprovados` : "Contagens não disponíveis";
    const recorded = row.status_registrado ? `Registro: ${escapeHtml(row.status_registrado)}` : "Status não registrado";
    return `<tr><td><span class="participant-name">${escapeHtml(participant)}</span><span class="trial-id">${escapeHtml(row.trial_id)}</span></td><td>${escapeHtml(row.kata)}</td><td><span class="treatment-tag ${escapeHtml(row.tratamento)}"><span class="treatment-dot ${escapeHtml(row.tratamento)}" aria-hidden="true"></span>${escapeHtml(treatment)}</span></td><td class="numeric">${numberCell(row.tempo_min)}${row.tempo_censurado ? '<span class="censored-label">Censurado</span>' : ""}</td><td class="numeric">${numberCell(row.taxa_sucesso)}</td><td class="numeric">${numberCell(row.complexidade_media)}</td><td class="numeric">${numberCell(row.loc, true)}</td><td class="numeric">${numberCell(row.sloc, true)}</td><td class="evidence-cell"><span class="evidence-main">${evidence}</span><span class="evidence-source">${report ? "Relatório de testes arquivado" : "Taxa informada no CSV"}</span><span class="evidence-status${row.status_divergente ? " is-divergent" : ""}">${recorded}${row.status_divergente ? '<span class="evidence-flag" title="O status registrado no CSV difere do resultado dos testes arquivados.">Divergente</span>' : ""}</span></td></tr>`;
  }).join("") : '<tr><td colspan="9">Não há rodadas neste recorte.</td></tr>';
  const counts = view.counts;
  $("#table-summary").textContent = `${format(counts.total, true)} ${counts.total === 1 ? "rodada selecionada" : "rodadas selecionadas"} · dados do mesmo recorte dos gráficos`;
  $("#evidence-summary").textContent = `${format(counts.testes_arquivados, true)}/${format(counts.total, true)} com relatório de testes · ${format(counts.metricas_arquivadas, true)}/${format(counts.total, true)} com métricas · ${format(counts.divergencias, true)} ${counts.divergencias === 1 ? "status divergente" : "status divergentes"}`;
}

function render() {
  const view = currentView();
  const participant = labelFor(state.manifest.participants, state.participant);
  const kata = labelFor(state.manifest.katas, state.kata);
  const context = `${state.participant === "all" ? "todos os participantes" : participant}; ${state.kata === "all" ? "todas as katas" : kata}`;
  const counts = view.counts;
  $("#filter-summary").innerHTML = `<strong>${format(counts.total, true)} ${counts.total === 1 ? "rodada" : "rodadas"}</strong> neste recorte · ${format(counts.manual, true)} Manual · ${format(counts.ia, true)} Com IA <span aria-hidden="true">—</span> ${escapeHtml(context)}`;
  const adjustmentNote = $("#adjustment-note");
  adjustmentNote.hidden = !view.adjustment_count;
  adjustmentNote.textContent = "Os rótulos Manual/IA das rodadas de Áulus foram invertidos conforme solicitado. Os CSVs preservam também o tratamento originalmente registrado.";
  $("#reset-filters").disabled = state.participant === "all" && state.kata === "all";
  const csv = $("#download-csv");
  csv.href = assetPath(view.csv);
  csv.download = `lab02-rodadas-${state.participant}-${state.kata}.csv`;
  const fallback = counts.total - counts.testes_arquivados;
  $("#test-source-note").textContent = fallback > 0
    ? `${format(fallback, true)} ${fallback === 1 ? "rodada usa a taxa de sucesso do CSV, sem relatório de testes arquivado" : "rodadas usam a taxa de sucesso do CSV, sem relatório de testes arquivado"} neste recorte.`
    : "Todas as rodadas deste recorte têm relatório de testes arquivado.";
  const note = $("#comparison-note");
  const missingTreatment = counts.manual === 0 || counts.ia === 0;
  note.hidden = !missingTreatment;
  if (missingTreatment) note.textContent = counts.total === 0
    ? "Não há observações neste recorte. Altere os filtros para consultar outras rodadas."
    : `Este recorte contém apenas ${counts.manual ? "o tratamento Manual" : "o tratamento Com IA"}. Não há observações do outro tratamento para comparar; valores ausentes não representam zero.`;
  renderKpis(view);
  renderCharts(view, context);
  renderRows(view);
}

async function loadDashboard() {
  const loadState = $("#load-state");
  loadState.hidden = false;
  loadState.classList.remove("is-error");
  loadState.querySelector("h1").textContent = "Preparando a dashboard";
  loadState.querySelector("p").textContent = "Carregando os resultados e as visualizações do experimento.";
  $("#retry-load").hidden = true;
  $("#dashboard-content").hidden = true;
  $("#source-dot").classList.remove("is-ready");
  $("#source-status").textContent = "Preparando os resultados…";
  try {
    const response = await fetch("./data/manifest.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`Não foi possível abrir os dados (${response.status}).`);
    const manifest = await response.json();
    validateManifest(manifest);
    state.manifest = manifest;
    configureFilters();
    render();
    $("#total-trials").textContent = format(manifest.views.all__all.counts.total, true);
    $("#study-dimensions").textContent = `${manifest.participants.length - 1} participantes · ${manifest.katas.length - 1} katas`;
    const generated = new Date(manifest.generated_at);
    $("#generated-label").textContent = Number.isNaN(generated.getTime()) ? "" : `Dados preparados em ${new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(generated)}`;
    $("#source-status").textContent = "Dados do Lab 02 · gráficos gerados com Python";
    $("#source-dot").classList.add("is-ready");
    loadState.hidden = true;
    $("#dashboard-content").hidden = false;
    updateUrl();
    if (window.location.hash) document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ behavior: "instant" });
  } catch (error) {
    loadState.classList.add("is-error");
    loadState.querySelector("h1").textContent = "Não foi possível carregar os resultados";
    loadState.querySelector("p").textContent = window.location.protocol === "file:"
      ? "Abra esta dashboard por um servidor local ou pelo endereço publicado. O navegador bloqueia a leitura dos dados quando o HTML é aberto diretamente como arquivo."
      : `${error.message || "O arquivo de dados não está acessível."} Tente carregar novamente.`;
    $("#retry-load").hidden = false;
    $("#source-status").textContent = "Dados indisponíveis";
  }
}

$("#participant-filter").addEventListener("change", (event) => {
  state.participant = event.target.value;
  render();
  updateUrl();
});
$("#kata-filter").addEventListener("change", (event) => {
  state.kata = event.target.value;
  render();
  updateUrl();
});
$("#reset-filters").addEventListener("click", () => {
  state.participant = "all";
  state.kata = "all";
  $("#participant-filter").value = "all";
  $("#kata-filter").value = "all";
  render();
  updateUrl();
});
$("#retry-load").addEventListener("click", loadDashboard);
for (const image of document.querySelectorAll(".chart-image")) {
  image.addEventListener("error", () => {
    image.hidden = true;
    const frame = image.closest(".chart-frame");
    if (frame.querySelector(".chart-error")) return;
    const message = document.createElement("p");
    message.className = "chart-error";
    message.setAttribute("role", "status");
    message.textContent = "Não foi possível abrir este gráfico. Os valores continuam disponíveis na tabela e no CSV do recorte. Recarregue a página para tentar novamente.";
    frame.append(message);
  });
}
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    for (const link of document.querySelectorAll(".nav-link")) {
      const active = link.hash === `#${visible.target.id}`;
      link.classList.toggle("is-active", active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }, { rootMargin: "-8% 0px -55% 0px", threshold: [0, .2, .5, 1] });
  for (const section of document.querySelectorAll("[data-section]")) observer.observe(section);
}
configureChartControls();
loadDashboard();
