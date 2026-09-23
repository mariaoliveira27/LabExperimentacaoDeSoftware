import pandas as pd
from scipy import stats
import warnings

warnings.filterwarnings("ignore")

def executar_testes_wilcoxon(csv_entrada="registro_experimento.csv", csv_saida="resultados_wilcoxon.csv"):
    try:
        df = pd.read_csv(csv_entrada)
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo '{csv_entrada}' não encontrado.")
        return

    # Agrupa por Kata e Tratamento, tirando a média das métricas para fazer o pareamento
    df_kata = df.groupby(['Kata', 'Tratamento'])[['Tempo_Final_Considerado', 'Taxa_Sucesso_Testes']].mean().unstack()
    df_kata = df_kata.dropna()

    if len(df_kata) < 6:
        print(f"⚠️ Atenção: Apenas {len(df_kata)} Katas pareados encontrados. O ideal são 6.")

    # Isolando os vetores para o teste
    tempo_ia = df_kata['Tempo_Final_Considerado']['ia']
    tempo_manual = df_kata['Tempo_Final_Considerado']['manual']
    sucesso_ia = df_kata['Taxa_Sucesso_Testes']['ia']
    sucesso_manual = df_kata['Taxa_Sucesso_Testes']['manual']

    resultados = []

    # --- RQ1: Tempo ---
    try:
        stat_t, p_t = stats.wilcoxon(tempo_ia, tempo_manual)
        significativo_t = bool(p_t < 0.05 and tempo_ia.median() < tempo_manual.median())
    except ValueError:
        stat_t, p_t, significativo_t = (None, None, False)

    resultados.append({
        "Metrica": "Tempo_Final_Considerado (Minutos)",
        "Media_IA": round(tempo_ia.mean(), 2),
        "Media_Manual": round(tempo_manual.mean(), 2),
        "Mediana_IA": round(tempo_ia.median(), 2),
        "Mediana_Manual": round(tempo_manual.median(), 2),
        "Estatistica_W": stat_t,
        "P_Value": round(p_t, 5) if p_t is not None else None,
        "Significativo (p < 0.05)": significativo_t
    })

    # --- RQ2: Taxa de Sucesso ---
    try:
        stat_f, p_f = stats.wilcoxon(sucesso_ia, sucesso_manual)
        significativo_f = bool(p_f < 0.05 and sucesso_ia.median() > sucesso_manual.median())
    except ValueError:
        stat_f, p_f, significativo_f = (None, None, False)

    resultados.append({
        "Metrica": "Taxa_Sucesso_Testes (%)",
        "Media_IA": round(sucesso_ia.mean(), 2),
        "Media_Manual": round(sucesso_manual.mean(), 2),
        "Mediana_IA": round(sucesso_ia.median(), 2),
        "Mediana_Manual": round(sucesso_manual.median(), 2),
        "Estatistica_W": stat_f,
        "P_Value": round(p_f, 5) if p_f is not None else None,
        "Significativo (p < 0.05)": significativo_f
    })

    # Gera o DataFrame e salva em CSV
    df_resultados = pd.DataFrame(resultados)
    df_resultados.to_csv(csv_saida, index=False, sep=";", decimal=",", encoding="utf-8")
    
    print("=" * 70)
    print("✅ Testes de Wilcoxon concluídos!")
    print(f"📄 Tabela de resultados estatísticos salva em: {csv_saida}")
    print("=" * 70)
    print(df_resultados.to_string(index=False))

if __name__ == "__main__":
    executar_testes_wilcoxon()