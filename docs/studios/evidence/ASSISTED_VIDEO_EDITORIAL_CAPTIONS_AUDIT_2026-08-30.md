# Auditoria vertical — Vídeo Assistido sem voz, legenda editorial

Data: 30/08/2026  
Status: primeiro corte técnico aprovado; áudio natural adquirido, ainda não aprovado para produção

## Decisão

O Video Studio autenticado não usa mais uma transcrição manual fictícia para materializar texto em
um vídeo sem fala. O texto informado pelo editor agora cria diretamente a track
`captions-main` do `CreativeDocument`. Cada linha vira um cue temporal editorial, sem `speaker`,
`sourceSegmentId` ou `confidence`.

O documento grava também `captionMode=editorial` e `speechExpected=false`. Isso separa texto que
conduz a narrativa visual de evidência de reconhecimento de fala. Nenhum endpoint de transcrição,
Whisper, TTS, clonagem, voz stock ou lip-sync participa deste corte.

## Persistência e concorrência

- os cues usam identidades estáveis `editorial-caption-N`;
- o último cue termina exatamente no último frame da timeline;
- reaplicar substitui somente `captions-main` e preserva as demais tracks;
- a gravação usa a revisão corrente do documento;
- conflito `409` recarrega a revisão vencedora e pede repetição explícita;
- após cortes, trim e reorder, o texto do editor reflete a ordem efetiva dos cues na timeline;
- reload recupera exatamente esse estado persistido.

## Prova autenticada

O E2E percorreu upload de MP4, probe, proxy, time-map, waveform, aplicação das legendas,
corte não destrutivo, reorder, trim por teclado, render FFmpeg, QC, reload e envio para revisão.
No snapshot revisado, o teste exige:

- track `Legendas editoriais PT-BR` materializada no MP4;
- todos os cues com campos de fala nulos;
- `captionMode=editorial` e `speechExpected=false`;
- lista de transcrições vazia para o ingest;
- texto reidratado depois da recarga;
- artefato privado com checksum, H.264/AAC e revisão exata vinculada.

Resultado: 1/1 E2E autenticado passou.

## Qualidade estrutural

- TypeScript/lint: passou;
- build: passou, mantendo somente o aviso conhecido de chunk acima de 500 kB;
- Action Contracts: 6/6;
- audit CX estrito: 413 controles executáveis canônicos, zero sem Action Contract;
- timeline unitária: 13/13;
- Axe da superfície de vídeo: 1/1 sem violações WCAG A/AA detectáveis;
- `git diff --check`: sem erro de whitespace; apenas avisos de conversão LF/CRLF.

## Limite da prova

O áudio usado no E2E é uma fixture técnica para exercitar waveform, encode e QC; não é um asset de
produção e não é apresentado como foley natural licenciado. O Video Studio ainda preserva o áudio
captado no take, e uma waveform não comprova ausência de voz ou música.

Portanto, este checkpoint não aprova nenhum dos dez anúncios UGC para produção. O próximo corte
precisa obter bytes reais de take/avatar e foley/ambiência, registrar licença e checksum, executar
detecção rastreável de fala/música, concluir escuta humana e vincular tudo ao digest do caso. Até
isso acontecer, os dez casos permanecem corretamente em `0/10 production-ready` e publicação
externa continua bloqueada.

Nenhuma VPS, serviço externo, Voicebox ou Figma foi alterado nesta entrega.

## Aquisição iniciada — caso 01 café

O primeiro lote de som foi obtido em
`artifacts/validation/ugc-no-voice/assets/ugc-nv-01-cafe/`, totalizando menos de 1 MB:

- grãos saindo de torrador, `CC BY 4.0`, Work With Sounds / Werstas;
- água fervente despejada em caneca, domínio público, cori;
- caneca tocando a mesa, `CC0 1.0`, atlaslives via Freesound.

O manifesto `sources.json` registra origem, licença, autoria, duração, tamanho e SHA-256.
O preflight reproduzível combina FFmpeg, `webrtcvad-wheels 2.0.14` em modo agressivo e um
YAMNet ONNX local de aproximadamente 3,7 milhões de parâmetros. A entrada log-mel segue os
parâmetros canônicos (16 kHz mono, 25/10 ms, 64 bandas, patches 96 × 64); o export expõe logits e o
auditor aplica sigmoid antes do limiar conservador de `0.35`.

O resultado continua falhando fechado. Foley transiente acionou o VAD nas três fontes, portanto
fala segue `inconclusive`. YAMNet marcou música como `pass` nos sons de grãos e água; a batida da
caneca ficou `inconclusive` porque o maior evento musical foi `Wood block` (`0.4116838`), um falso
positivo plausível que precisa de escuta. O som da água também ficou inconclusivo para voz ao marcar
`Breathing` (`0.42239255`). Em nenhum caso o classificador substitui revisão humana.

O modelo é um export de terceiro sem model card ou relatório de paridade com o checkpoint oficial.
Seu commit, arquivos e hashes estão fixados em
`artifacts/models/yamnet-onnx-d8b2365/model-manifest.json`, com
`conversionProvenanceVerified=false` e uso limitado a challenger de preflight. A escuta humana,
calibração num corpus Clicko, take/avatar com direitos e o mix final continuam bloqueando produção.
Nenhum byte foi promovido.

Um mix técnico de 15 segundos foi materializado para fechar somente o caminho de composição dos
cues `s1` e `s2`. Ele encadeia grãos, água e impacto da caneca, preserva cada fonte no manifesto e
foi reanalisado: música ficou `pass`, fala `inconclusive`, escuta `pending`. O arquivo mede
`-29.75 LUFS` e não foi masterizado. Além disso, as fontes não comprovam captação no mesmo ambiente
e não existe take com o qual avaliar sincronismo. O manifesto
`candidate-final-mix-manifest.json` declara todos esses bloqueios; o termo “final” no nome significa
timeline completa do candidato, não aprovação de produção.

Testes do detector e contrato UGC sem voz: 10/10. Ruff: aprovado. As dependências foram fixadas em
`backend/requirements-audio-audit.txt` (somente avaliação local/dev, fora da API e do worker padrão);
o auditor está em `backend/scripts/audit_ugc_sound_asset.py`.
