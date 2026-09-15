import os
import re
import time
from google import genai
from google.genai.errors import APIError



# Inicializa o cliente da API do Gemini
client = genai.Client(api_key="YOUR_API_KEY_HERE")

# Define os diretórios com base na estrutura do projeto
KATAS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Katas"))
SOLUCOES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "solucoes_das_Katas"))

os.makedirs(SOLUCOES_DIR, exist_ok=True)

def extrair_codigo(texto_resposta):
    match = re.search(r"```python\s*(.*?)\s*```", texto_resposta, re.DOTALL)
    if match:
        return match.group(1)
    match_generico = re.search(r"```\s*(.*?)\s*```", texto_resposta, re.DOTALL)
    if match_generico:
        return match_generico.group(1)
    return texto_resposta

def processar_katas():
    arquivos = sorted(os.listdir(KATAS_DIR))
    
    for arquivo in arquivos:
        if arquivo.endswith(".md"):
            match_num = re.search(r"kata0?(\d+)", arquivo, re.IGNORECASE)
            if not match_num:
                continue
            num_kata = match_num.group(1).zfill(2)
            
            caminho_kata = os.path.join(KATAS_DIR, arquivo)
            with open(caminho_kata, "r", encoding="utf-8") as f:
                enunciado = f.read()

            prompt = (
                "Resolva o seguinte kata de programação em Python. "
                "Retorne APENAS o código Python funcional dentro de um bloco de código markdown (```python ... ```), "
                "sem explicações textuais adicionais.\n\n"
                f"Enunciado:\n{enunciado}"
            )

            print(f"Processando {arquivo}...")
            
            # Utiliza a API de Chat com o modelo gemini-3.6-flash
            chat = client.chats.create(model="gemini-3.6-flash")
            
            max_tentativas = 3
            codigo_solucao = ""
            
            for tentativa in range(max_tentativas):
                try:
                    response = chat.send_message(prompt)
                    codigo_solucao = extrair_codigo(response.text)
                    break
                except APIError as e:
                    print(f"Erro na requisição. Tentando novamente em 5s ({tentativa + 1}/{max_tentativas})...")
                    if tentativa < max_tentativas - 1:
                        time.sleep(5)
                    else:
                        raise

            nome_saida = f"kata{num_kata}_gemini_ia.py"
            caminho_saida = os.path.join(SOLUCOES_DIR, nome_saida)

            with open(caminho_saida, "w", encoding="utf-8") as f_out:
                f_out.write(codigo_solucao)

            print(f"Solução salva em: {caminho_saida}")

if __name__ == "__main__":
    processar_katas()