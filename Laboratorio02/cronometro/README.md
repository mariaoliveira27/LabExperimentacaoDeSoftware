# ⏱️ Como usar o Cronômetro do Experimento

Guia passo a passo para execução e registro dos tempos de desenvolvimento durante os katas.

---

## 📋 Passo a Passo para Execução

1. **Abra o terminal** na pasta raiz do repositório.
2. **Execute o script** com o comando abaixo:
   ```bash
   python cronometro_lab.py
   ```
   *(Dependendo da sua configuração de ambiente, pode ser necessário utilizar `python3`)*.

3. **Preencha as informações iniciais**:
   - Seu nome
   - Nome do kata
   - Se o assistente de IA está habilitado para a rodada

4. **Inicie a contagem**:
   - Pressione <kbd>ENTER</kbd> no terminal no **exato momento** em que começar a programar.

5. **Finalize a contagem**:
   - Pressione <kbd>ENTER</kbd> novamente assim que o código passar nos testes automatizados ou o tempo limite estourar.

6. **Classifique o resultado**:
   - Responda se o código passou em todos os testes para que o sistema registre a classificação do resultado (**Sucesso** ou **Falha**).

---

## ⚠️ Observação Importante

O script salvará os resultados automaticamente no arquivo `registro_experimento.csv`. 

> **Atenção:** **Não altere este arquivo manualmente.** Ele será lido pelo script do Pandas na **Sprint 3** para a geração do Dashboard.