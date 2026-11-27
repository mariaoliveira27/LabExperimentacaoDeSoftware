# Validação dos dados da coleta completa

Gerado por `scripts/validate-data.mjs --phase full` em 2026-11-27T00:04:06+00:00. Não edite à mão: rode o script de novo.

Plano: `data/raw/full/plan.json`, seed 3118576651, 10 execuções por serviço e form factor em 2 blocos, 200 execuções esperadas.

## Resumo

| Item | Valor |
|---|---|
| Execuções esperadas | 200 |
| Linhas válidas em `full.csv` | 200 |
| Execuções sem linha válida | 0 |
| Tentativas registradas em `run-metadata.json` | 205 (ok: 202, missing-values: 3) |
| Linhas em `data/failed-runs.csv` desta fase | 5 |
| Brutos inválidos ainda na pasta (`full_failures.csv`) | 0 |
| Erros | **0** |
| Avisos | 0 |
| Valores fora da cerca de Tukey (marcados, não removidos) | 105 em 60 execuções |
| Pausa entre tentativas (mín. / mediana) | 10,001 s / 10,011 s |

## Sessões

| Sessão | Rótulo | Início (UTC) | Fim (UTC) | Tentativas com horário |
|---|---|---|---|---|
| full-2026-11-25T113828-0300 | morning | 2026-11-25T14:38:33.424Z | 2026-11-25T15:14:22.952Z | 100 |
| full-2026-11-25T150107-0300 | afternoon | 2026-11-25T18:01:13.501Z | 2026-11-25T18:39:05.479Z | 105 |

## Execuções válidas por serviço × form factor × horário

| Serviço | Form factor | afternoon | morning | Total | Esperado |
|---|---|---|---|---|---|
| govbr | mobile | 5 | 5 | 10 | 10 |
| govbr | desktop | 5 | 5 | 10 | 10 |
| meuinss | mobile | 5 | 5 | 10 | 10 |
| meuinss | desktop | 5 | 5 | 10 | 10 |
| receita-ecac | mobile | 5 | 5 | 10 | 10 |
| receita-ecac | desktop | 5 | 5 | 10 | 10 |
| ctps-digital | mobile | 5 | 5 | 10 | 10 |
| ctps-digital | desktop | 5 | 5 | 10 | 10 |
| svr-bcb | mobile | 5 | 5 | 10 | 10 |
| svr-bcb | desktop | 5 | 5 | 10 | 10 |
| meususdigital | mobile | 5 | 5 | 10 | 10 |
| meususdigital | desktop | 5 | 5 | 10 | 10 |
| portal-mg | mobile | 5 | 5 | 10 | 10 |
| portal-mg | desktop | 5 | 5 | 10 | 10 |
| portal-servidor | mobile | 5 | 5 | 10 | 10 |
| portal-servidor | desktop | 5 | 5 | 10 | 10 |
| consumidor | mobile | 6 | 4 | 10 | 10 |
| consumidor | desktop | 6 | 4 | 10 | 10 |
| enem-inep | mobile | 5 | 5 | 10 | 10 |
| enem-inep | desktop | 5 | 5 | 10 | 10 |

## Erros

Nenhum.

## Avisos

Nenhum.

## Tentativas que falharam (`data/failed-runs.csv`)

| Sessão | Rótulo | Execução | Status | Código | Motivo |
|---|---|---|---|---|---|
| full-2026-11-25T113828-0300 | morning | consumidor_mobile_2 | invalid-found-on-resume | MISSING_VALUES | MISSING_VALUES: valor(es) nulo(s): performanceScore, LCP, FCP, TBT, SpeedIndex |
| full-2026-11-25T113828-0300 | morning | consumidor_desktop_2 | invalid-found-on-resume | MISSING_VALUES | MISSING_VALUES: valor(es) nulo(s): performanceScore, LCP, FCP, TBT, SpeedIndex |
| full-2026-11-25T150107-0300 | afternoon | consumidor_desktop_2 | missing-values | MISSING_VALUES | valor(es) nulo(s): performanceScore, LCP, FCP, TBT, SpeedIndex; The page did not paint any content. Please ensure you keep the browser window in the foreground  |
| full-2026-11-25T150107-0300 | afternoon | consumidor_desktop_8 | missing-values | MISSING_VALUES | valor(es) nulo(s): performanceScore, LCP, FCP, TBT, SpeedIndex; The page did not paint any content. Please ensure you keep the browser window in the foreground  |
| full-2026-11-25T150107-0300 | afternoon | consumidor_desktop_9 | missing-values | MISSING_VALUES | valor(es) nulo(s): performanceScore, LCP, FCP, TBT, SpeedIndex; The page did not paint any content. Please ensure you keep the browser window in the foreground  |

## Marcações de revisão (`full_flags.csv`)

- `BENCHMARK_LOW_OUTLIER`: 2 (consumidor_mobile_5, ctps-digital_mobile_3)

## Outliers (regra de Tukey)

Regra: dentro de cada serviço × form factor, um valor é outlier se fica abaixo de Q1 − 1.5 × IQR ou acima de Q3 + 1.5 × IQR (quantis com interpolação linear). As execuções **não são removidas**: a análise roda com todas as execuções e de novo sem as marcadas (ver `analysis/results.md`). Lista completa em `data/processed/full_outliers.csv`.

| Serviço | Form factor | Métrica | Runs (valor) | Cercas |
|---|---|---|---|---|
| consumidor | desktop | FCP | 1 (1693.8), 9 (1432.3) | 1199.475 a 1363.475 |
| consumidor | desktop | performanceScore | 1 (74) | 43.125 a 70.125 |
| consumidor | desktop | SpeedIndex | 9 (2623.9) | 782.8375 a 2125.7375 |
| consumidor | desktop | TBT | 1 (233.9) | 366.65 a 1066.45 |
| consumidor | mobile | CLS | 2 (0.0154), 3 (0.0154) | 0 a 0 |
| consumidor | mobile | LCP | 10 (11969.5) | 4209.7375 a 10743.4375 |
| ctps-digital | desktop | CLS | 1 (0.0157), 3 (0.2039), 9 (0.0157) | 0.1542 a 0.1986 |
| ctps-digital | desktop | LCP | 6 (1356.2), 9 (1119.1), 10 (1353.7) | 1250.2125 a 1331.5125 |
| ctps-digital | desktop | performanceScore | 1 (95), 9 (97) | 85.5 a 89.5 |
| ctps-digital | mobile | CLS | 8 (0.2372) | 0 a 0 |
| ctps-digital | mobile | FCP | 1 (4599.7), 8 (1669.8), 10 (4330.9) | 4264.3875 a 4310.0875 |
| ctps-digital | mobile | LCP | 8 (7058.8), 10 (6880.9) | 6813.7375 a 6868.8375 |
| ctps-digital | mobile | SpeedIndex | 1 (4599.7), 8 (3166.4), 10 (4330.9) | 4264.3875 a 4310.0875 |
| enem-inep | desktop | FCP | 5 (1345.4) | 1099.8 a 1341.4 |
| enem-inep | mobile | CLS | 6 (0.0007) | 0 a 0 |
| enem-inep | mobile | FCP | 2 (6737.1), 3 (6831.2) | 5548.725 a 5927.925 |
| enem-inep | mobile | LCP | 4 (32959.3), 7 (31900.5) | 9059.1125 a 18991.4125 |
| enem-inep | mobile | performanceScore | 3 (54) | 54.625 a 61.625 |
| enem-inep | mobile | TBT | 3 (213) | -2.3125 a 127.1875 |
| govbr | desktop | CLS | 1 (0.0378), 4 (0.042), 5 (0.0785) | 0.0692 a 0.0735 |
| govbr | desktop | LCP | 5 (5505.6), 9 (4674.9) | 4812.6625 a 5237.7625 |
| govbr | desktop | performanceScore | 4 (67), 5 (63) | 67.5 a 71.5 |
| govbr | desktop | SpeedIndex | 5 (2772.1) | 1360.0125 a 2377.9125 |
| govbr | desktop | TBT | 1 (5), 5 (42) | -2.25 a 3.75 |
| govbr | mobile | CLS | 5 (0.1154) | -0.0014 a 0.0024 |
| govbr | mobile | LCP | 8 (28345.9), 9 (26355.9) | 29170.3125 a 30457.4125 |
| govbr | mobile | performanceScore | 8 (47) | 52.75 a 62.75 |
| govbr | mobile | SpeedIndex | 8 (28180.9) | 4888.0875 a 7574.9875 |
| govbr | mobile | TBT | 8 (340) | 64 a 250 |
| meuinss | desktop | CLS | 1 (0.3792), 2 (0.7765), 4 (0.7764), 10 (0.2048) | 0.4168 a 0.7681 |
| meuinss | desktop | FCP | 7 (1147.9) | 1152.275 a 1221.075 |
| meuinss | desktop | LCP | 2 (3444.9), 3 (2905.7), 8 (2870.7), 10 (8307.2) | 2999.7625 a 3338.6625 |
| meuinss | mobile | CLS | 6 (0.3592) | 0.6164 a 0.6164 |
| meuinss | mobile | FCP | 2 (5961.8), 3 (6108.9), 8 (5975) | 5995.2625 a 6073.5625 |
| meuinss | mobile | LCP | 6 (26991.4) | 12381.925 a 18091.125 |
| meuinss | mobile | SpeedIndex | 5 (9472.8), 6 (9242.7) | 6658.4875 a 8965.7875 |
| meususdigital | desktop | CLS | 1 (0) | 0.2222 a 0.2222 |
| meususdigital | desktop | FCP | 5 (4043.8) | 3525.5 a 3996.1 |
| meususdigital | desktop | performanceScore | 1 (28) | 13.5 a 17.5 |
| meususdigital | mobile | LCP | 1 (32257.7), 2 (31728.8), 3 (35939.3) | 32373.3875 a 35491.4875 |
| portal-mg | desktop | CLS | 9 (0.0652) | 0.0754 a 0.0867 |
| portal-mg | desktop | LCP | 7 (2871.7), 9 (2853.4) | 2719.225 a 2841.425 |
| portal-mg | desktop | performanceScore | 4 (71) | 77.5 a 81.5 |
| portal-mg | desktop | SpeedIndex | 4 (5654.2) | 1161.175 a 1378.575 |
| portal-mg | desktop | TBT | 7 (7) | 0 a 0 |
| portal-mg | mobile | accessibilityScore | 2 (96) | 100 a 100 |
| portal-mg | mobile | CLS | 2 (0.1669) | 0.0077 a 0.0196 |
| portal-mg | mobile | FCP | 2 (4373.9), 10 (6159.8) | 6305.2 a 6314.4 |
| portal-mg | mobile | LCP | 2 (13241.8) | 12520.6 a 12843 |
| portal-mg | mobile | performanceScore | 2 (40) | 45.875 a 58.875 |
| portal-mg | mobile | SpeedIndex | 1 (6308.2), 2 (11106.5), 10 (6159.8) | 6308.3125 a 6313.0125 |
| portal-servidor | desktop | performanceScore | 1 (71), 9 (76) | 71.5 a 75.5 |
| portal-servidor | mobile | LCP | 2 (30875.4), 3 (17475.2), 5 (17078.5) | 19673.5875 a 24795.0875 |
| portal-servidor | mobile | TBT | 3 (199) | 3.5 a 175.5 |
| receita-ecac | desktop | FCP | 7 (26558.9) | 344.325 a 1517.925 |
| receita-ecac | desktop | LCP | 7 (26558.9) | 344.325 a 1517.925 |
| receita-ecac | desktop | performanceScore | 7 (55) | 91.5 a 103.5 |
| receita-ecac | desktop | SpeedIndex | 7 (27005.5) | 396.8875 a 1486.3875 |
| receita-ecac | mobile | CLS | 7 (0) | 0.0097 a 0.0097 |
| receita-ecac | mobile | LCP | 7 (3696.8) | 6029.5125 a 6246.8125 |
| receita-ecac | mobile | performanceScore | 7 (88) | 74.5 a 78.5 |
| receita-ecac | mobile | TBT | 1 (8), 7 (10) | 0 a 0 |
| svr-bcb | desktop | LCP | 10 (5633.6) | 5645.6 a 6199.4 |
| svr-bcb | mobile | CLS | 1 (1.066) | 0.9657 a 0.9908 |
| svr-bcb | mobile | performanceScore | 1 (2), 2 (2) | 1 a 1 |
