# Caio Vale — execução local da voz autorizada e avatar

Este registro substitui os estados operacionais antigos, sem apagar tentativas anteriores.
Workspace: `C:\Users\edugu\Downloads\res`. O projeto no OneDrive não foi usado.

## Evidências concluídas

- Uma operação Sora concluída: `video_6a9b4a23a3348191ac64616dd4dee7430ce114a31905529b`.
- Base: `artifacts/studios/avatar-pilots/caio-vale/base-video-v1.mp4`; 12 s, 720 × 1280, 30 FPS, 360 frames, um stream visual e nenhum áudio.
- SHA-256: `e777ee42a96a44c4f1e56b8ff8273e9f1a12d2d2127a6fe11fa0675234921912`.
- Custo estimado acumulado: US$ 1,20; teto US$ 1,50. Fatura não consultada. Nenhuma segunda geração enviada.
- Inspeção visual amostral: uma pessoa ficcional, rosto livre, barba curta, camisa verde-petróleo, fundo cinza, luz e identidade consistentes nas amostras. Enquadramento mais fechado que a intenção inicial, com pouco espaço sobre o cabelo. Não equivale a revisão humana de todos os frames.
- Autorização vocal do usuário: `user-session-authorization-2026-09-04`. Referência de 11,8865 s; arquivo original preservado fora do repositório, sem upload. Não se afirma que seja a voz de um personagem, ator ou dublador específico.
- Voz final candidata V3: `C:\Users\edugu\Downloads\clicko-private-evaluation\voice-casting\caio-vale\caio-full-ad-v3.wav`.
- WAV PCM mono, 24 kHz, **44,52 s**; SHA-256 `8f5df5e8efc4bd7d4ab54b3cc1ec9dd50d62b9be1ba01f3faeb983b64b68419b`.
- Medição FFmpeg: -17,00 LUFS integrados, -1,50 dBTP, LRA 4,70. Nenhuma alteração artificial da velocidade.
- ASR local `faster-whisper`/`small`, CPU int8, PT-BR, reconheceu as seis frases e o CTA; grafou a marca como “Clico”. Isso sustenta completude lexical, não comprova naturalidade nem equivalência vocal.

## Falhas diagnosticadas e preservadas

1. Kokoro e Chatterbox stock: rejeitados pelo usuário; continuam no histórico.
2. Condicionamento inicial em FP16: o código upstream convertia tokens inteiros da referência para FP16. Inteiros acima de 2048 podem perder precisão; converter de volta depois não recupera o valor. O adapter agora conserva os tokens inteiros originais antes da conversão, restaurando-os na entrada do flow.
3. V1 integral chegou ao limite de aproximadamente 40 s do gerador e sua transcrição era fortemente distorcida. Não foi usado como áudio do avatar.
4. V2 por frases: transcrição recuperou o texto, mas duração de 51,44 s reprovou o contrato. Arquivo preservado, não promovido.
5. V3: retiradas duas frases inteiras redundantes da copy antes da síntese. Seis unidades completas, com intervalos de 120 ms, preservando cinco beats e CTA.

## Copy e mapa da fala V3

| Intervalo da síntese | Função | Texto |
|---|---|---|
| 0–6,64 s | Hook | Se sua agência começa um vídeo escolhendo cenas, ela já começou pela etapa errada. |
| 6,76–16,08 s | Problema | Sem uma lógica comum, oferta, audiência e referências viram decisões soltas na produção. |
| 16,20–25,72 s | Mecanismo | O Clicko Studios organiza estratégia, copy, roteiro, personagem e produção em um fluxo revisável. |
| 25,84–30,36 s | Especificação | Cada decisão fica ligada ao objetivo da campanha. |
| 30,48–40,96 s | Benefício | Assim, sua equipe pode avaliar o que funciona, corrigir a etapa certa e preservar a identidade de cada projeto. |
| 41,08–44,52 s | CTA | Solicite acesso ao piloto do Clicko Studios. |

São timestamps dos segmentos sintetizados, não alinhamento fonético. As notas numéricas de copy do plano anterior não foram reaplicadas como se fossem uma nova auditoria independente. A primeira frase continua sendo uma formulação confrontativa a avaliar na revisão criativa.

## MuseTalk local e limites do adapter

- Commit: `0a89dec45a0192b824e3cf4daf96c239440c5ed8`; checkout mantido limpo.
- Runtime isolado: PyTorch 2.6.0+cu124, Diffusers 0.30.2, Transformers 4.39.2, GPU RTX 2050 4 GB.
- `scripts/musetalk_fixed_camera_pilot.py` usa features Whisper, VAE, UNet MuseTalk 1.5 e segmentação BiSeNet.
- Para esta única fonte com câmera fixa, uma ROI admitida `[100,174,565,650]` substitui DWPose/S3FD. Não é um detector geral, não serve automaticamente para outra identidade ou câmera móvel.
- Os 300 frames da base a 25 FPS são preparados uma vez. Repetição bidirecional sem duplicar os endpoints estende a base durante a fala; inversão do movimento e repetição são riscos explícitos.
- Pesos grandes carregados separadamente; UNet construído diretamente em FP16 na GPU. Features e latentes são armazenados localmente para reutilização.
- O checkpoint completo BiSeNet contém o backbone. O arquivo ResNet antigo em formato tar não é desserializado; o carregamento completo exige correspondência estrita das chaves.
- DWPose e SyncNet foram baixados, mas **não são executados por este adapter**. Nenhuma pontuação SyncNet será inventada.
- Rosto-base não treina voz. `heygemModelCreated=false`; renderer efetivo é `musetalk-v1.5-local`.
- Manifesto de pesos e revisão limitada ao benchmark privado: `../knowledge/ledgers/musetalk-fixed-camera-private-model-review-2026-09-04.json`.

## Estado de entrega

Voz V3 pronta. Prova curta concluída: `caio-lipsync-proof-v2.mp4`, 3 s, 75 frames, 720 × 1280, 25 FPS, um stream visual e um áudio. SHA-256 `e40401ea239abc738cd9c8d2d0a1a8e8c5087ac6fac304c42bd4382c9e61f7bf`. Execução após preparação: 52,78 s; pico de alocação PyTorch 2.055.689.728 bytes. Nove amostras mostram articulação e fundo estável, mas suavização de barba/lábios; não permitem atestar sincronização perceptiva ou estabilidade de todos os frames.

Preparação reaproveitável salva em `C:\Users\edugu\Downloads\clicko-private-evaluation\avatar-renders\caio-vale\fixed-camera-cache-v1`.

**Anúncio bruto completo gerado:** `C:\Users\edugu\Downloads\clicko-private-evaluation\avatar-renders\caio-vale\clicko-studios-caio-vale-raw-ad-v1.mp4`.

- 44,52 s, 720 × 1280, H.264, 25 FPS, 1.113 frames; AAC mono 24 kHz.
- 11.215.416 bytes; SHA-256 `7a994145054f8c6b192b791c7800e08d06118f5925bb5158e21bd9abd700ee0a`.
- Render local: 691,30 s; pico alocado PyTorch 2.055.689.728 bytes.
- QC decodificou 1.113/1.113 frames, sem frames quase pretos pelo critério registrado. Erro médio fora da cabeça: 1,557/255; máximo por frame 1,639/255 (limiar interno 3/255).
- Áudio do MP4: -17,00 LUFS; -1,46 dBTP; LRA 4,70. Disclosure sintético presente nos metadados.
- Nova transcrição automática feita diretamente do MP4 final reconheceu as seis frases; CTA entre aproximadamente 40,80 e 44,40 s. Marca grafada pelo ASR como “Clico”. Nenhuma frase foi truncada na muxagem segundo essa conferência lexical.
- Inspeção de nove amostras gerais e nove próximas às inversões (11,96 s, 23,92 s e 35,88 s): cabeça, figurino e fundo estáveis nas amostras; articulação varia, com suavização visível da barba e lábios. Não certifica sincronização percebida nem todos os frames.
- Avatar reutilizável registrado em `../knowledge/ledgers/caio-vale-private-avatar-preparation-v1.json`.

Estado final: `avatar_rendered_private_review`. Ainda não há aprovação de naturalidade, identidade ou sincronização humana. Publicação e promoção do provider permanecem bloqueadas. Sem B-roll, trilha, motion, captions ou novas cenas.

Falha adicional preservada: a primeira composição passou um array de coordenadas NumPy à PIL, incompatível com `paste`; corrigido para lista de inteiros nativos. A segunda prova usou a mesma preparação, sem nova geração da fonte.

## Testes automatizados executados

- 14 testes direcionados de contratos do cast, piloto, ciclo bidirecional, manifesto e QC estrutural passaram.
- 13 testes adicionais de adapter OpenAI com transporte simulado e integridade dos assets Chatterbox passaram. Não fizeram chamadas pagas.
- Ruff e compilação dos scripts de geração/renderer/QC passaram.
- Prova curta: 75/75 frames decodificados, zero frames com luminância média abaixo de 3; diferença média fora da cabeça de 1,546/255, máximo por frame 1,613/255. Limiar interno exploratório 3/255 em imagens reduzidas para 180 × 320; não é uma métrica semântica nem prova de identidade ou sincronização labial.
- O aviso genérico de fallback de serialização do VAE não corresponde à liberação de pickle irrestrito neste runtime: o loader Diffusers instalado passa `weights_only=True` ao PyTorch 2.6. O checkpoint legado ResNet não é carregado.

## Fontes técnicas consultadas

- [MuseTalk — código e instruções oficiais](https://github.com/TMElyralab/MuseTalk): FP16, modelo 1.5, composição e limitações.
- [Model card MuseTalk](https://huggingface.co/TMElyralab/MuseTalk): licença declarada CreativeML OpenRAIL-M; não confundir com MIT do código.
- [SD-VAE publicado pela Stability AI](https://huggingface.co/stabilityai/sd-vae-ft-mse): model card declara MIT.
- [Whisper Tiny](https://huggingface.co/openai/whisper-tiny): checkpoint e licença declarada Apache-2.0.
- [Face parsing upstream](https://github.com/zllrunning/face-parsing.PyTorch): código MIT; procedência de redistribuição dos pesos requer revisão adicional antes de promoção.

Revisão técnica de escopo, não parecer jurídico. Nenhum modelo é redistribuído nem oferecido como serviço neste piloto.
