"""Script de Geração do Dashboard do Lab 04 (Lab04S01)
Consolida os dados reais e simulados, calcula as estatísticas descritivas,
gera os gráficos G1 e G2 e produz o arquivo de dados JSON para a interface web.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.server
import json
from pathlib import Path
import socketserver
import webbrowser

from dados import (
    METRICAS_DISPONIVEIS,
    carregar_dados_reais,
    calcular_estatisticas_descritivas,
    simular_distribuicao_sintetica,
    gerar_simulacoes_g3_erro_tipo_1,
    gerar_simulacoes_g4_poder,
    calcular_tabela_dados_reais,
)
from graficos import (
    construir_dados_g1,
    construir_dados_g2,
    construir_dados_g3,
    construir_dados_g4,
    executar_teste_estatistico,
)

HERE = Path(__file__).resolve().parent


def gerar_dados_dashboard() -> dict:
    """Prepara todos os recortes de métricas, simulações e testes

    para consumo pela aplicação web.
    """
    df = carregar_dados_reais()
    metricas_validas = [m for m in METRICAS_DISPONIVEIS.keys() if m in df.columns]

    distribuicoes = ["Lognormal", "Exponencial", "Normal"]
    testes = ["t-Student", "Mann-Whitney U"]
    alphas = [0.01, 0.05, 0.10]

    views = {}

    for metrica in metricas_validas:
        serie_real = df[metrica].dropna().to_numpy()
        stats_real = calcular_estatisticas_descritivas(serie_real)

        # Divisão em dois grupos para comparação (ex: Tiers DORA Alto vs Baixo ou Metades)
        if "tier_dora_geral" in df.columns and len(df["tier_dora_geral"].dropna()) > 10:
            mask_alto = df["tier_dora_geral"].isin(["Elite", "High"])
            g1_arr = df[mask_alto][metrica].dropna().to_numpy()
            g2_arr = df[~mask_alto][metrica].dropna().to_numpy()
            label_g1, label_g2 = "Tiers Elite & High", "Tiers Medium & Low"
        else:
            n_mid = len(serie_real) // 2
            g1_arr = serie_real[:n_mid]
            g2_arr = serie_real[n_mid:]
            label_g1, label_g2 = "Subgrupo A", "Subgrupo B"

        views[metrica] = {
            "meta": METRICAS_DISPONIVEIS.get(metrica, {"nome": metrica, "descricao": "", "unidade": ""}),
            "stats_real": stats_real,
            "distribuicoes": {},
            "testes": {},
        }

        # Simulações para cada distribuição
        for dist in distribuicoes:
            sim_dados, fit_params = simular_distribuicao_sintetica(
                dados_reais=serie_real,
                distribuicao=dist,
                tamanho_amostra=len(serie_real),
                semente=42,
            )
            g1_spec = construir_dados_g1(serie_real, sim_dados)
            views[metrica]["distribuicoes"][dist] = {
                "fit_params": fit_params,
                "g1": g1_spec,
            }

        # Testes de hipótese para cada teste e alfa
        for t_tipo in testes:
            res_teste = executar_teste_estatistico(g1_arr, g2_arr, tipo_teste=t_tipo)
            views[metrica]["testes"][t_tipo] = {
                "cenario": f"{label_g1} vs. {label_g2}",
                "n_g1": len(g1_arr),
                "n_g2": len(g2_arr),
                "stat_obs": res_teste["stat_obs"],
                "p_valor": res_teste["p_valor"],
                "df": res_teste["df"],
                "alphas": {},
            }
            for a in alphas:
                g2_spec = construir_dados_g2(
                    stat_obs=res_teste["stat_obs"],
                    p_valor=res_teste["p_valor"],
                    graus_liberdade=res_teste["df"],
                    alpha=a,
                    tipo_teste=t_tipo,
                )
                views[metrica]["testes"][t_tipo]["alphas"][str(a)] = g2_spec

    # Repositórios para a tabela de exploração (amostra de até 100 linhas)
    colunas_tabela = [
        col for col in [
            "full_name",
            "language",
            "tier_dora_geral",
            "stars",
            "lead_time_commit_mediana_dias",
            "tempo_recuperacao_mediana_horas",
            "deployment_frequency_semana",
        ] if col in df.columns
    ]
    tabela_rows = df[colunas_tabela].head(100).to_dict(orient="records")

    # Simulações de Monte Carlo para os Gráficos G3 e G4 (Lab04S02 / Final)
    print("-> Executando simulações Monte Carlo para Gráficos G3 e G4 (Q1, Q2, Q3)...")
    dados_sim_g3 = gerar_simulacoes_g3_erro_tipo_1(semente=42, n_sims=10_000, alpha=0.05)
    g3_spec = construir_dados_g3(dados_sim_g3)

    dados_sim_g4 = gerar_simulacoes_g4_poder(semente=42, n_sims=2_000, alpha=0.05)
    g4_spec = construir_dados_g4(dados_sim_g4)

    # Tabela analítica dos dados reais (Seção 6 do edital)
    print("-> Consolidando estatísticas, p-valores e tamanhos de efeito nos dados reais (Seção 6)...")
    dados_reais_testes = calcular_tabela_dados_reais(df, alpha=0.05)

    payload = {
        "schema_version": 2,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_repositorios": len(df),
        "metricas": metricas_validas,
        "views": views,
        "g3": g3_spec,
        "g4": g4_spec,
        "dados_reais_testes": dados_reais_testes,
        "repositorios": tabela_rows,
    }

    # Salva em pasta data/dados.json
    data_dir = HERE / "data"
    data_dir.mkdir(exist_ok=True)
    caminho_json = data_dir / "dados.json"
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"[OK] Dados analíticos consolidados com sucesso em: {caminho_json}")
    return payload


def iniciar_servidor_local(porta: int = 8000) -> None:
    """Inicia servidor HTTP estático local na pasta do dashboard."""
    import os
    os.chdir(HERE)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", porta), handler) as httpd:
        url = f"http://localhost:{porta}"
        print(f"\n=======================================================")
        print(f"  Dashboard Lab 04 em execução em: {url}")
        print(f"  Pressione Ctrl+C para encerrar o servidor.")
        print(f"=======================================================\n")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor finalizado pelo usuário.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerador do Dashboard Lab 04")
    parser.add_argument("--servir", action="store_true", help="Inicia o servidor web local após gerar os dados.")
    parser.add_argument("--porta", type=int, default=8000, help="Porta do servidor local (padrão 8000).")
    args = parser.parse_args()

    gerar_dados_dashboard()

    if args.servir:
        iniciar_servidor_local(args.porta)


if __name__ == "__main__":
    main()
