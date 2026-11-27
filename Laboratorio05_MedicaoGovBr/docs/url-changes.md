# Lista final de URLs e trocas

Fonte: `data/urls.json` (lista e histórico de trocas) e `docs/robots-check.md` (evidência do `robots.txt`, gerada em 25/11/2026 às 11:37, antes da primeira sessão). A seção 1.4 de [`proposta.md`](proposta.md) resume as trocas; este arquivo é o registro completo.

## 1. Lista final (10 serviços)

| # | Id | Serviço | URL pedida | Página que carregou | `robots.txt` | No piloto |
|---|---|---|---|---|---|---|
| 1 | `govbr` | Portal gov.br | https://www.gov.br/pt-br | mesma URL | robots.txt com regras; caminho liberado | sim |
| 2 | `meuinss` | Meu INSS | https://meu.inss.gov.br/ | https://meu.inss.gov.br/#/login | HTTP 403 no robots.txt; pela RFC 9309, sem restrições | sim |
| 3 | `receita-ecac` | Receita Federal (e-CAC) | https://cav.receita.fazenda.gov.br/autenticacao/login | mesma URL | HTTP 200 com página HTML, sem regras válidas; liberado | não |
| 4 | `ctps-digital` | Carteira de Trabalho Digital (web) | https://servicos.mte.gov.br/spme-v2/ | https://servicos.mte.gov.br/spme-v2/#/login | HTTP 404 no robots.txt; sem restrições | não |
| 5 | `svr-bcb` | Valores a Receber (Banco Central) | https://www.bcb.gov.br/meubc/valores-a-receber?modalAberto=cuidado-com-golpes-modal | mesma URL | robots.txt com regras; caminho liberado | sim |
| 6 | `meususdigital` | Meu SUS Digital | https://meususdigital.saude.gov.br/ | https://meususdigital.saude.gov.br/login | HTTP 200 com página HTML, sem regras válidas; liberado | não |
| 7 | `portal-mg` | Portal MG (serviços do Governo de Minas) | https://www.mg.gov.br/ | mesma URL | robots.txt com regras; caminho liberado | não |
| 8 | `portal-servidor` | Portal do Servidor | https://www.gov.br/servidor/pt-br | mesma URL | robots.txt com regras; caminho liberado | não |
| 9 | `consumidor` | Consumidor.gov.br | https://www.consumidor.gov.br/ | https://www.consumidor.gov.br/pages/principal/?<número> (ver nota 1) | robots.txt com regras; caminho liberado | não |
| 10 | `enem-inep` | ENEM (Inep) | https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem | mesma URL | robots.txt com regras; caminho liberado | não |

Em 4 dos 10 serviços o `robots.txt` não traz regras válidas (Meu INSS, 403; Carteira de Trabalho Digital, 404; e-CAC e Meu SUS Digital, página HTML no lugar do arquivo). Pela RFC 9309, uma resposta 4xx quer dizer que não há restrições, e uma página sem regras não restringe nada. A verificação repete a requisição com o User-Agent do Lighthouse quando a primeira resposta não é 2xx.

Notas:

1. **Consumidor.gov.br.** A página inicial redireciona no cliente para `/pages/principal/?<número>`, em que o número muda a cada visita. O Lighthouse mede a página final, e a URL pedida continua a mesma. O redirecionamento está registrado como ameaça de construto ([`ameacas-validade.md`](ameacas-validade.md)).
2. **Páginas de login.** Meu INSS, Carteira de Trabalho Digital e Meu SUS Digital abrem a tela de login (`#/login` ou `/login`); o e-CAC é a própria URL de login. As medições são da tela anterior à autenticação, sem login e sem dados pessoais.
3. **Portal do Servidor.** Continua na lista sem número de uso verificável. Decidido em 25/11/2026: o serviço atende os critérios técnicos e éticos (`robots.txt` liberado, sem bloqueio), então fica, com a ressalva **NÃO ENCONTRADO** na seção 1.3 da proposta. Fica de fora do cálculo de impacto ([`impacto.md`](impacto.md)).
4. **Mesmo host.** Portal gov.br, Portal do Servidor e ENEM ficam em `www.gov.br` (plataforma Plone). São três páginas, mas menos independentes entre si do que parecem.

## 2. Candidatas trocadas

| Candidata | URL | Trocada por | Data | Motivo |
|---|---|---|---|---|
| Conecte SUS | https://conectesus-paciente.saude.gov.br/ | consumidor | 2026-11-17 | A URL redireciona para https://meususdigital.saude.gov.br/ (o Meu SUS Digital substituiu o Conecte SUS). Mantê-la mediria a mesma página duas vezes. |
| Detran-MG | https://www.detran.mg.gov.br/ | portal-mg | 2026-11-17 | O robots.txt (HTTP 200) tem "User-agent: *" + "Disallow: /" (só Googlebot e bedrockbot são liberados). Cópia mantida em data/robots/www.detran.mg.gov.br.txt. https://transito.mg.gov.br/ redireciona para o mesmo host. |
| Senatran - Portal de Serviços (considerado para substituir o Detran-MG) | https://portalservicos.senatran.serpro.gov.br/ | portal-mg | 2026-11-17 | A requisição do robots.txt não teve resposta HTTP (status 000 no curl), ou seja, inacessível; pela RFC 9309 assume-se proibição total, então não foi usado. |
| Portal da Transparência | https://portaldatransparencia.gov.br/ | svr-bcb | 2026-11-17 | O robots.txt libera "/", mas no piloto 4 de 6 execuções do Lighthouse receberam um CAPTCHA do AWS WAF ("Let's confirm you are human", documento principal com HTTP 202) em vez do portal. Só a primeira visita e uma visita depois receberam a página real. Contornar o CAPTCHA está fora do escopo, então o serviço não pode ser medido de forma confiável. Arquivos brutos mantidos em data/raw/pilot/transparencia_*.json. |
| IBGE (considerado para substituir o Portal da Transparência) | https://www.ibge.gov.br/ | svr-bcb | 2026-11-17 | A página inicial devolveu HTTP 403 a uma única requisição com curl e User-Agent de navegador (proteção anti-bot), então não foi usado. |

Todas as trocas foram feitas na Sprint 1 (17/11/2026), depois do piloto e da verificação do `robots.txt`. Na Sprint 2 (coleta completa de 25/11/2026) nenhum serviço foi trocado e nenhum bloqueio apareceu.

## 3. Efeito das trocas na amostra

Os serviços que bloqueiam acesso automatizado (Detran-MG, Senatran, Portal da Transparência, IBGE) saíram da amostra. Isso pode puxar a amostra para serviços sem proteção anti-bot, e o resultado vale para os serviços que podem ser medidos do jeito descrito aqui (validade externa, [`ameacas-validade.md`](ameacas-validade.md)).
