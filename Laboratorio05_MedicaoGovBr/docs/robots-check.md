# Verificação do robots.txt

Gerado por `scripts/robots-check.mjs` em 2026-11-25T11:37:39-03:00.

User agents verificados: `*`, `Lighthouse`, `Chrome-Lighthouse`. Uma URL só conta como liberada se todos eles forem liberados.
As regras seguem a RFC 9309: robots.txt com 4xx significa sem restrições; 429, 5xx ou erro de rede significa proibição total.
Cada robots.txt é pedido primeiro com um User-Agent que identifica o estudo (`Mozilla/5.0 (compatible; Lab05-robots-check; academic study, PUC Minas)`). Se a resposta não for 2xx, ele é pedido mais uma vez com o User-Agent de desktop que o Lighthouse envia, porque alguns hosts bloqueiam clientes que não são navegadores. A coluna "UA" diz qual resposta foi usada.
As cópias de cada robots.txt estão em `data/robots/`. O registro completo das tentativas está em `data/robots-check.json`.

| Serviço | URL | robots.txt | Baixado em | HTTP | UA | Liberado? | Crawl-delay | Observações |
|---|---|---|---|---|---|---|---|---|
| Portal gov.br | https://www.gov.br/pt-br | https://www.gov.br/robots.txt | 2026-11-25T11:37:16-03:00 | 200 | identificado | sim | — | caminho liberado para todos os user agents verificados |
| Meu INSS | https://meu.inss.gov.br/ | https://meu.inss.gov.br/robots.txt | 2026-11-25T11:37:18-03:00 | 403 | identificado | sim | — | robots.txt devolveu HTTP 403; pela RFC 9309, não há restrições |
| Receita Federal (e-CAC) | https://cav.receita.fazenda.gov.br/autenticacao/login | https://cav.receita.fazenda.gov.br/robots.txt | 2026-11-25T11:37:23-03:00 | 200 | identificado | sim | — | a URL do robots.txt devolveu uma página HTML (sem regras válidas); liberado (TLS: servidor não enviou o intermediário; "AC SERPRO AR46 OV TLS CA 2025" baixado de http://secure.globalsign.com/cacert/acserproar46ovtlsca2025.crt e verificado contra a raiz "GlobalSign Root R46") |
| Carteira de Trabalho Digital (web) | https://servicos.mte.gov.br/spme-v2/ | https://servicos.mte.gov.br/robots.txt | 2026-11-25T11:37:26-03:00 | 404 | identificado | sim | — | robots.txt devolveu HTTP 404; pela RFC 9309, não há restrições |
| Valores a Receber (Banco Central) | https://www.bcb.gov.br/meubc/valores-a-receber?modalAberto=cuidado-com-golpes-modal | https://www.bcb.gov.br/robots.txt | 2026-11-25T11:37:32-03:00 | 200 | identificado | sim | — | caminho liberado para todos os user agents verificados |
| Meu SUS Digital | https://meususdigital.saude.gov.br/ | https://meususdigital.saude.gov.br/robots.txt | 2026-11-25T11:37:34-03:00 | 200 | identificado | sim | — | a URL do robots.txt devolveu uma página HTML (sem regras válidas); liberado |
| Portal MG (serviços do Governo de Minas) | https://www.mg.gov.br/ | https://www.mg.gov.br/robots.txt | 2026-11-25T11:37:37-03:00 | 200 | identificado | sim | — | caminho liberado para todos os user agents verificados |
| Portal do Servidor | https://www.gov.br/servidor/pt-br | https://www.gov.br/robots.txt | 2026-11-25T11:37:16-03:00 | 200 | identificado | sim | — | caminho liberado para todos os user agents verificados |
| Consumidor.gov.br | https://www.consumidor.gov.br/ | https://www.consumidor.gov.br/robots.txt | 2026-11-25T11:37:39-03:00 | 200 | identificado | sim | — | caminho liberado para todos os user agents verificados |
| ENEM (Inep) | https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem | https://www.gov.br/robots.txt | 2026-11-25T11:37:16-03:00 | 200 | identificado | sim | — | caminho liberado para todos os user agents verificados |

Todas as URLs da lista estão liberadas.

## Candidatas descartadas

Candidatas retiradas de `data/urls.json`, mantidas aqui como evidência (fonte: a lista `replaced` desse arquivo).

| Candidata | URL | Data | Trocada por | Motivo |
|---|---|---|---|---|
| Conecte SUS | https://conectesus-paciente.saude.gov.br/ | 2026-11-17 | consumidor | A URL redireciona para https://meususdigital.saude.gov.br/ (o Meu SUS Digital substituiu o Conecte SUS). Mantê-la mediria a mesma página duas vezes. |
| Detran-MG | https://www.detran.mg.gov.br/ | 2026-11-17 | portal-mg | O robots.txt (HTTP 200) tem "User-agent: *" + "Disallow: /" (só Googlebot e bedrockbot são liberados). Cópia mantida em data/robots/www.detran.mg.gov.br.txt. https://transito.mg.gov.br/ redireciona para o mesmo host. |
| Senatran - Portal de Serviços (considerado para substituir o Detran-MG) | https://portalservicos.senatran.serpro.gov.br/ | 2026-11-17 | portal-mg | A requisição do robots.txt não teve resposta HTTP (status 000 no curl), ou seja, inacessível; pela RFC 9309 assume-se proibição total, então não foi usado. |
| Portal da Transparência | https://portaldatransparencia.gov.br/ | 2026-11-17 | svr-bcb | O robots.txt libera "/", mas no piloto 4 de 6 execuções do Lighthouse receberam um CAPTCHA do AWS WAF ("Let's confirm you are human", documento principal com HTTP 202) em vez do portal. Só a primeira visita e uma visita depois receberam a página real. Contornar o CAPTCHA está fora do escopo, então o serviço não pode ser medido de forma confiável. Arquivos brutos mantidos em data/raw/pilot/transparencia_*.json. |
| IBGE (considerado para substituir o Portal da Transparência) | https://www.ibge.gov.br/ | 2026-11-17 | svr-bcb | A página inicial devolveu HTTP 403 a uma única requisição com curl e User-Agent de navegador (proteção anti-bot), então não foi usado. |
