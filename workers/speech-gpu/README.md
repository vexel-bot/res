# Clicko speech GPU preflight

Este manifest reserva `studio.gpu.speech` para `transcription` e `voice_clone`.
`providers` permanece vazio: WhisperX, Chatterbox e Kokoro+OpenVoice ainda são
candidatos de benchmark, não capacidades do produto. O piso de 16 GiB/compute
7.5 é apenas um limite inicial de isolamento e deverá ser recalibrado pelo
benchmark real antes de qualquer promoção; não é uma alegação de sizing final.

O inventário Chatterbox agora separa código, cada checkpoint T3/S3Gen, voice
encoder, tokenizer, código/checkpoint Perth e a imagem candidata local. O lock de assets
`chatterbox-model-assets.v1.json` fixa oito arquivos para V3 e pt-BR, incluindo a
adaptação explícita `s3gen_v3.pt` → `s3gen.pt` exigida pelo loader local do pack
brasileiro. Seu digest canônico é
`0b3757e10317b5ace3a594ca58bbb6dc184af4a81bfbae0d473398aa543e5b7f`.
Os hashes vêm da revisão exata do Hugging Face; os bytes grandes ainda não foram
montados em imagem. Perth foi clonado separadamente no commit
`ce86c49d029f42272c1902eccb675556b9ed2330`, e o checkpoint bundlado de
37.429.684 bytes foi verificado por SHA-256.

O inventário OpenVoice V2 fixa o converter no commit Hugging Face
`f36e7edfe1684461a8343844af60babc2efbb727`, checkpoint/config e WavMark local
por SHA-256. A cadeia mínima é Kokoro pt-BR → extração direta de embeddings →
converter OpenVoice → watermark local; MeloTTS, Whisper, Silero e downloads
dinâmicos foram excluídos. O inventário segue `incomplete`: a cadeia composta
Kokoro, a licença do wheel WavMark, SBOM/notices e a imagem GPU ainda não foram
aprovadas para promoção.

O job de clone agora materializa uma única amostra consentida, valida o checksum,
normaliza para WAV PCM16 mono/24 kHz de 3–30 s e entrega o arquivo apenas no diretório
efêmero do job. `VoiceCloneProvider` é um registry separado de TTS stock, e o resultado
deve repetir `voiceVersionId`, `consentGrantId` e o checksum normalizado na proveniência.
O manifest exige FFmpeg 5.1.9 para essa normalização, mas continua com `providers: []`.

`AuditedVoiceCloneSidecarProvider` materializa a fronteira de processo para as duas
variantes Chatterbox e para Kokoro+OpenVoice. Ele revalida o conjunto completo de
assets antes de cada execução, exige comando absoluto, imagem/manifest atestados,
protocolo e watermark correspondentes, suporta timeout/cancelamento e remove arquivos
de controle. Isso é adapter de candidato; os entrypoints de inferência e as imagens
reais não são promovidos e nada é registrado automaticamente.

O entrypoint `sidecars/chatterbox_clone.py` já traduz os dois loader contracts para
`ChatterboxMultilingualTTS.from_local`, seleciona `t3_mtl23ls_v3.safetensors` ou
`t3_pt_br.safetensors`, exige CUDA/offline, preserva o roteiro integral e grava PCM16
24 kHz. Ele passou contra runtime injetado e assets sintéticos. O entrypoint
`sidecars/kokoro_openvoice_clone.py` também está implementado: compõe Kokoro
`pf_dora`, embeddings diretos do OpenVoice, converter e WavMark local, preserva o
roteiro integral e falha se a releitura não confirmar o watermark.

Os locks Linux AMD64/CUDA 12.4 estão congelados em `candidate/`: Chatterbox possui
125 pacotes (`93ff3518...ee5`) e OpenVoice possui 130 (`d56c6da1...8dd`). Em
2026-08-27, os dois recipes passaram source audit, instalação integral e import smoke
offline no Docker. As imagens locais finais `sha256:5702bdc8...a214a` e
`sha256:bdadbe1e...7d61c` também passaram CLI/UID/import smoke com rede bloqueada,
root filesystem read-only, capabilities removidas e `no-new-privileges`. O tmpfs
`/tmp/clicko-speech` deve ser montado com `uid=10001,gid=10001`. A evidência está
em `candidate/build-verification.v1.json`. Pesos externos de clone, inferência,
SBOM/notices revisados, provenance de promoção, assinatura e ativação continuam
pendentes.

O inventário package-focused SPDX e a triagem de licenças estão ligados aos mesmos
digests em `candidate/license-review.v1.json`. A revisão encontrou dependências
evitáveis de idiomas/demos (`pykakasi`, cleaners OpenVoice e extra inglês Misaki),
além das superfícies que não podem ser omitidas por decisão técnica (`phonemizer-fork`
no G2P PT-BR atual, LGPL e CUDA proprietário). A revisão `speech-gpu-pt-br-minimal-v2`
está planejada, mas ainda não possui lock nem imagem; os artefatos `v1` permanecem
imutáveis e bloqueados.

Digest canônico atual do manifest: `a25610988da91694c8fd9f4a451d2fd18315465d7ce327bbd5e5f9aea79db206`.

O worker precisa de object storage privado, fila isolada, filesystem read-only,
workspace efêmero, no-egress e attestation de GPU. A policy de voz e o lock devem
ser copiados para a imagem somente depois de os pesos, wheels, licença transitiva,
SBOM e provenance estarem congelados.

Gates obrigatórios antes de anunciar providers:

1. corpus privado com consentimento ativo, finalidade, prazo e pseudônimo;
2. benchmark separado de stock/clone com evidência por caso, referência privada
   materializada apenas durante o job e revisão cega;
3. licença comercial explícita para código, pesos e runtime transitivo;
4. cancelamento, retry, cleanup e recibo de deleção testados por tenant;
5. imagem Linux/AMD64 assinada e digest ligada ao manifest e ao resultado do gate.

A VPS Nexus continua fora do plano de execução.
