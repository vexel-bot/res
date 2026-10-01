# Auditoria vertical — Carrossel, Reuse e Fábrica

Data: 30/08/2026  
Status: corte técnico aprovado; validação humana e concorrência forte ainda pendentes

## Decisão

O handoff `Carrossel/Conteúdo publicado → Reuse → Fábrica → revisão em lote` deixou de depender de
estado efêmero do navegador. As derivações recebem identidade de formato e lineage persistente; um
reload recompõe a seleção; a rodada da Fábrica recebe identidade determinística a partir de
`workspaceId`, conteúdo de origem e conjunto ordenado de derivações.

Repetir o início com as mesmas entradas recupera a rodada já existente antes de criar documento,
versão ou job. O teste autenticado compara IDs de jobs e números de versão antes/depois da repetição.

## Verdade de dados e interface

- Reuse não inventa imagem, campanha, data, métrica, racional ou performance da origem.
- Métricas do conteúdo pai não são copiadas para os filhos.
- `derivationKey`, hipótese, campos preservados e campos adaptados são gravados no lineage.
- A Fábrica autenticada usa somente origem, campanha, objetivo, lineage, destinos, documentos,
  versões, jobs e erros observados no workspace.
- Os cards autenticados não usam arte arbitrária como se fosse preview gerado.
- As alegações demonstrativas (`3×`, `92%`, capacidade e peças prontas) ficam restritas ao modo demo.
- O CTA de lote só habilita quando há documento e versão fixa elegíveis; publicação continua humana.

## Idempotência comprovada

Identidade canônica:

```text
SHA-256({ workspaceId, sourcePostId, sort(unique(derivativeIds)) })[0:32]
```

O backend já garante unicidade de `WorkspaceResource(workspace, kind, resourceKey)`, documento do
Studio por `workspace/post/contentType` e job por chave de idempotência. O frontend agora consulta a
rodada determinística antes de qualquer efeito colateral.

A prova cobre repetição sequencial após navegação/reload. Ela não prova duas abas iniciando no mesmo
milissegundo. Idempotência concorrente forte exigirá uma operação transacional de reserva/orquestração
no backend antes de considerar essa condição encerrada.

## Inventário de controles

O auditor passou a contar também `input`, `select` e `textarea`, não apenas botões. Todos os 37 campos
canônicos descobertos receberam Action Contract. Baseline estrito atual:

- 45 entradas no route registry e 59 URLs conhecidas;
- zero rotas órfãs ou com owner conflitante;
- 906 controles renderizados;
- 809 wired, 7 submit e 72 disabled com motivo;
- zero disabled sem motivo;
- 413 controles executáveis no escopo canônico;
- zero executáveis sem `data-action-id`;
- 250 Action Contracts cobertos, sem ID ausente ou não registrado.

Baseline: `CX_ROUTE_ACTION_BASELINE.json`.

## Responsividade e acessibilidade

O E2E em `390 × 844` percorre Reuse e Fábrica, identifica o scroll owner efetivo e alcança a ação
primária em ambas. A suíte Axe passou a incluir as duas superfícies. Contrastes de cards indisponíveis,
rodapé da Fábrica e botões bloqueados foram corrigidos sem ocultar elementos do auditor.

Resultado WCAG automatizado: 8/8 superfícies críticas sem violações A/AA detectáveis. Isso não
substitui navegação manual por teclado, leitor de tela nem teste com pessoas.

## Provas executadas

- `npm run lint` — passou;
- `npm run build` — passou; permanece apenas o aviso conhecido de chunk acima de 500 kB;
- `npm run test:cx-contracts` — 6/6;
- `npm run audit:cx-strict` — passou com zero lacunas no escopo canônico;
- `pytest tests/test_history_learning.py tests/test_workspace_features.py -q` — 9/9;
- E2E focado de lineage/reload/idempotência, mobile e Visual/Carrossel autenticado — 3/3;
- suíte Axe crítica completa — 8/8.

## Limites e próximos gates

Este checkpoint não declara a meta concluída. Permanecem:

1. idempotência concorrente transacional da Fábrica entre clientes;
2. atualização/polling do estado corrente de cada job e retry auditável por célula;
3. teste humano CX-0 e evidência manual de teclado/leitor de tela;
4. aquisição de takes/avatar e foley/ambiência com direitos para os dez UGC sem voz;
5. sincronização posterior com Figma somente quando o MCP estiver disponível e solicitada.

Voicebox, TTS, clonagem, narração, fala incidental, música e lip-sync continuam fora do perfil UGC
vigente. Nenhuma VPS, serviço remoto ou configuração externa foi alterada neste corte.
