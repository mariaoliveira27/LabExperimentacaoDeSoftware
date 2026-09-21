import os
import re
import time
from pathlib import Path

# Define os diretórios com base na estrutura do projeto
KATAS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Katas"))
SOLUCOES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "solucoes_das_Katas"))

def extrair_codigo(texto_resposta):
    match = re.search(r"```python\s*(.*?)\s*```", texto_resposta, re.DOTALL)
    if match:
        return match.group(1)
    match_generico = re.search(r"```\s*(.*?)\s*```", texto_resposta, re.DOTALL)
    if match_generico:
        return match_generico.group(1)
    return texto_resposta


def _inicializar_cliente():
    """Carrega a dependência opcional apenas quando uma geração é solicitada."""
    chave = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not chave:
        raise RuntimeError("Configure GEMINI_API_KEY ou GOOGLE_API_KEY para usar o Gemini.")
    try:
        from google import genai
        from google.genai.errors import APIError
    except ImportError as erro:
        raise RuntimeError("Instale google-genai para usar o tratamento com Gemini.") from erro
    return genai.Client(api_key=chave), APIError


def gerar_solucao(enunciado: str, caminho_saida: Path | str, *, modelo: str | None = None) -> dict:
    """Gera uma solução com a mesma API, prompt e extração usados no lote.

    O arquivo só é escrito após uma resposta não vazia. Falhas de configuração,
    API ou gravação são propagadas para o coordenador registrar a rodada.
    """
    if not isinstance(enunciado, str) or not enunciado.strip():
        raise ValueError("O enunciado deve conter texto.")
    modelo = modelo or os.environ.get("GEMINI_MODEL") or "gemini-3.6-flash"
    client, erro_api = _inicializar_cliente()
    prompt = (
        "Resolva o seguinte kata de programação em Python. "
        "Retorne APENAS o código Python funcional dentro de um bloco de código markdown (```python ... ```), "
        "sem explicações textuais adicionais.\n\n"
        f"Enunciado:\n{enunciado}"
    )
    chat = client.chats.create(model=modelo)
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            response = chat.send_message(prompt)
            break
        except erro_api:
            if tentativa == max_tentativas - 1:
                raise
            print(f"Erro na requisição. Tentando novamente em 5s ({tentativa + 1}/{max_tentativas})...")
            time.sleep(5)

    if not isinstance(response.text, str) or not response.text.strip():
        raise RuntimeError("O Gemini retornou uma resposta sem código.")
    codigo_solucao = extrair_codigo(response.text)
    if not codigo_solucao.strip():
        raise RuntimeError("O Gemini retornou um bloco de código vazio.")
    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_saida.write_text(codigo_solucao, encoding="utf-8")
    return {
        "caminho_saida": str(caminho_saida),
        "modelo": modelo,
        "tentativas": tentativa + 1,
    }


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

            print(f"Processando {arquivo}...")

            nome_saida = f"kata{num_kata}_gemini_ia.py"
            caminho_saida = os.path.join(SOLUCOES_DIR, nome_saida)
            gerar_solucao(enunciado, caminho_saida)

            print(f"Solução salva em: {caminho_saida}")

if __name__ == "__main__":
    processar_katas()
