# Dashboard dos Resultados

Dashboard estática para explorar os CSVs das RQs do Laboratório 01. Ela não faz novas consultas à API do GitHub: os gráficos e indicadores são calculados no navegador a partir dos arquivos em `../CSV - 100/` e `../CSV - 1000/`.

## Como executar

No diretório `Laboratorio01_GitHubRepo`, inicie um servidor local:

```powershell
python -m http.server 8000
```

Depois, abra <http://localhost:8000/dashboard/> no navegador.

> Não abra o `index.html` diretamente pelo explorador de arquivos. Os navegadores bloqueiam a leitura dos CSVs via `fetch` quando a página é aberta com `file://`.

## Recursos

- Alternância entre as amostras de 100 e 1.000 repositórios.
- Busca por repositório e filtro por linguagem primária.
- Indicadores de popularidade, idade, PRs e resolução de issues.
- Visualizações para as RQs 01 a 07 e tabela de exploração dos repositórios.
- Barras de linguagem clicáveis para aplicar o filtro global e destaques de PRs/tags que fixam o projeto selecionado no explorador.
- Faixas de tags clicáveis, aplicadas somente à tabela, e ordenação por coluna nas duas tabelas.
- Alternância de métrica na RQ07 (PRs, releases, atividade de issues e atualização), com suporte a teclado e redução de movimento.
- Sem bibliotecas externas ou dependências para instalar.

## Observação sobre RQ04

O CSV individual disponível para RQ04 expressa a frequência de issues, que a dashboard apresenta como proxy de atividade. A média de dias sem atualização é mostrada na seção de linguagem, pois esse campo está disponível de forma agregada em `bonus.csv`. O arquivo `release.csv` armazena **tags**, que a dashboard identifica como proxy de releases na RQ03.
