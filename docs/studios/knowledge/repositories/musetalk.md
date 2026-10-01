# Auditoria — musetalk

**Status:** `full_private_render_generated_pending_human_review`  
**Decisão provisória:** `adapt` para avaliação privada; promoção continua bloqueada  
**Commit:** `0a89dec45a0192b824e3cf4daf96c239440c5ed8`  
**Origem:** https://github.com/TMElyralab/MuseTalk.git  
**Licença de código detectada:** `MIT`, checksum `858c5fdc07b8d71e1c88b64337bbc2c32a70a621733ab19809140ec9e19e6904`

## Capacidade

lip synchronization candidate.

- Manifests: requirements.txt
- Linguagens amostradas: Python
- A documentação do commit fixado recomenda MuseTalk 1.5, 25 FPS e relata um teste Windows em RTX 3050 Ti Laptop de 4 GB no modo FP16.
- O runner Clicko usa `batch_size=1`, `use_float16`, preserva o fundo do vídeo-base e grava corretamente `musetalk-v1.5-local` no lineage.
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware local: RTX 2050 Laptop, 4096 MiB; compatibilidade é hipótese de benchmark, não aprovação.
- PT-BR: o renderer recebe waveform e features acústicas; inteligibilidade e sincronização em PT-BR continuam pendentes de benchmark humano.
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Manter fora do domínio de produção. O adapter de piloto falha fechado sem vídeo-base admitido, WAV aprovado, commit exato, manifesto com checksum de todos os pesos e dependências completas.

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

- pesos auxiliares (Whisper, SD-VAE, DWPose, SyncNet e face parsing) ainda exigem resolução individual de versão, checksum e licença;
- o README declara código MIT e pesos MuseTalk utilizáveis comercialmente, mas isso não concede automaticamente os termos dos modelos auxiliares;
- o `testdata` da internet é somente para pesquisa não comercial e não será usado;
- o vídeo-base de 12 s será reproduzido em ciclo bidirecional pelo algoritmo durante o WAV de 32,125 s; repetição perceptível é um risco explícito do piloto;
- biometric/identity use requires explicit consent, private benchmark and deletion controls

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [x] confirmar licença do código no commit fixado;
- [ ] confirmar licença e checksum de cada peso auxiliar;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.

## Gate atual do piloto Caio Vale

Atualização de execução em 2026-09-04 (substitui o estado histórico abaixo): vídeo-base Sora admitido por amostragem; voz autorizada V3 com 44,52 s; modelos baixados e checksums registrados; runtime CUDA local instalado. O adapter de câmera fixa gerou 75 frames em 25 FPS, 720 × 1280, com áudio, em 52,78 s após reuso da preparação. Pico de memória alocada por PyTorch: 2.055.689.728 bytes. Não é uma medida do consumo total do processo/driver. Há suavização da barba/lábios nas amostras. Render completo em execução, não aprovado para produção.

O adapter ativo não usa DWPose, S3FD nem SyncNet: ROI estática vinculada ao checksum de uma única fonte. O BiSeNet carrega seu checkpoint completo sem desserializar o ResNet antigo. A revisão dos nove arquivos verificados está em `../ledgers/musetalk-fixed-camera-private-model-review-2026-09-04.json`; pesos excluídos não recebem aprovação implícita.

Detalhes e falhas: `../../pilots/CLICKO_CAIO_LOCAL_CLONE_EXECUTION_2026-09-04.md`.

Conclusão posterior: o render completo terminou em 691,30 s, 44,52 s de duração e 1.113 frames. QC decodificou todos os frames; fonte, máscaras e áudio têm lineage. Continua `private_review`, com naturalidade/identidade/lip-sync aguardando revisão humana. A menção a render em execução acima é o marco intermediário preservado.

### Registro histórico anterior à execução

- código: fixado e limpo em `0a89dec45a0192b824e3cf4daf96c239440c5ed8`;
- GPU: detectada, 4 GB;
- FFmpeg: disponível;
- WAV local: pronto, 32,125 s, checksum registrado;
- vídeo-base: ausente porque o preflight Sora rejeitou a chave antes do POST;
- pesos/runtime MuseTalk: não baixados; serão resolvidos somente depois que o vídeo-base passar pela admissão visual;
- custo em nuvem do avatar: US$ 0.
