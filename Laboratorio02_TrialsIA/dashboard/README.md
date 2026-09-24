# Dashboard do Lab 2 — Manual × IA

Dashboard estático em português para explorar as 18 rodadas do experimento. Pandas prepara os dados e Matplotlib/Seaborn geram os gráficos. O navegador seleciona os recortes prontos, sem servidor Python de aplicação ou dependências externas de interface.

## Executar localmente

Na pasta `Laboratorio02_TrialsIA/dashboard`, usando PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe gerar_dashboard.py
.venv/Scripts/python.exe -m http.server 8000 --directory public
```

Abra <http://localhost:8000>. Use um servidor HTTP; abrir o HTML por `file://` impede o carregamento do manifesto em alguns navegadores.

Em Linux/macOS, substitua `.venv/Scripts/python.exe` por `.venv/bin/python`.

## Atualizar os dados

```powershell
.venv/Scripts/python.exe gerar_dashboard.py --dados ../cronometro --saida public
```

`--dados` recebe a pasta que contém `registro_experimento.csv` e `resultados/`. O gerador lê os dados, sem executar soluções ou alterar os registros originais. O diretório padrão é `../cronometro`; uma exportação independente também pode usar `insumos/cronometro`.

São produzidos 28 recortes: Todos/Áulus/Maria/Vinícius × Todas/K01–K06. Cada recorte contém cinco gráficos em SVG e PNG, estatísticas e um CSV analítico. O manifesto fica em `public/data/manifest.json`. A interface-fonte fica em `web/` e é copiada para `public/` durante a geração. Edite `web/`, não a cópia gerada.

Os filtros afetam indicadores, gráficos, tabela e downloads. Os parâmetros `integrante` e `kata` na URL permitem guardar um recorte. Quando um tratamento não está presente, a interface informa “Sem observações”, sem usar zero para representar ausência.

Os gráficos usam distribuições e barras horizontais, com medianas e percentuais destacados. Cada gráfico tem uma versão de tela (`display`) e outra para celular (`mobile`), além dos arquivos SVG/PNG completos para download. O navegador escolhe a imagem adequada, sem recalcular estatísticas. **Ampliar** abre o gráfico com título, contexto e notas; Escape fecha a janela e devolve o foco ao botão. As escalas permanecem iguais entre os recortes. Em amostras com menos de três valores, a distribuição mostra somente os pontos, sem caixa.

## Definições e limitações

- **População:** 18 IDs únicos do CSV principal, nove Manual e nove IA. Os JSONs individuais são associados por `Trial_ID`, sem depender dos caminhos Windows gravados no CSV.
- **Ajuste solicitado por Áulus:** os rótulos Manual/IA de suas seis rodadas são invertidos na preparação do dashboard. No recorte de Áulus, a mediana exibida passa a IA = 9,15 min e Manual = 19,8 min. O ajuste está explícito em `dados.py`; os arquivos de origem e os IDs permanecem intactos. Os CSVs exportados preservam `tratamento_registrado` e sinalizam `tratamento_ajustado`. Todos os indicadores e gráficos usam o tratamento ajustado de forma consistente; os demais integrantes permanecem iguais.
- **Tempo registrado:** campo `Tempo_Final_Considerado`, em minutos. Os scripts de coleta usam durações fixas e modo de simulação; a origem das durações não foi confirmada. Esses valores não são apresentados como time-to-green validado ou evidência causal de produtividade.
- **Sucesso:** percentual de testes aprovados em cada rodada, priorizando `testes.json`. A média por tratamento dá o mesmo peso a cada rodada, mesmo quando o número de testes varia. O número de rodadas com 100% é um indicador separado.
- **Rodada Áulus/K04 (ID original `aulus_K04_ia_01`, tratamento ajustado Manual):** só existe no CSV. Seu percentual de 100% e tempo de 20 minutos são apresentados como registros do CSV; contagens de testes e métricas de código ficam ausentes.
- **Status:** seis rodadas têm `Status=SUCESSO` apesar de testes falhando. A aprovação é derivada dos testes, e a divergência é preservada na tabela.
- **Estrutura:** complexidade ciclomática média por função e LOC vêm dos 17 `metricas.json` arquivados. LOC representa linhas totais; SLOC também está disponível no CSV para consulta. Cada métrica informa seu próprio tamanho amostral.
- **Resumos:** mediana, primeiro e terceiro quartis para tempo, complexidade e LOC. Os quartis usam a interpolação linear do Pandas. Pontos individuais tornam visíveis os dados da amostra pequena.
- **Fontes excluídas:** o CSV geral da RQ3 contém 20 soluções, incluindo arquivos sem rodada correspondente, e uma medida global de duplicação repetida em cada linha. O CSV enriquecido de falhas também não é uma amostra adicional.
- **Interpretação:** análise descritiva, sem novos testes de hipótese, conclusões causais ou imputação de valores ausentes. A comparação de sucesso inclui um resultado declarado somente no CSV, identificado no painel.

## Testes

Depois de gerar o dashboard:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Os testes verificam fontes, ausência de dados, divergências, IDs duplicados, cálculos e integridade dos 28 recortes. A verificação de navegador é opcional e documentada no seu arquivo de teste; o site não depende do Playwright para funcionar.

Para incluir a verificação no Edge instalado, em modo headless:

```powershell
.venv/Scripts/python.exe -m pip install playwright
$env:DASHBOARD_BROWSER_TESTS = "1"
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
```

A suíte inclui todos os filtros, downloads, versões responsivas, ampliação por teclado, erro de carregamento e celular. Ambiente validado: Python 3.12, Pandas 3.0.6, Matplotlib 3.11.2 e Seaborn 0.13.2.

## Publicação privada no Sites

A configuração local `.openai/hosting.json` guarda o identificador do site. Uma cópia independente do dashboard, com insumos e arquivos gerados, é enviada ao repositório de fontes do Sites. A exportação copia `public/` para `dist/`, diretório estático aceito pelo Sites. O pacote de publicação contém apenas a configuração e `dist/`, a partir do mesmo commit enviado. As credenciais temporárias não são gravadas nos arquivos.

Para preparar uma cópia independente em uma pasta nova:

```powershell
.venv/Scripts/python.exe exportar_sites.py --saida .local/sites-source
```

A exportação preserva os valores necessários à reprodução em `insumos/cronometro`, removendo campos com caminhos pessoais e deixando de fora os códigos executáveis das soluções. Não sobrescreve uma pasta já preenchida.

Para atualizar a publicação, regenere os arquivos, valide os testes e publique uma versão do mesmo site, preservando o acesso privado. O link privado exige autenticação do proprietário; a visibilidade não é alterada automaticamente para permitir compartilhamento.
