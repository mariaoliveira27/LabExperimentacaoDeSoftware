/**
 * Dashboard do Laboratório 04 (Lab04S01)
 * Lógica do cliente: carregamento de dados analíticos,
 * renderização interativa dos Gráficos G1 e G2 e filtros reativos.
 */

(function () {
  "use strict";

  // Estado da aplicação
  const state = {
    dados: null,
    erroCarregamentoDados: null,
    metricaAtual: "lead_time_commit_mediana_dias",
    distribuicaoAtual: "Lognormal",
    testeAtual: "t-Student",
    alphaAtual: "0.05",
    modoG1: "Lado a Lado", // "Lado a Lado" ou "Sobreposto"
    cenarioG4: "lognormal_base",
  };

  // Elementos do DOM
  const dom = {
    sourceStatus: document.getElementById("source-status"),
    sourceDot: document.getElementById("source-dot"),
    selectMetrica: document.getElementById("select-metrica"),
    selectDistribuicao: document.getElementById("select-distribuicao"),
    selectTeste: document.getElementById("select-teste"),
    selectAlpha: document.getElementById("select-alpha"),
    btnG1Side: document.getElementById("btn-g1-side"),
    btnG1Over: document.getElementById("btn-g1-over"),
    chartG1: document.getElementById("chart-g1-container"),
    chartG2: document.getElementById("chart-g2-container"),
    chartG3: document.getElementById("chart-g3-container"),
    chartG4: document.getElementById("chart-g4-container"),
    g1Title: document.getElementById("g1-title"),
    g2Title: document.getElementById("g2-title"),
    g3Title: document.getElementById("g3-title"),
    g4Title: document.getElementById("g4-title"),
    selectCenarioG4: document.getElementById("select-cenario-g4"),
    g1StatsBody: document.getElementById("g1-stats-body"),
    g2ConclusionBox: document.getElementById("g2-conclusion-box"),
    g3ConclusionBox: document.getElementById("g3-conclusion-box"),
    g4ConclusionBox: document.getElementById("g4-conclusion-box"),
    g2StatusPill: document.getElementById("g2-status-pill"),
    kpiNReais: document.getElementById("kpi-n-reais"),
    kpiMedia: document.getElementById("kpi-media"),
    kpiStat: document.getElementById("kpi-stat"),
    kpiDecisao: document.getElementById("kpi-decisao"),
    kpiDecisaoFoot: document.getElementById("kpi-decisao-foot"),
    inputBuscaRepo: document.getElementById("input-busca-repo"),
    tabelaReposBody: document.getElementById("tabela-repos-body"),
    tabelaDadosReaisBody: document.getElementById("tabela-dados-reais-body"),
  };

  // Inicialização
  document.addEventListener("DOMContentLoaded", () => {
    configurarEventos();
    carregarDados();
  });

  function configurarEventos() {
    dom.selectMetrica.addEventListener("change", (e) => {
      state.metricaAtual = e.target.value;
      atualizarVisualizacoes();
    });

    dom.selectDistribuicao.addEventListener("change", (e) => {
      state.distribuicaoAtual = e.target.value;
      atualizarVisualizacoes();
    });

    dom.selectTeste.addEventListener("change", (e) => {
      state.testeAtual = e.target.value;
      atualizarVisualizacoes();
    });

    dom.selectAlpha.addEventListener("change", (e) => {
      state.alphaAtual = e.target.value;
      atualizarVisualizacoes();
    });

    dom.btnG1Side.addEventListener("click", () => {
      state.modoG1 = "Lado a Lado";
      dom.btnG1Side.classList.add("active");
      dom.btnG1Over.classList.remove("active");
      renderizarG1();
    });

    dom.btnG1Over.addEventListener("click", () => {
      state.modoG1 = "Sobreposto";
      dom.btnG1Over.classList.add("active");
      dom.btnG1Side.classList.remove("active");
      renderizarG1();
    });

    if (dom.inputBuscaRepo) {
      dom.inputBuscaRepo.addEventListener("input", (e) => {
        filtrarTabelaRepositorios(e.target.value.toLowerCase());
      });
    }

    if (dom.selectCenarioG4) {
      dom.selectCenarioG4.addEventListener("change", (e) => {
        state.cenarioG4 = e.target.value;
        renderizarG4();
      });
    }
  }

  async function carregarDados() {
    try {
      const response = await fetch(`data/dados.json?v=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Falha ao carregar data/dados.json");
      state.dados = await response.json();
      finalizarCarregamento();
    } catch (err) {
      state.erroCarregamentoDados = err?.message || "Não foi possível carregar data/dados.json";
      console.warn("Falha ao carregar data/dados.json. Abra o dashboard pelo servidor HTTP local:", err);
      state.dados = gerarDadosEmbutidosFallback();
      finalizarCarregamento();
    }
  }

  function finalizarCarregamento() {
    if (dom.sourceStatus) dom.sourceStatus.textContent = state.erroCarregamentoDados
      ? "JSON não carregado; exibindo modo de contingência"
      : "Dados consolidados (Entrega Final)";
    if (dom.sourceDot) dom.sourceDot.classList.add("is-ready");

    preencherSelectMetricas();
    const textos = state.dados.textos_dashboard || {};
    ["secao_1_cenario", "secao_6_dados_reais", "secao_7_conclusao"].forEach((chave, i) => {
      const elemento = document.getElementById(`texto-secao-${[1, 6, 7][i]}`);
      if (elemento && textos[chave]) elemento.textContent = textos[chave];
    });
    if (dom.kpiNReais) dom.kpiNReais.textContent = state.dados.metadados_coleta?.n_observacoes_csv ?? state.dados.dados_reais_testes?.n_total ?? "—";
    renderizarTabelaDadosReais();
    renderizarTabelaRepositorios(state.dados.repositorios || []);
    atualizarVisualizacoes();
    configurarScrollObserver();
  }

  function preencherSelectMetricas() {
    dom.selectMetrica.innerHTML = "";
    const metricas = state.dados.metricas || Object.keys(state.dados.views);
    metricas.forEach((m) => {
      const meta = state.dados.views[m]?.meta;
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = meta?.nome || m;
      dom.selectMetrica.appendChild(opt);
    });

    if (metricas.includes(state.metricaAtual)) {
      dom.selectMetrica.value = state.metricaAtual;
    } else if (metricas.length > 0) {
      state.metricaAtual = metricas[0];
      dom.selectMetrica.value = state.metricaAtual;
    }
  }

  function atualizarVisualizacoes() {
    if (!state.dados) return;
    renderizarG1();
    renderizarG2();
    renderizarG3();
    renderizarG4();
    atualizarKPIs();
  }

  // -------------------------------------------------------------------------
  // RENDERIZAÇÃO DO GRÁFICO G1 (Histogramas Comparativos)
  // -------------------------------------------------------------------------
  function renderizarG1() {
    const view = state.dados.views[state.metricaAtual];
    if (!view) return;

    const distData = view.distribuicoes[state.distribuicaoAtual];
    if (!distData || !distData.g1) return;

    const g1 = distData.g1;
    const nomeMetrica = view.meta?.nome || state.metricaAtual;

    dom.g1Title.textContent = `Histograma Comparativo: Dados Reais vs. Simulados (${state.distribuicaoAtual})`;

    // Atualiza a tabela descritiva abaixo do gráfico
    dom.g1StatsBody.innerHTML = `
      <tr>
        <td><strong style="color:#1677c8;">● Dados Reais</strong></td>
        <td>${g1.stats_real.n}</td>
        <td><strong>${g1.stats_real.media}</strong></td>
        <td>${g1.stats_real.mediana}</td>
        <td>${g1.stats_real.dp}</td>
        <td>${g1.stats_real.skew}</td>
      </tr>
      <tr>
        <td><strong style="color:#ec9b24;">● Dados Simulados (${state.distribuicaoAtual})</strong></td>
        <td>${g1.stats_sim.n}</td>
        <td><strong>${g1.stats_sim.media}</strong></td>
        <td>${g1.stats_sim.mediana}</td>
        <td>${g1.stats_sim.dp}</td>
        <td>${g1.stats_sim.skew}</td>
      </tr>
    `;

    // Renderização com Plotly.js
    if (typeof Plotly === "undefined") {
      dom.chartG1.innerHTML = `<p style="padding:20px; color:#e36b57;">Plotly.js indisponível. Visualize as estatísticas descritivas na tabela acima.</p>`;
      return;
    }

    // Limpa qualquer mensagem ou loader residual antes de renderizar
    dom.chartG1.innerHTML = "";

    const corReal = "#1677c8";
    const corSim = "#ec9b24";

    if (state.modoG1 === "Lado a Lado") {
      const traceReal = {
        x: g1.valores_reais,
        type: "histogram",
        name: `Dados Reais (N=${g1.stats_real.n})`,
        histnorm: "probability density",
        marker: { color: corReal, line: { color: "#075b9a", width: 1 } },
        opacity: 0.85,
        xaxis: "x",
        yaxis: "y",
      };

      const traceSim = {
        x: g1.valores_simulados,
        type: "histogram",
        name: `Simulado (N=${g1.stats_sim.n})`,
        histnorm: "probability density",
        marker: { color: corSim, line: { color: "#c97f14", width: 1 } },
        opacity: 0.85,
        xaxis: "x2",
        yaxis: "y2",
      };

      const layout = {
        grid: { rows: 1, columns: 2, pattern: "independent" },
        title: {
          text: `<b>G1: Distribuição Real vs. Simulada</b> — ${nomeMetrica}`,
          font: { size: 14, color: "#102a43" },
          x: 0.5,
          xanchor: "center",
          y: 0.97,
        },
        xaxis: { title: `${nomeMetrica} (Real)` },
        xaxis2: { title: `${nomeMetrica} (Simulado)` },
        yaxis: { title: "Densidade de Probabilidade" },
        yaxis2: { title: "Densidade de Probabilidade" },
        showlegend: true,
        legend: { orientation: "h", y: -0.22, x: 0.5, xanchor: "center", font: { size: 11.5 } },
        margin: { t: 55, b: 75, l: 60, r: 40 },
        height: 420,
        shapes: [
          // Linha de média real
          { type: "line", x0: g1.stats_real.media, x1: g1.stats_real.media, y0: 0, y1: 1, yref: "y domain", xref: "x", line: { color: "#075b9a", width: 2, dash: "dash" } },
          // Linha de média simulada
          { type: "line", x0: g1.stats_sim.media, x1: g1.stats_sim.media, y0: 0, y1: 1, yref: "y2 domain", xref: "x2", line: { color: "#c97f14", width: 2, dash: "dash" } },
        ],
      };

      Plotly.newPlot(dom.chartG1, [traceReal, traceSim], layout, { responsive: true, displayModeBar: false });
    } else {
      // Modo Sobreposto
      const traceReal = {
        x: g1.valores_reais,
        type: "histogram",
        name: `Dados Reais (N=${g1.stats_real.n})`,
        histnorm: "probability density",
        marker: { color: corReal },
        opacity: 0.6,
      };

      const traceSim = {
        x: g1.valores_simulados,
        type: "histogram",
        name: `Simulado (N=${g1.stats_sim.n})`,
        histnorm: "probability density",
        marker: { color: corSim },
        opacity: 0.6,
      };

      const layout = {
        barmode: "overlay",
        title: {
          text: `<b>G1: Histogramas Sobrepostos</b> — ${nomeMetrica}`,
          font: { size: 14, color: "#102a43" },
          x: 0.5,
          xanchor: "center",
          y: 0.97,
        },
        xaxis: { title: nomeMetrica },
        yaxis: { title: "Densidade de Probabilidade" },
        showlegend: true,
        legend: { orientation: "h", y: -0.22, x: 0.5, xanchor: "center", font: { size: 11.5 } },
        margin: { t: 55, b: 75, l: 60, r: 40 },
        height: 420,
        shapes: [
          { type: "line", x0: g1.stats_real.media, x1: g1.stats_real.media, y0: 0, y1: 1, yref: "paper", line: { color: corReal, width: 2, dash: "dash" } },
          { type: "line", x0: g1.stats_sim.media, x1: g1.stats_sim.media, y0: 0, y1: 1, yref: "paper", line: { color: corSim, width: 2, dash: "dash" } },
        ],
      };

      Plotly.newPlot(dom.chartG1, [traceReal, traceSim], layout, { responsive: true, displayModeBar: false });
    }
  }

  // -------------------------------------------------------------------------
  // RENDERIZAÇÃO DO GRÁFICO G2 (Distribuição sob H0 & Região Crítica)
  // -------------------------------------------------------------------------
  function renderizarG2() {
    const view = state.dados.views[state.metricaAtual];
    if (!view) return;

    const testeData = view.testes[state.testeAtual];
    if (!testeData) return;

    const g2 = testeData.alphas[state.alphaAtual];
    if (!g2) return;

    dom.g2Title.textContent = `${g2.titulo_distribuicao} — Região de Rejeição (α = ${state.alphaAtual})`;

    // Atualiza status pill e caixa de conclusão
    const rejeita = g2.rejeita_h0;
    if (rejeita) {
      dom.g2StatusPill.className = "badge-decision reject";
      dom.g2StatusPill.textContent = "Rejeita H₀";
      dom.g2ConclusionBox.className = "callout-box danger";
      dom.g2ConclusionBox.innerHTML = `
        <strong>🛑 Veredito Estatístico: Rejeita-se a Hipótese Nula (H₀) ao nível de significância de α = ${state.alphaAtual}.</strong><br>
        O p-valor obtido (<strong>${g2.p_valor.toExponential(4)}</strong>) é estritamente menor que α, e a estatística observada (${g2.nome_stat}<sub>obs</sub> = <strong>${g2.stat_obs}</strong>) encontra-se na <strong>região crítica de rejeição</strong> (|${g2.nome_stat}| ≥ ${g2.valor_critico}). Há evidência empírica conclusiva de diferença significativa no cenário analisado (<em>${testeData.cenario}</em>).
      `;
    } else {
      dom.g2StatusPill.className = "badge-decision no-reject";
      dom.g2StatusPill.textContent = "Não Rejeita H₀";
      dom.g2ConclusionBox.className = "callout-box success";
      dom.g2ConclusionBox.innerHTML = `
        <strong>✅ Veredito Estatístico: Não se rejeita a Hipótese Nula (H₀) ao nível de significância de α = ${state.alphaAtual}.</strong><br>
        O p-valor obtido (<strong>${g2.p_valor.toFixed(4)}</strong>) é maior ou igual a α, e a estatística observada (${g2.nome_stat}<sub>obs</sub> = <strong>${g2.stat_obs}</strong>) encontra-se dentro da região de não-rejeição. Os dados observados são compatíveis com a hipótese de igualdade entre os grupos comparados.
      `;
    }

    if (typeof Plotly === "undefined") {
      dom.chartG2.innerHTML = `<p style="padding:20px; color:#e36b57;">Plotly.js indisponível para renderização da curva de distribuição sob H₀.</p>`;
      return;
    }

    // Limpa loader residual
    dom.chartG2.innerHTML = "";

    const xVals = g2.x_grid;
    const yVals = g2.pdf_grid;
    const crit = g2.valor_critico;

    // Traço da densidade sob H0
    const traceCurva = {
      x: xVals,
      y: yVals,
      type: "scatter",
      mode: "lines",
      line: { color: "#102a43", width: 2.5 },
      name: `Densidade sob H₀ (${g2.nome_stat})`,
    };

    // Região de rejeição à esquerda (x <= -crit)
    const idxLeft = xVals.filter((x) => x <= -crit);
    const traceRegiaoLeft = {
      x: idxLeft.concat([-crit, idxLeft[0]]),
      y: yVals.slice(0, idxLeft.length).concat([0, 0]),
      fill: "toself",
      fillcolor: "rgba(220, 38, 38, 0.4)",
      line: { color: "rgba(0,0,0,0)" },
      name: `Região Crítica (α/2 = ${(parseFloat(state.alphaAtual) / 2).toFixed(3)})`,
      type: "scatter",
      mode: "lines",
    };

    // Região de rejeição à direita (x >= +crit)
    const idxRight = xVals.filter((x) => x >= crit);
    const startIdx = xVals.length - idxRight.length;
    const traceRegiaoRight = {
      x: [crit].concat(idxRight, [idxRight[idxRight.length - 1]]),
      y: [0].concat(yVals.slice(startIdx), [0]),
      fill: "toself",
      fillcolor: "rgba(220, 38, 38, 0.4)",
      line: { color: "rgba(0,0,0,0)" },
      showlegend: false,
      type: "scatter",
      mode: "lines",
    };

    // Marcador da estatística observada
    const corObs = rejeita ? "#dc2626" : "#7357d8";
    const layout = {
      title: {
        text: `<b>G2: Distribuição sob H₀</b> | ${g2.nome_stat}<sub>crítico</sub> = ±${crit} | ${g2.nome_stat}<sub>obs</sub> = ${g2.stat_obs} (p = ${g2.p_valor.toExponential(3)})`,
        font: { size: 13.5, color: "#102a43" },
        x: 0.5,
        xanchor: "center",
        y: 0.97,
      },
      xaxis: { title: `Estatística do Teste (${g2.nome_stat})` },
      yaxis: { title: "Densidade de Probabilidade sob H₀" },
      showlegend: true,
      legend: { orientation: "h", y: -0.22, x: 0.5, xanchor: "center", font: { size: 11.5 } },
      margin: { t: 55, b: 75, l: 60, r: 40 },
      height: 420,
      shapes: [
        // Linhas verticais dos valores críticos
        { type: "line", x0: -crit, x1: -crit, y0: 0, y1: 1, yref: "paper", line: { color: "#dc2626", width: 1.5, dash: "dash" } },
        { type: "line", x0: crit, x1: crit, y0: 0, y1: 1, yref: "paper", line: { color: "#dc2626", width: 1.5, dash: "dash" } },
        // Linha destacada da estatística observada
        { type: "line", x0: g2.stat_obs, x1: g2.stat_obs, y0: 0, y1: 1, yref: "paper", line: { color: corObs, width: 3 } },
      ],
      annotations: [
        {
          x: g2.stat_obs,
          y: 0.85,
          yref: "paper",
          text: `<b>${g2.nome_stat}<sub>obs</sub> = ${g2.stat_obs}</b><br>(p = ${g2.p_valor.toExponential(3)})`,
          showarrow: true,
          arrowhead: 2,
          arrowcolor: corObs,
          font: { color: corObs, size: 12 },
          bgcolor: "#ffffff",
          bordercolor: corObs,
        },
      ],
    };

    Plotly.newPlot(dom.chartG2, [traceCurva, traceRegiaoLeft, traceRegiaoRight], layout, { responsive: true, displayModeBar: false });
  }

  // -------------------------------------------------------------------------
  // RENDERIZAÇÃO DO GRÁFICO G3 (Taxa de Erro Tipo I sob H0 em Múltiplos Cenários)
  // -------------------------------------------------------------------------
  function renderizarG3() {
    if (!dom.chartG3) return;
    const g3 = state.dados?.g3;
    if (!g3) {
      dom.chartG3.innerHTML = `<p style="padding:20px; color:#7b93aa;">Dados de simulação do Gráfico G3 não disponíveis.</p>`;
      return;
    }

    if (dom.g3Title) {
      dom.g3Title.textContent = `${g3.titulo} (N = ${g3.n_simulacoes.toLocaleString("pt-BR")} repetições)`;
    }

    if (dom.g3ConclusionBox) {
      dom.g3ConclusionBox.innerHTML = `
        <strong>📊 Conclusão Analítica de Erro Tipo I (Q1 & Q3):</strong><br>
        ${g3.texto_explicativo}
      `;
    }

    if (typeof Plotly === "undefined") {
      dom.chartG3.innerHTML = `<p style="padding:20px; color:#e36b57;">Plotly.js indisponível para renderização do Gráfico G3.</p>`;
      return;
    }

    // Limpa loader residual
    dom.chartG3.innerHTML = "";

    const traceWelch = {
      x: g3.cenarios_labels,
      y: g3.taxa_welch,
      name: "t-Student (Welch)",
      type: "bar",
      marker: { color: g3.cor_welch || "#1677c8" },
      text: g3.taxa_welch.map((v) => `${v.toFixed(1)}%`),
      textposition: "auto",
    };

    const traceMW = {
      x: g3.cenarios_labels,
      y: g3.taxa_mw,
      name: "Mann-Whitney U",
      type: "bar",
      marker: { color: g3.cor_mw || "#ec9b24" },
      text: g3.taxa_mw.map((v) => `${v.toFixed(1)}%`),
      textposition: "auto",
    };

    const layout = {
      title: {
        text: `<b>G3: Taxa de Erro Tipo I sob H₀</b> | Linha Nominal α = ${g3.alpha_nominal}%`,
        font: { size: 13.5, color: "#102a43" },
        x: 0.5,
        xanchor: "center",
        y: 0.97,
      },
      barmode: "group",
      xaxis: { title: g3.eixo_x_nome, tickangle: -10 },
      yaxis: {
        title: g3.eixo_y_nome,
        range: [0, 8],
        dtick: 1,
      },
      showlegend: true,
      legend: { orientation: "h", y: -0.25, x: 0.5, xanchor: "center", font: { size: 11.5 } },
      margin: { t: 55, b: 85, l: 60, r: 40 },
      height: 420,
      shapes: [
        {
          type: "line",
          x0: -0.5,
          x1: g3.cenarios_labels.length - 0.5,
          y0: g3.alpha_nominal,
          y1: g3.alpha_nominal,
          line: { color: g3.cor_linha_alfa || "#e36b57", width: 2.5, dash: "dash" },
        },
      ],
      annotations: [
        {
          x: g3.cenarios_labels[0],
          y: g3.alpha_nominal + 0.35,
          text: `<b>α Nominal = ${g3.alpha_nominal}%</b>`,
          showarrow: false,
          font: { color: g3.cor_linha_alfa || "#e36b57", size: 11 },
          bgcolor: "#fff",
          bordercolor: g3.cor_linha_alfa || "#e36b57",
          borderwidth: 1,
        },
      ],
    };

    Plotly.newPlot(dom.chartG3, [traceWelch, traceMW], layout, { responsive: true, displayModeBar: false });
  }

  // -------------------------------------------------------------------------
  // RENDERIZAÇÃO DO GRÁFICO G4 (Curvas de Poder Estatístico)
  // -------------------------------------------------------------------------
  function renderizarG4() {
    if (!dom.chartG4) return;
    const g4 = state.dados?.g4;
    if (!g4) {
      dom.chartG4.innerHTML = `<p style="padding:20px; color:#7b93aa;">Dados de simulação do Gráfico G4 não disponíveis.</p>`;
      return;
    }

    const cenario = g4.cenarios[state.cenarioG4] || Object.values(g4.cenarios)[0];
    if (!cenario) return;

    if (dom.g4Title) {
      dom.g4Title.textContent = `Curvas de Poder — ${cenario.nome}`;
    }

    if (dom.g4ConclusionBox) {
      dom.g4ConclusionBox.innerHTML = `
        <strong>⚡ Conclusão Analítica de Poder Estatístico (Q2 & Q3):</strong><br>
        ${g4.texto_explicativo}
      `;
    }

    if (typeof Plotly === "undefined") {
      dom.chartG4.innerHTML = `<p style="padding:20px; color:#e36b57;">Plotly.js indisponível para renderização do Gráfico G4.</p>`;
      return;
    }

    // Limpa loader residual
    dom.chartG4.innerHTML = "";

    const traceWelch = {
      x: cenario.deltas,
      y: cenario.poder_welch,
      name: "t-Student (Welch)",
      mode: "lines+markers",
      line: { color: g4.cor_welch || "#1677c8", width: 3 },
      marker: { size: 7 },
      type: "scatter",
    };

    const traceMW = {
      x: cenario.deltas,
      y: cenario.poder_mw,
      name: "Mann-Whitney U",
      mode: "lines+markers",
      line: { color: g4.cor_mw || "#ec9b24", width: 3 },
      marker: { size: 7 },
      type: "scatter",
    };

    const layout = {
      title: {
        text: `<b>G4: Curvas de Poder (Rejeições vs. Efeito)</b> — ${cenario.nome}`,
        font: { size: 13.5, color: "#102a43" },
        x: 0.5,
        xanchor: "center",
        y: 0.97,
      },
      xaxis: {
        title: g4.eixo_x_nome,
        dtick: 0.2,
      },
      yaxis: {
        title: g4.eixo_y_nome,
        range: [0, 105],
        dtick: 20,
      },
      showlegend: true,
      legend: { orientation: "h", y: -0.22, x: 0.5, xanchor: "center", font: { size: 11.5 } },
      margin: { t: 55, b: 75, l: 60, r: 40 },
      height: 420,
      shapes: [
        {
          type: "line",
          x0: cenario.deltas[0],
          x1: cenario.deltas[cenario.deltas.length - 1],
          y0: g4.limiar_poder_recomendado || 80.0,
          y1: g4.limiar_poder_recomendado || 80.0,
          line: { color: g4.cor_linha_80 || "#10b981", width: 2, dash: "dot" },
        },
      ],
      annotations: [
        {
          x: cenario.deltas[cenario.deltas.length - 1],
          y: 80.0,
          text: "<b>Poder 80% (Padrão)</b>",
          showarrow: true,
          arrowhead: 2,
          arrowcolor: g4.cor_linha_80 || "#10b981",
          ax: -60,
          ay: 20,
          font: { color: g4.cor_linha_80 || "#10b981", size: 11 },
          bgcolor: "#ffffff",
          bordercolor: g4.cor_linha_80 || "#10b981",
        },
      ],
    };

    Plotly.newPlot(dom.chartG4, [traceWelch, traceMW], layout, { responsive: true, displayModeBar: false });
  }

  // -------------------------------------------------------------------------
  // ATUALIZAÇÃO DOS KPIS
  // -------------------------------------------------------------------------
  function atualizarKPIs() {
    const view = state.dados.views[state.metricaAtual];
    if (!view) return;

    const g1 = view.distribuicoes[state.distribuicaoAtual]?.g1;
    const g2 = view.testes[state.testeAtual]?.alphas[state.alphaAtual];

    if (g1) {
      dom.kpiNReais.textContent = `${g1.stats_real.n}`;
      dom.kpiMedia.textContent = `${g1.stats_real.media} / ${g1.stats_sim.media}`;
    }

    if (g2) {
      dom.kpiStat.textContent = `${g2.nome_stat} = ${g2.stat_obs}`;
      dom.kpiDecisao.textContent = g2.rejeita_h0 ? "Rejeita H₀" : "Não Rejeita H₀";
      dom.kpiDecisao.style.color = g2.rejeita_h0 ? "#dc2626" : "#16a34a";
      dom.kpiDecisaoFoot.textContent = `p = ${g2.p_valor < 0.0001 ? g2.p_valor.toExponential(3) : g2.p_valor.toFixed(4)}`;
    }
  }

  // -------------------------------------------------------------------------
  // TABELA DE DADOS REAIS (Seção 6)
  // -------------------------------------------------------------------------
  function renderizarTabelaDadosReais() {
    if (!dom.tabelaDadosReaisBody) return;
    const dadosReais = state.dados?.dados_reais_testes?.linhas;
    if (!dadosReais || dadosReais.length === 0) {
      dom.tabelaDadosReaisBody.innerHTML = `<tr><td colspan="9" class="empty-state">${state.erroCarregamentoDados
        ? "Não foi possível buscar os resultados reais. Abra o dashboard por run_lab04.ps1 (ou run_lab04.bat), em vez de abrir index.html diretamente; depois atualize a página."
        : "O arquivo data/dados.json não contém resultados para a Seção 6. Gere novamente com python dashboard/gerar_dashboard.py."}</td></tr>`;
      return;
    }

    dom.tabelaDadosReaisBody.innerHTML = "";
    dadosReais.forEach((row) => {
      const tr = document.createElement("tr");

      const badgeWelch = row.welch.rejeita
        ? `<span class="badge-decision reject">t = ${row.welch.stat_t} (p=${row.welch.p_valor_formatado})</span>`
        : `<span class="badge-decision no-reject">t = ${row.welch.stat_t} (p=${row.welch.p_valor_formatado})</span>`;

      const badgeMW = row.mann_whitney.rejeita
        ? `<span class="badge-decision reject">U = ${row.mann_whitney.stat_u} (p=${row.mann_whitney.p_valor_formatado})</span>`
        : `<span class="badge-decision no-reject">U = ${row.mann_whitney.stat_u} (p=${row.mann_whitney.p_valor_formatado})</span>`;

      tr.innerHTML = `
        <td><strong>${row.metrica}</strong></td>
        <td>${row.n_elite_high} / ${row.n_medium_low}</td>
        <td>${row.media_elite_high} vs ${row.media_medium_low}</td>
        <td>${row.mediana_elite_high} vs ${row.mediana_medium_low}</td>
        <td>${badgeWelch}</td>
        <td><strong>d = ${row.welch.cohen_d}</strong> (${row.welch.classificacao_efeito})</td>
        <td>${badgeMW}</td>
        <td><strong>δ = ${row.mann_whitney.cliff_delta}</strong> (${row.mann_whitney.classificacao_efeito})</td>
        <td style="font-size:0.78rem; color:#334e68;">${row.conclusao}</td>
      `;
      dom.tabelaDadosReaisBody.appendChild(tr);
    });
  }

  // -------------------------------------------------------------------------
  // SCROLL OBSERVER PARA NAVEGAÇÃO LATERAL
  // -------------------------------------------------------------------------
  function configurarScrollObserver() {
    const secoes = document.querySelectorAll(".dashboard-section");
    const navLinks = document.querySelectorAll(".section-nav .nav-link");

    window.addEventListener("scroll", () => {
      let atual = "";
      const scrollPos = window.scrollY + 120;

      secoes.forEach((secao) => {
        if (secao.offsetTop <= scrollPos) {
          atual = secao.getAttribute("id");
        }
      });

      navLinks.forEach((link) => {
        link.classList.remove("is-active");
        if (link.getAttribute("href") === `#${atual}`) {
          link.classList.add("is-active");
        }
      });
    });
  }

  // -------------------------------------------------------------------------
  // TABELA DE EXPLORAÇÃO DE REPOSITÓRIOS
  // -------------------------------------------------------------------------
  function renderizarTabelaRepositorios(repos) {
    if (!dom.tabelaReposBody) return;
    dom.tabelaReposBody.innerHTML = "";

    repos.slice(0, 50).forEach((repo) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${repo.full_name || "—"}</strong></td>
        <td><span style="background:#e2e8f0; padding:2px 6px; border-radius:4px; font-size:0.75rem;">${repo.language || "—"}</span></td>
        <td>${repo.tier_dora_geral || "—"}</td>
        <td>${repo.stars ? repo.stars.toLocaleString("pt-BR") : "—"}</td>
        <td>${repo.lead_time_commit_mediana_dias != null ? repo.lead_time_commit_mediana_dias + " d" : "—"}</td>
        <td>${repo.tempo_recuperacao_mediana_horas != null ? repo.tempo_recuperacao_mediana_horas + " h" : "—"}</td>
        <td>${repo.deployment_frequency_semana != null ? repo.deployment_frequency_semana + "/sem" : "—"}</td>
      `;
      dom.tabelaReposBody.appendChild(tr);
    });
  }

  function filtrarTabelaRepositorios(termo) {
    if (!state.dados || !state.dados.repositorios) return;
    const filtrados = state.dados.repositorios.filter((r) => {
      const nome = (r.full_name || "").toLowerCase();
      const lang = (r.language || "").toLowerCase();
      return nome.includes(termo) || lang.includes(termo);
    });
    renderizarTabelaRepositorios(filtrados);
  }

  // -------------------------------------------------------------------------
  // FALLBACK DETERMINÍSTICO (caso executado via file:// sem servidor web)
  // -------------------------------------------------------------------------
  function gerarDadosEmbutidosFallback() {
    return {
      schema_version: 1,
      metricas: ["lead_time_commit_mediana_dias", "tempo_recuperacao_mediana_horas"],
      views: {
        lead_time_commit_mediana_dias: {
          meta: { nome: "Lead Time de Commit (dias)", unidade: "dias" },
          distribuicoes: {
            Lognormal: {
              g1: {
                valores_reais: [3.8, 4.2, 2.1, 7.5, 5.0, 1.2, 9.4, 4.8, 3.2, 6.1, 8.0, 2.5, 4.1],
                valores_simulados: [3.6, 4.0, 2.4, 6.9, 4.8, 1.5, 8.8, 4.5, 3.5, 5.8, 7.6, 2.8, 4.3],
                stats_real: { n: 300, media: 4.72, mediana: 3.86, dp: 2.84, skew: 0.67 },
                stats_sim: { n: 300, media: 4.59, mediana: 3.66, dp: 3.41, skew: 2.78 },
              },
            },
          },
          testes: {
            "t-Student": {
              cenario: "Tiers Elite & High vs. Medium & Low",
              alphas: {
                "0.05": {
                  titulo_distribuicao: "Distribuição t de Student sob H₀ (gl=297.4)",
                  nome_stat: "t",
                  stat_obs: -15.939,
                  p_valor: 8.99e-42,
                  valor_critico: 1.968,
                  rejeita_h0: true,
                  x_grid: [-4, -3, -2, -1, 0, 1, 2, 3, 4],
                  pdf_grid: [0.0001, 0.004, 0.054, 0.24, 0.39, 0.24, 0.054, 0.004, 0.0001],
                },
              },
            },
          },
        },
      },
      repositorios: [],
    };
  }
})();
