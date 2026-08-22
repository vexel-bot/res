# ADR 0001 — Rotas e manifesto das telas do Stitch

Status: aceito em 2026-08-15.

## Decisão

O produto usa rotas reais via History API e mantém `STITCH_SCREENS` como matriz executável das 57 referências válidas. As 38 telas finais e as 19 telas do Creative Lab compartilham shells e editores quando representam estados do mesmo fluxo. O projeto “Creative OS Redesign v1” é explicitamente excluído.

## Consequências

- Deep links e reload preservam a superfície atual.
- Frames de overlay e estados de canvas usam query strings, evitando editores duplicados.
- `npm run test:stitch` bloqueia contagem incorreta, IDs duplicados e o retorno da paleta verde legada.

