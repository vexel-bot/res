# Auditoria de honestidade dos controles — 2026-08-29

## Resultado

A superfície canônica e as telas de compatibilidade foram endurecidas para que nenhum controle pareça acionável sem produzir consequência. O auditor agora classifica handlers JSX, submissões nativas e estados desabilitados com razão verificável, além de falhar quando encontra um controle desabilitado sem explicação.

Resultado de `npm run audit:cx`:

- 753 controles inspecionados;
- 672 com ação conectada;
- 7 submissões nativas;
- 74 desabilitados com razão explícita;
- zero desabilitados sem razão;
- zero pendentes de revisão;
- 363 com atributo de Action ID, sendo 357 literais e 6 dinâmicos;
- 362 executáveis no escopo contratual canônico;
- zero sem Action ID no escopo contratual estrito;
- 45 registros, 59 URLs, zero issues de registry, zero URLs órfãs e zero owners conflitantes.

## Regras aplicadas

1. Qualquer propriedade JSX `onX` é tratada como ação conectada.
2. Controles de submissão são classificados separadamente.
3. `disabled` e `aria-disabled` exigem `title`, `aria-describedby` ou `data-disabled-reason`.
4. O componente canônico `Button` fica desabilitado por padrão quando não recebe ação nem é do tipo `submit`, expondo o motivo de indisponibilidade.
5. A auditoria encerra com erro se houver controle desabilitado sem razão.
6. A interface usa texto e componentes gráficos, sem emojis como ícones, marcadores, status ou decoração.

O comando `npm run audit:cx-strict` é bloqueante para `actionId`: além de exigir IDs, valida que todo ID literal usado possui Action Contract registrado. A auditoria está verde e publica a prova completa em `CX_ROUTE_ACTION_BASELINE.json`.

## Verificações correlatas

- `npm run lint`: aprovado;
- `npm run test:cx-contracts`: 6/6;
- `npm run test:a11y`: 6/6 superfícies críticas sem violações axe A/AA;
- `npm run build`: aprovado, com warning não bloqueante de tamanho de chunk;
- `npm run test:e2e`: 27/27 em 1,4 min;
- varredura das faixas Unicode pictográficas em `src/canonical`, `src/studios` e `src/app`: zero ocorrências.

## Limite desta evidência

Esta auditoria prova consistência técnica, honestidade de estado e cobertura contratual completa dos controles executáveis. Ela não substitui a validação moderada CX-0 com 10 participantes reais definida em `docs/studios/CX_USER_VALIDATION_PROTOCOL_2026-08-29.md`.
