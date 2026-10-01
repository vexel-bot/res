# Evidência — slice CX Vídeo assistido — 2026-08-28

## Resultado

O fluxo canônico `Editorial → Video Studio → Review` agora possui contratos executáveis, controles funcionais, persistência não destrutiva, job observável, recuperação após reload e handoff para a revisão exata. O slice preserva o Studio Kernel e os adapters existentes; nenhum provider foi incorporado ao domínio.

## Contratos e navegação

- `SCREEN-VIDEO` resolve `/content/:contentId/edit?mode=video` no shell `studio`.
- A ação primária é `VIDEO-RENDER-PREVIEW`, do tipo `JOB` e persistência `job`.
- Upload, proxy, waveform, captions, corte, checkpoint, refresh/cancel/retry e review possuem Action Contracts estáveis.
- `EDITORIAL-OPEN-VIDEO` preserva a identidade do conteúdo na troca de modo.
- `VIDEO-SEND-REVIEW` só habilita depois de render bem-sucedido, revisão/versão correspondentes e QC técnico aprovado; em sucesso navega para `/approvals/:contentId?view=creative`.

## Pipeline comprovado

1. upload privado e original imutável;
2. probe técnico;
3. proxy de edição e time-map;
4. waveform do áudio original;
5. CreativeDocument com timeline frame-exact;
6. transcript/captions editáveis;
7. corte e reorder/trim não destrutivos;
8. render FFmpeg 1080×1920 H.264/AAC em job observável;
9. QC técnico ligado ao artefato;
10. reload recupera o último job `video_render`, o Blob privado e o gate de revisão;
11. review referencia job, asset, checksum, revisão e versão exatos.

## Estados honestos, acessibilidade e telemetria

- O vazio orienta o próximo passo e explicita a preservação do original.
- Fila, execução, cancelamento, falha, retry, QC e erro de segurança são visíveis; o card do job usa região viva.
- Custo não é inventado: a UI declara `Não medido neste worker`.
- Controles antes decorativos de Composição, Ajustar, corte e importação agora abrem ações reais.
- Player, tabs, playhead, clips, reorder e trim têm nomes/estado/alternativas de teclado.
- Ações canônicas emitem `clicko:experience` por uma fronteira provider-neutral; E2E prova `VIDEO-APPLY-CUT` e `VIDEO-RENDER-PREVIEW`.
- O layout foi validado em 1440×1000 e 390×844 sem overflow horizontal.

## Evidência executável

- `npm run lint` — aprovado.
- `npm run test:cx-contracts` — 6/6 aprovado, incluindo resolução de `SCREEN-VIDEO` e validação do grafo.
- `npm run audit:cx` — 43 rotas, 59 URLs conhecidas, zero órfãs e zero conflitos; 28 controles com Action ID.
- `python -m pytest tests/test_video_render_job.py -q` em `backend/` — aprovado; inclui listagem filtrada e isolamento entre workspaces.
- Playwright guest/mobile — aprovado; laboratório, não destrutividade, telemetria e responsividade.
- Playwright autenticado — aprovado; MP4 real percorre upload, proxy, waveform, captions, corte, timeline, render, QC, reload/recovery e review versionado.

## Limites deliberados

- OpenCut permanece referência de UX/componentes, não store nem núcleo do produto.
- O provider de render continua atrás do contrato existente.
- ASR real, múltiplos assets, undo/redo, volume/fades, transições avançadas, thumbnails, custo medido e rollout externo permanecem incrementos posteriores; nenhum deles é anunciado como disponível.
