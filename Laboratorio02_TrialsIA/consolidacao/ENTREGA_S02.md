# Entrega local da Sprint 02 — Áulus

Verificação realizada em 16/09/2026. Branch:
`feat/lab02-s02-consolidacao-37`. Identidade Git conferida:
`Áulus <111202256+AulusHZP@users.noreply.github.com>`.

Esta branch local está associada descritivamente nas Issues à implementação
da integração da [#37](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/37)
e à [#38](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/38)
como relacionada, com a execução manual ainda pendente. O vínculo na seção
**Development** do GitHub depende de futura publicação autorizada da branch.

Este documento registra a preparação da entrega. Não é resultado de uma
rodada oficial. Commit, push, publicação de PR e encerramento de Issues
permanecem fora desta etapa, conforme solicitado pelo participante.

## Situação da sprint

A consulta ao repositório encontrou estas duas Issues da S02 atribuídas a
`AulusHZP`:

| Issue | Entrega | Situação local |
| --- | --- | --- |
| [#37](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/37) | Consolidação de scripts | Implementada e validada; arquivos aguardam revisão local. |
| [#38](https://github.com/mariaoliveira27/LabExperimentacaoDeSoftware/issues/38) | Resolver manualmente os Katas 1, 3 e 5 | Pendente da execução pessoal de Áulus; nenhuma solução foi gerada, completada ou corrigida nesta tarefa. |

As duas Issues estavam abertas na consulta. Não foi encontrada outra Issue
da S02 atribuída a Áulus. O protocolo geral prevê metade das rodadas com IA e
metade manual; não foi encontrada uma ordem concreta aprovada para Áulus nos
documentos consultados. Confirmar com o grupo a ordem e o registro das rodadas
com IA antes de iniciar a coleta oficial. A numeração abaixo identifica os
exercícios e não determina sua ordem de execução.

## Evidências da implementação

- Coordenador, executor, coletor e cliente Gemini existentes reutilizados.
- Entrada única: `Laboratorio02_TrialsIA/executar_rodada.py`.
- Mesmo `trial_id` em tempo, testes, métricas e solução preservada.
- Cópias por tentativa e SHA-256 vinculam a versão avaliada à coleta estática.
- Sucesso, reprovação, limite, interrupção e erro preservados explicitamente.
- Métricas indisponíveis e testes não obtidos não são transformados em zero.
- Diretórios/IDs existentes são recusados; dados anteriores ficam preservados.
- Comandos anteriores continuam disponíveis; mudanças de API e estado estão
  descritas no [guia da consolidação](README.md).

Validações concluídas:

| Verificação | Resultado |
| --- | --- |
| Testes existentes do coletor | 31 aprovados |
| Testes existentes dos casos/comparador | 12 aprovados |
| Testes da integração, executor e Gemini | 51 aprovados; reexecutados após instalar o SDK |
| Demonstração real DEMO_DOBRO | Cinco cenários verificados: sucesso, reprovação, limite, falha de análise e EOF |
| Revisão independente de snapshots, IDs e prazo | Sem bloqueadores identificados |
| Terminal com stdin aberto, sem resposta | Timeout real respeitado; processo encerrado sem travamento |
| Importação do SDK real | `google-genai==2.23.0`, `Client` e `APIError` disponíveis |
| `pip check` | Sem dependências quebradas |
| Gemini sem credencial, pela CLI real | Retorno 2, status ERRO, diagnóstico e artefatos preservados |
| Gemini autenticado, cliente existente e `gemini-3.6-flash` | SUCESSO no DEMO_DOBRO: 3/3 testes, LOC 7, complexidade média 1,0; IDs e hashes conferidos |

Evidências locais ignoradas pelo Git:

- [Resumo dos cinco cenários](resultados_demo/20260916T162123Z_b9253f06/resumo_demonstracao.json).
- [Verificação do Gemini sem chave](resultados_demo/gemini_sem_chave_20260916T163042Z_f90cbcb7/verificacao_gemini.json).
- [Validação real do Gemini](resultados_demo/gemini_real_20260916T163616Z_8708bf1a/verificacao_gemini.json).

Esses links existem no ambiente da validação e não serão publicados com o
código. O comando `demonstrar.py` documentado no guia reproduz os cinco cenários
em uma pasta nova. Resultados oficiais e soluções existentes não foram alterados.

## Rodadas manuais de Áulus

Após confirmar a ordem com o grupo, crie no editor apenas o arquivo vazio do
exercício que vai iniciar. Execute o comando correspondente na raiz do
repositório. Pressione ENTER no coordenador para liberar a rodada e só então
escreva a solução manual. Use o menu para testar durante a resolução.

Kata 1:

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe Laboratorio02_TrialsIA/executar_rodada.py --participante aulus --exercicio kata01 --tratamento manual --solucao Laboratorio02_TrialsIA/solucoes_das_Katas/kata01_aulus_manual.py
```

Kata 3:

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe Laboratorio02_TrialsIA/executar_rodada.py --participante aulus --exercicio kata03 --tratamento manual --solucao Laboratorio02_TrialsIA/solucoes_das_Katas/kata03_aulus_manual.py
```

Kata 5:

```powershell
.\Laboratorio02_TrialsIA\metricas_estruturais\.venv\Scripts\python.exe Laboratorio02_TrialsIA/executar_rodada.py --participante aulus --exercicio kata05 --tratamento manual --solucao Laboratorio02_TrialsIA/solucoes_das_Katas/kata05_aulus_manual.py
```

Ao finalizar cada rodada, confira o manifesto indicado pelo terminal, a cópia
final, os testes e as métricas. Conserve o registro mesmo se houver reprovação,
limite, interrupção ou erro. Não edite o resultado para atribuir sucesso nem
refaça retroativamente o tempo de uma solução já escrita. Uma avaliação com
`--automatico` mede somente código pronto e não substitui o tempo de resolução.

## Pendências que dependem de configuração ou participação

1. **Configuração para novas chamadas:** a validação real do Gemini foi
   concluída com a credencial fornecida por Áulus e o modelo `gemini-3.6-flash`.
   A chave foi usada somente na memória dos processos, sem persistência no
   repositório ou configuração permanente. Para novas chamadas, configurar
   `GEMINI_API_KEY` ou `GOOGLE_API_KEY` no ambiente e manter o modelo acordado
   pelo grupo. Não colocar chaves em arquivos versionados ou no PR.
2. **Coleta oficial:** Áulus deve executar pessoalmente suas rodadas manuais;
   alinhar previamente a ordem contrabalanceada e as rodadas com IA com o grupo.
3. **Entrega no GitHub:** quando autorizada em uma etapa posterior, revisar o
   diff, criar o commit e publicar o PR. Nesta etapa os arquivos ficam locais.

## Texto preparado para um futuro PR

**Título:** `feat(lab02): consolidar execução de rodadas da S02 (#37)`

**Descrição:**

Durante uma rodada, o código em edição pode mudar enquanto os testes estão
executando. A integração passa a avaliar cópias e a associar testes, métricas,
tempo e solução preservada ao mesmo `trial_id` e SHA-256, evitando atribuir
aprovação a uma versão diferente da coletada.

Disponibiliza `executar_rodada.py` como entrada única, reutilizando coordenador,
executor, Radon e cliente Gemini. O prazo cobre entrada de terminal, bateria e
geração; estados de encerramento e falhas ficam explícitos, com dados
indisponíveis representados por `null`. Documenta compatibilidade e demonstração
em exercício separado dos seis oficiais.

Validação: 94 testes aprovados, cinco cenários demonstrativos, revisão
independente e `pip check`. SDK Gemini instalado e importado; integração
validada com mocks, falha de configuração sem chave e uma chamada real
autenticada ao `gemini-3.6-flash` para DEMO_DOBRO: 3/3 testes, LOC 7,
complexidade média 1,0, identificadores e hashes consistentes.

Relacionado à #37. Não inclui a resolução manual da #38 nem altera resultados
de rodadas anteriores.

**Mensagem de commit sugerida:**

```text
feat(lab02): consolidar execução de rodadas da S02 (#37)
```
