# Clicko — redesign e simplificação dos Studios

**Entrega local de 24/10/2026.** Inventário iniciado em 23/10 antes das mudanças.
Base Git: `946397d04061952104f5e25319ea2c0bcf05958b`, preservada. Sem commit,
push, deploy, dependência nova, serviço contratado ou chamada paga nesta etapa.
Nenhuma alteração de backend, credencial, modelo Gemini, voz ou regra comercial.

**Resultado:** reorganização implementada e fluxos principais locais validados
no navegador DEV, além das regressões técnicas. Não é homologação de geração
por IA, motores Craft, áudio externo ou operação comercial em produção.

## 1. Problemas da interface anterior

Cabeçalhos/abas redundantes consumiam altura; comandos, biblioteca e histórico
competiam com o canvas; propriedades permanentes expunham dezenas de campos;
timeline e exportação exigiam rolagem geral. Formulários completos apareciam
antes de uma primeira ação clara. O inventário funcional está em
[`UX_INVENTORY_2026-10-23.md`](docs/studios/UX_INVENTORY_2026-10-23.md).

As capturas anteriores disponíveis são históricas, de **22/10**, não uma
recriação: [Motion anterior](.codex-runtime/clicko-dev/dev-motion-ui.png) e
[Imagem anterior](.codex-runtime/clicko-dev/dev-image-ui.png). A primeira mostra
o canvas e propriedades numa página longa, sem timeline simultânea na janela.

## 2. Nova navegação

Uma barra Studios / ferramenta atual e o seletor agrupado **Alterar Studio**
substituem categorias e subabas simultâneas. As nove rotas, aliases, permissões,
foco, histórico do navegador e opções futuras continuam. Não foi criada licença
“Studios” nem concedido acesso cruzado a Imagem/Vídeo.

## 3. Funcionalidades reorganizadas

Criar/importar iniciam o trabalho; salvar/exportar ficam na barra; materiais e
camadas à esquerda; prévia no centro; propriedades apenas com seleção; timeline
inferior com scroll próprio. Projetos, versões, produção, modelos, planos,
recibos, recuperação e saída ficam em painéis sob demanda. Erros, cotas,
consentimento e operações incertas não foram escondidos.

## 4. Componentes e implementação reaproveitados

Reutilizados `ProductDataProvider`, governança, `productApi`, `localApi`,
`canonicalTimeline`, renderização FFmpeg, `LocalLayerControls`, versões,
`useCraftStudio`, `ClickoSelectMenu`, Biblioteca e conversa global KLIC.
Novos componentes de UI: `StudioEditorFrame`, `StudioUtilityPanel`,
`StudioKlicButton`, `useStudioShortcuts` e `LocalInspector`.

Grupos principais alterados: `src/studios/shared/*`, `StudiosWorkspace.tsx`,
`ClickoStudioView.tsx`, `local/*`, `video/*` e `image/*`; runner de testes,
smoke DEV e documentação. Arquitetura detalhada em
[`UX_ARCHITECTURE_2026-10-24.md`](docs/studios/UX_ARCHITECTURE_2026-10-24.md).

## 5. Melhorias de usabilidade

Defaults locais revisáveis; projeto manual em branco sem IA; seleção do canvas
respeita letterboxing; Ctrl/Cmd+S e undo/redo fora de campos de texto; estado
salvo explícito; Escape/foco em painéis; alternativa numérica ao arrastar;
troca de faixa acessível; proteção da montagem não salva ao abrir outro projeto.

O QA detectou e corrigiu: classe nova confundida com progresso pelo CSS global,
transição de briefing para editor antes do término do guard de salvamento,
cabeçalho de vídeo excessivo no notebook e cálculo de altura quando avisos ou
controles alteram a posição do editor sem resize da janela.

## 6. Motion Design

Editor integrado com barra, camadas/materiais, canvas, inspector e timeline
redimensionável. Cenas, start/duration, presets, tipografia, sombra, gradiente e
editor completo de keyframes permanecem. O acesso a recursos nativos esclarece
dependências/formato, sem alegar 3D ou runtime instalado.

No navegador foi criado **QA UX · Motion · 24-10**, adicionado/alterado texto,
salvo por atalho, verificado undo/redo (64 → 72), recuperada versão anterior
(72 → 64), redimensionada timeline por teclado e exportado MP4 real de 12 s.
O projeto foi reaberto posteriormente com revisão e texto preservados.

## 7. Video Studio

Briefing inicial reduzido; nome, direção e roteiro sob demanda. Editor canônico
reutiliza exatamente o `mediaTimeline` existente, agora com layout integrado e
inspector contextual. Cortes, áudio, efeitos/transições existentes, títulos,
keyframes, histórico de edição, render/cancel/retry e recuperação permanecem.

Projetos/novo projeto/ajuda foram recolhidos sem duplicar a barra do editor.
No notebook 1190×668 a página cabe na janela; a prévia não fica reduzida à barra
do player. A timeline pode ser diminuída para ampliar o monitor.

Na montagem de QA: duração ajustada para 3 s, keyframes aplicados/limpos, título
adicionado, documento salvo e MP4 renderizado. HTML5 confirmou duração 3 s,
`readyState=4`, reprodução e avanço do cursor. A seleção móvel abre Propriedades.

## 8. Image Studio

Criação prioriza descrição, enquadramento e estilo; campos técnicos, referências
e marca recolhidos. A edição manual usa canvas/camadas/inspector/histórico e
exportação. Originais, crop, ajustes, texto, formas, editor nativo e editorial
continuam disponíveis. Provedor indisponível não retorna imagem simulada.

No navegador: **QA UX · Imagem · 24-10**, importação real de `source-card.png`,
crop de 10%, contraste 1,05, salvamento e confirmação de PNG exportado. O smoke
real também comprovou PNG vertical 720×1280 e checksum do original inalterado.

## 9. Publicidade

Produto/oferta, público e resultado são as três perguntas centrais. Benefício,
CTA e roteiro ficam opcionais. Materiais existentes alimentam o mesmo editor.
Foi criado um anúncio de QA com imagem da Biblioteca, aberto no editor canônico,
editado e renderizado sem publicar campanha. Criativos visuais usam o mesmo
Image Studio; público/objetivo são campos opcionais no briefing existente,
compatíveis com rascunhos antigos. Nada simula compra de mídia/publicação.

## 10. KLIC

Botão discreto abre **a conversa global existente** em modo/contexto de produção
local. O painel foi aberto/fechado pelo navegador; mensagem/voz não foram
acionadas para evitar chamadas externas. Não foram criados chats por Studio,
nem alterados Gemini, voz ou credenciais. Comandos manuais são independentes.
Testes Python preservam roteamento, revisão, escopo da seleção e idempotência.

## 11. Testes executados

| Verificação | Resultado / natureza da evidência |
|---|---|
| `npm test` | 262 Node/SSR + 2 isolamento Vite = **264 aprovados**, zero falhas |
| `npm run lint` | TypeScript (`tsc --noEmit`) aprovado; não equivale a lint Python global |
| `npm run build` | Vite + servidor/workers aprovados |
| Controles/reset DEV e estado Craft | **4 + 7 aprovados** complementares |
| Python pertinente | **37 aprovados**, sem falhas/erros/pulados |
| Smoke sessão DEV real | Importar, criar, salvar, PNG, MP4, versões e original preservado |
| Arquivos do smoke | PNG 720×1280; MP4 2 s, 640×360, 24 fps, H.264/AAC; decode completo FFmpeg aprovado |
| Browser Motion | Criar, editar, seleção canvas/lista, atalhos, versões, timeline, export MP4 e reabertura |
| Browser imagem | Importar, selecionar, crop/contraste, salvar, export PNG e menus de criação |
| Browser vídeo/publicidade | Três perguntas, Biblioteca, mesmo editor, duração/título/keyframes, salvar/render/playback |
| Responsividade | 1440×900, 1190×668, 820×900 e 390×844; painéis por etapa, sem overflow horizontal da página nos editores verificados |
| Temas | Motion, imagem e vídeo inspecionados no claro e escuro; preferência restaurada ao escuro |
| KLIC | Painel global/contexto aberto e fechado; sem inferência ou voz externas |
| Git / DEV | `diff --check`, HEAD preservado, perfil loopback pronto; sem push/deploy |

Python: `test_image_frontend_contract.py`, `test_video_frontend_contract.py`,
`test_local_agent_stage2.py`, `test_stage2_completion.py`,
`test_stage3_homologation.py` e `test_stage3_shared_media.py`.
Testes unitários/SSR não foram confundidos com ações reais do navegador.

Logs privados: `.codex-runtime/studios-ux-{node-final,types,build-final,python,
control,craft-state,live,media,persistence}.log` e JUnit `studios-ux-python.xml`.
Smoke: `scripts/audits/studios-ux-live.ts`; evidência em
`.codex-runtime/studios-ux/evidence.json`. São dados próprios isolados DEV.
O registro do QA visual está em `.codex-runtime/studios-ux/browser-evidence.json`;
a última inspeção do console da aba não registrou erros. A tentativa de sair com
opacidade não salva foi bloqueada; a mudança de QA foi desfeita e salva antes da
navegação. A prévia final permanece aberta no Motion.

## 12. Resultados e capturas reais

Comparação: os editores antes exigiam scroll geral; agora prévia, materiais e
timeline ficam na janela, com propriedades e listas rolando internamente.
Criação tem rolagem normal de formulário quando necessária, não a restrição
artificial de um editor. Móvel alterna painéis do mesmo projeto.

Capturas de 24/10, privadas e não publicadas no GitHub:

- [Motion escuro](.codex-runtime/studios-ux/screenshots/motion-desktop-dark.jpg)
  e [Motion claro](.codex-runtime/studios-ux/screenshots/motion-desktop-light.jpg).
- [Prévia funcional final](.codex-runtime/studios-ux/screenshots/motion-final-preview.jpg).
- [MP4 no notebook](.codex-runtime/studios-ux/screenshots/motion-export-notebook.jpg),
  [tablet](.codex-runtime/studios-ux/screenshots/motion-tablet.jpg) e
  [timeline móvel](.codex-runtime/studios-ux/screenshots/motion-mobile-timeline.jpg).
- [Imagem/crop/export](.codex-runtime/studios-ux/screenshots/image-export-desktop.jpg),
  [editor claro](.codex-runtime/studios-ux/screenshots/image-editor-light.jpg) e
  [criação clara corrigida](.codex-runtime/studios-ux/screenshots/image-create-light.jpg).
- [Briefing de anúncio](.codex-runtime/studios-ux/screenshots/advertising-brief-light.jpg),
  [vídeo notebook](.codex-runtime/studios-ux/screenshots/video-notebook-light.jpg) e
  [propriedades móveis](.codex-runtime/studios-ux/screenshots/video-mobile-properties.jpg).

## 13. Pendências e limites

- Geração real por IA, qualidade artística, Gemini/TTS/voz externos e os
  binários/WASM Craft continuam dependentes da infraestrutura já apontada na
  auditoria anterior; não foram habilitados nem simulados por este redesign.
- QA responsivo foi no navegador com viewport ajustado, não em hardware móvel
  físico; gestos multitoque, todos os codecs e cada combinação possível de
  efeitos não estão homologados. Não foi prometido número de FPS sem medição.
- Nenhuma validação comercial de produção, rede adversa ou concorrência humana
  completa foi executada. Recuperação/idempotência têm regressões técnicas.
- A suíte Python global da auditoria de 23/10 tinha **888 aprovados, 277 falhas
  e 112 pulados**, Ruff global 323 achados e npm audit 1 alta. Esta etapa rodou o
  subconjunto pertinente, não declara essa dívida global resolvida.
- Prévia local não equivale a export final com vídeo/áudio; a montagem mantém
  renderização real e identificação de revisão. Composição local e formatos
  nativos continuam distintos, sem conversão silenciosa.

O redesign e a validação dos fluxos locais descritos estão entregues. Recursos
externos/experimentais não foram transformados em promessas de funcionamento.
As alterações permanecem no checkout para revisão, sem envio ao GitHub.
