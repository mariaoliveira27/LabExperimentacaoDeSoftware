import time
import csv
import os
from datetime import datetime

ARQUIVO_LOG = "registro_experimento.csv"
TIMEBOX_MINUTOS = 35

def inicializar_csv():
    """Cria o arquivo CSV com os cabeçalhos se ele não existir."""
    if not os.path.exists(ARQUIVO_LOG):
        with open(ARQUIVO_LOG, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Integrante", "Kata", "Tratamento_IA", "Horario_Inicio", 
                "Horario_Fim", "Tempo_Decorrido_Min", "Passou_Testes", 
                "Tempo_Final_Considerado", "Dado_Censurado"
            ])

def executar_trial():
    """Conduz a interface visual e registra os dados do trial."""
    print("="*45)
    print("⏱️  COLETA DE TEMPO - EXPERIMENTO DE IA ⏱️")
    print("="*45)
    
    integrante = input("1. Nome do Integrante: ")
    kata = input("2. Nome do Kata: ")
    com_ia = input("3. Usou IA neste trial? (S/N): ").strip().upper() == 'S'
    
    # Início da medição
    input("\n[ Pressione ENTER para iniciar o cronômetro ]")
    inicio_ts = time.time()
    horario_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n▶️ Iniciado em: {horario_inicio}")
    print(f"⚠️ Lembre-se: O time-box máximo é de {TIMEBOX_MINUTOS} minutos.")
    
    # Fim da medição
    input("\n[ Pressione ENTER quando passar nos testes ou estourar o tempo ]")
    fim_ts = time.time()
    horario_fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    tempo_decorrido = (fim_ts - inicio_ts) / 60
    print(f"\n⏹️ Finalizado em: {horario_fim}")
    print(f"⏳ Tempo real decorrido: {tempo_decorrido:.2f} minutos")
    
    passou = input("\nO código passou em TODOS os testes automatizados? (S/N): ").strip().upper() == 'S'
    
    # Lógica de Censura (Regra do Experimento)
    if tempo_decorrido >= TIMEBOX_MINUTOS or not passou:
        tempo_final = TIMEBOX_MINUTOS
        censurado = True
        print(f"\n❌ Status: CENSURADO")
        print(f"Motivo: " + ("Estourou o time-box." if tempo_decorrido >= TIMEBOX_MINUTOS else "Falhou nos testes."))
        print(f"Tempo registrado para análise: {TIMEBOX_MINUTOS}.00 min")
    else:
        tempo_final = round(tempo_decorrido, 2)
        censurado = False
        print(f"\n✅ Status: SUCESSO")
        print(f"Tempo registrado para análise: {tempo_final} min")
        
    # Salvar no CSV
    with open(ARQUIVO_LOG, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            integrante, kata, com_ia, horario_inicio, horario_fim, 
            round(tempo_decorrido, 2), passou, tempo_final, censurado
        ])
        
    print(f"\n💾 Dados salvos com sucesso em '{ARQUIVO_LOG}'!\n")

if __name__ == "__main__":
    inicializar_csv()
    executar_trial()