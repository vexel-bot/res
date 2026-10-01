# Video Studio — som externo editável e renderizado

Data: 31/08/2026. Workspace de código: `C:\Users\edugu\Downloads\res`.

## Resultado

A aba **Sons** permite enviar WAV/MP3/FLAC privados de até 20 MB, declarar origem,
autoria e licença, escolher início no vídeo/início no arquivo/duração/ganho/fade e
aplicar uma track canônica de som candidato. Reabrir a peça recupera esses dados;
ajustar o som já associado não cria novo upload. A faixa da timeline abre a aba.

O player do take continua sendo preview de montagem, sem mix externo ao vivo. A
interface explica isso; o player de MP4 em Saída reproduz o resultado efetivamente
renderizado. Uma prova antiga é identificada quando não serve à revisão atual.
Nenhuma voz, síntese, clonagem, música ou novo modelo foi ativado.

## Corte arquitetural e compatibilidade

| Antes | Agora | Persistência/risco | Verificação |
| --- | --- | --- | --- |
| Upload aceitava áudio, ingestão somente vídeo | Mesmo endpoint/job de ingestão aceita áudio-only | Sem segunda fila/tabela; worker continua responsável pelo probe | Arquivo WAV real, replay do mesmo ingest e tenant estrangeiro |
| Renderer limitado ao som pareado do take | Um vídeo, som original opcional e fontes externas independentes | Mesmo VideoRenderProvider; contratos AudioClipV1 existentes | MP4 decodificado, intervalos e RMS |
| Som natural fora do editor | Aba Sons, posição/offset/duração/ganho/fades | PUT revisionado no CreativeDocument; origem/licença declaradas não aprovam | Reload e edição sem duplicar asset |
| Fonte original requerida com áudio | Take sem áudio pode receber som externo | Ausência de original não implica ler stream inexistente | Render real de vídeo com `-an` |
| Trim podia deixar fades maiores que o trecho | Fades limitados ao intervalo resultante | Mesmo remapeamento no frontend e no serviço de cortes | Teste de timeline e regressão dos edit decisions |

Arquivos principais: `src/studios/NaturalSoundPanel.tsx`,
`src/studios/naturalSoundTimeline.ts`, `useVideoStudio.ts`, `VideoStudio.tsx`,
`videoTimeline.ts`, CSS local, registry de ações; serviços `media_ingest.py`,
`video_render.py`, `transcripts.py` e provider `video_render.py`.

O renderer aceita até nove assets totais e nove tracks de áudio, no máximo 32 clips
externos ativos. A UI atual configura uma track de som natural; não é ainda um
mixer visual com inserção independente de vários cues. Ganho, fade e atraso são
materializados por FFmpeg. `amix` não normaliza automaticamente nem elimina risco
de clipping: o QC permanece necessário. Pan, efeitos e keyframes externos não
suportados são rejeitados, não ignorados.

## Origem e estados de verdade

- Upload, probe e storage permanecem privados e escopados por workspace.
- O asset guarda checksum; o documento referencia ingest, filename, duração,
  origem e licença **declaradas**. `rightsStatus=unknown` e escuta `pending`.
- A API de render exige ingest pronto e checksum do som correspondente ao asset.
  O worker também calcula SHA-256 dos bytes materializados antes da execução.
- Ajustes invalidam a aprovação/render anterior pelas regras existentes do kernel.
- Em 409 o documento é recarregado e a aplicação não sobrescreve a outra sessão.
- Upload pendente fica reaproveitável na sessão, com idempotência do ingest;
  retry de job falho usa a API existente. Recuperação desse upload ainda não
  associado após fechar/recarregar a página permanece uma lacuna de UX.
- Cortes preservam offsets e referências; um som removido inteiramente por trim
  pode permanecer referenciado para histórico, mas não entra no mix.
- O gate `studio_publication_natural_sound_evidence_pending` continua impedindo
  entrega do perfil explícito, mesmo após aprovação criativa genérica. Este corte
  não implementa aprovação acústica nem converte declarações em evidência.

## Evidência executada

- Backend focado: **27/27** — oito novos testes de som, regressões de provider,
  job, ingestão, cortes e preflight de publicação.
- Timeline frontend: **18/18**, incluindo três testes de placement/remapeamento.
- Action Contracts: **6/6**; audit estrito: **424 controles executáveis canônicos**,
  zero sem contrato, zero rotas órfãs ou conflitantes.
- Regressão adicional após verificação dos hashes materializados: job/review
  binding **9/9**, com Ruff aprovado.
- E2E autenticado de Video Studio: upload de MP4, proxy, waveform, legenda,
  corte/reorder/trim, render/review; agora também mute, upload de WAV, placement,
  reload, ganho ajustado sem duplicar asset e MP4 com som externo.
- Telemetria usa o evento provider-neutral `clicko:experience` com action/screen/rota,
  sem origem/licença digitadas. `video.natural_sound_apply_requested` registra
  acionamento, não presume sucesso. Não é um coletor de analytics já implantado.
- A prova PCM confirma silêncio antes da entrada e amostras audíveis somente no
  trecho esperado. O teste de provider cobre duas fontes, -6 dB, fades, silêncio
  entre/depois dos cues e bytes originais intactos.
- E2E móvel em **390 × 844**: campos e ação utilizáveis, sem overflow horizontal;
  Axe A/AA nas abas Sons e Saída sem violações detectadas. Testes automáticos não
  substituem pesquisa humana de CX ou escuta.
- TypeScript, Ruff dos arquivos alterados e build passaram; build mantém o aviso
  conhecido de chunk JavaScript acima de 500 kB.

Screenshot: `artifacts/validation/video-studio-natural-sound-mobile.png`.
O MP4 e WAV da jornada são fixtures técnicas, não anúncios ou foley de produção.

## Pendências e rollback

Não houve migração de schema/banco, dependência nova, deploy, commit/push, Figma ou
alteração da VPS. O rollback deve retirar apenas este corte. Documentos com som
externo não podem voltar silenciosamente ao renderer antigo; é necessário mantê-lo
indisponível para esses documentos ou usar renderer compatível. Originais ficam
preservados e não foram excluídos.

Próximos cortes: múltiplos cues de som editáveis, mute/remoção/undo por track,
envelope preservado com fidelidade após split (hoje fades são limitados e reaplicados
ao trecho), preview do mix em tempo real, recuperação de upload após reload, tomada
real aprovada, sincronismo audiovisual, medição acústica calibrada e admissão
server-owned do mix final com licença e escuta humanas verificáveis.

Os dez anúncios continuam **0/10 aprovados para produção**. O trabalho move o fluxo
de vídeo assistido adiante, mas não conclui a meta ampla nem os demais cortes de
Presenter/Motion/CX humano. A continuação anterior foi progresso comprovado
(mute/render/jornada); esta continuação também altera produto e evidência real.
