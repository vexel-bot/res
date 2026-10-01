# Auditoria de acessibilidade e rollout — 2026-08-29

## Acessibilidade automatizada

Foi criada uma suíte axe isolada em `tests/accessibility/critical-journeys.a11y.spec.ts`, executada por `npm run test:a11y`. Ela cobre as seis superfícies diretamente ligadas ao gate de first-click:

1. Início;
2. Criar;
3. Editar imagem;
4. Editar vídeo;
5. Revisar;
6. Publicar.

A primeira execução encontrou 57 nós em violações de contraste, alternativa de imagem, rótulo de campo, nome de botão, semântica interativa aninhada e tamanho de alvo. As correções foram feitas na origem em `CanonicalProduct`, `canonical.css`, `VideoStudio` e `video-studio.css`.

Resultado final: **6/6 superfícies sem violações axe** para as tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` e `wcag22aa`.

Essa prova automatizada não substitui a rodada manual por teclado e leitor de tela prevista no protocolo CX-0.

## Rollout e rollback

Todas as rotas com owner `canonical` agora recebem um contrato de rollout no registry:

- flag: `VITE_CANONICAL_CX_ROUTES`;
- estado padrão: canônico;
- rollback: owner `legacy` quando o valor é `false`;
- dados: nenhuma rota, versão ou documento é apagado durante a troca de owner.

O teste de contrato comprova owner canônico com a flag ativa, fallback legado com a flag desligada e ausência de efeito sobre rotas `product-surface`.

## Gate contratual descoberto

O inventário foi expandido para guardar `controlEvidence`, rótulo inferido, escopo contratual, Action ID literal/dinâmico e a lista completa de executáveis sem ID. O modo `npm run audit:cx-strict` também rejeita IDs literais não registrados.

Estado atual:

- 360 controles executáveis no escopo contratual canônico;
- 71 controles com atributo de Action ID no inventário total;
- 290 controles executáveis ainda sem Action ID;
- zero IDs literais usados sem Action Contract registrado.

A meta permanece aberta até essa fila chegar a zero e o CX-0 humano ser executado.
