import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    
    # Cria a pasta para salvar os gráficos, caso não exista
    if not os.path.exists("graficos_dora"):
        os.makedirs("graficos_dora")
    pasta_graficos = "graficos_dora"
    
    # Caminho do dataset gerado pelo pipeline
    caminho_csv = "data/output/repositorios_aprovados.csv"
    
    if not os.path.exists(caminho_csv):
        print(f"Erro: Arquivo '{caminho_csv}' não encontrado.")
        print("Certifique-se de executar o pipeline (python pipeline.py) primeiro.")
        return

    # Carrega os dados
    df = pd.read_csv(caminho_csv)
    print(f"Dados carregados: {df.shape[0]} repositórios.")

    # Configuração visual padrão para gráficos mais elegantes
    sns.set_theme(style="whitegrid", palette="muted")

    # =========================================================================
    # GRÁFICO 1 - RQ 01: Distribuição da Frequência de Deploy
    # =========================================================================
    plt.figure(figsize=(10, 6))
    sns.histplot(df['deployment_frequency_semana'].dropna(), bins=30, kde=True, color='skyblue')
    plt.title("RQ 01: Distribuição da Frequência de Deploy")
    plt.xlabel("Releases por Semana (Escala Logarítmica)")
    plt.ylabel("Quantidade de Repositórios")
    plt.xscale('log') # Escala log para lidar com repositórios que fazem deploy múltiplo por dia vs 1 por mês
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_graficos, "rq01_deployment_frequency.png"), dpi=300)
    plt.close()
    
    # =========================================================================
    # GRÁFICO 2 - RQ 02: Comparação de Lead Time (Variante A vs Variante B)
    # =========================================================================
    plt.figure(figsize=(10, 6))
    
    # Boxplot para mostrar a mediana e o IQR
    sns.boxplot(
        data=df[['lead_time_release_mediana_dias', 'lead_time_commit_mediana_dias']],
        orient='h' 
    )
    plt.title("RQ 02: Lead Time for Changes (Por Release vs Por Commit)")
    plt.xlabel("Mediana em Dias (Escala Logarítmica)")
    plt.yticks([0, 1], ['Variante (a) - Por Release', 'Variante (b) - Por Commit'])
    
    # Escala logarítmica no eixo X é importante pois métricas de repositórios 
    # costumam ser muito assimétrica
    plt.xscale('log') 
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_graficos, "rq02_lead_time_comparacao.png"), dpi=300)
    plt.close()
    
    # =========================================================================
    # GRÁFICO 3 - RQ 03: Distribuição do Change Failure Rate
    # =========================================================================
    plt.figure(figsize=(10, 6))
    sns.histplot(df['cfr_ci_proxy'].dropna(), bins=20, kde=True, color='indianred')
    plt.title("RQ 03: Distribuição da Taxa de Falha (Proxy CI)")
    plt.xlabel("Change Failure Rate (0.0 a 1.0)")
    plt.ylabel("Frequência de Repositórios")
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_graficos, "rq03_cfr_distribuicao.png"), dpi=300)
    plt.close()
    
    # =========================================================================
    # GRÁFICO 4 - RQ 04: Distribuição do Tempo de Recuperação
    # =========================================================================
    plt.figure(figsize=(10, 6))
    sns.histplot(df['tempo_recuperacao_mediana_horas'].dropna(), bins=30, kde=True, color='mediumpurple')
    plt.title("RQ 04: Distribuição do Tempo de Recuperação")
    plt.xlabel("Tempo de Recuperação em Horas (Escala Logarítmica)")
    plt.ylabel("Quantidade de Repositórios")
    plt.xscale('log') 
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_graficos, "rq04_tempo_recuperacao.png"), dpi=300)
    plt.close()

    # =========================================================================
    # GRÁFICO 5 - RQ 05: Velocidade vs Estabilidade (Frequência x CFR)
    # =========================================================================
    plt.figure(figsize=(10, 6))
    sns.scatterplot(
        data=df, 
        x='deployment_frequency_semana', 
        y='cfr_ci_proxy', 
        hue='tier_dora_geral',
        hue_order=['Elite', 'High', 'Medium', 'Low'],
        palette={'Elite': '#2ca02c', 'High': '#1f77b4', 'Medium': '#ff7f0e', 'Low': '#d62728'},
        alpha=0.7,
        edgecolor=None
    )
    plt.title("RQ 05: Frequência de Deploy vs Change Failure Rate (Velocidade x Estabilidade)")
    plt.xlabel("Frequência de Deploy (releases por semana) - Escala Log")
    plt.ylabel("Change Failure Rate (Proxy CI)")
    
    # Eixo X em log pois há bibliotecas com 1 release por mês e outras com 50 na semana
    plt.xscale('log') 
    plt.legend(title='Tier DORA (Geral)')
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_graficos, "rq05_dispersao_velocidade_estabilidade.png"), dpi=300)
    plt.close()


    # =========================================================================
    # GRÁFICO 6 - RQ 08 (Bônus): Rework Rate
    # =========================================================================
    # Verifica se a coluna foi adicionada no pipeline antes de tentar plotar
    coluna_rq08 = 'rework_rate' # Troque se você usou outro nome no pipeline.py
    
    if coluna_rq08 in df.columns:
        plt.figure(figsize=(10, 6))
        sns.histplot(df[coluna_rq08].dropna(), bins=20, kde=True, color='darkorange')
        plt.title("RQ 08: Distribuição da Taxa de Retrabalho (Rework Rate)")
        plt.xlabel("Proporção de Releases Corretivas (0.0 a 1.0)")
        plt.ylabel("Quantidade de Repositórios")
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_graficos, "rq08_rework_rate.png"), dpi=300)
        plt.close()
        print("Gráfico da RQ 08 (Rework Rate) gerado com sucesso!")
    else:
        print(f"Aviso: A coluna '{coluna_rq08}' não foi encontrada no CSV. O gráfico da RQ 08 foi ignorado.")
        print("Lembre-se de adicionar o cálculo do Rework Rate ao registro salvo no seu pipeline.py.")
        
    # =========================================================================
    # GRÁFICO 5 - Classificação DORA Geral
    # =========================================================================
    plt.figure(figsize=(8, 6))
    ordem_tiers = ['Elite', 'High', 'Medium', 'Low']
    cores_tiers = ['#2ca02c', '#1f77b4', '#ff7f0e', '#d62728']
    
    # Conta quantos repositórios estão em cada Tier
    sns.countplot(data=df, x='tier_dora_geral', order=ordem_tiers, palette=cores_tiers)
    plt.title("Classificação Geral DORA dos Repositórios")
    plt.xlabel("Categoria DORA")
    plt.ylabel("Quantidade de Repositórios")
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_graficos, "dora_classificacao_geral.png"), dpi=300)
    plt.close()

    print(f"Sucesso! 4 gráficos foram gerados na pasta '{pasta_graficos}/'")

if __name__ == "__main__":
    main()