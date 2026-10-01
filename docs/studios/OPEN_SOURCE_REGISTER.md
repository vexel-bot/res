# Clicko Studios — registro de open source

**Consulta:** 2026-08-27  
**Método:** páginas, repositórios e licenças oficiais; HEAD registrado para reprodutibilidade. Os candidatos foram clonados para `C:\Users\edugu\Downloads\clicko-oss-evaluation`, fora do repositório Clicko e sem incorporação ao produto.

## Registro resumido

| Projeto | URL / commit auditado | Problema | Licença observada | Decisão atual |
| --- | --- | --- | --- | --- |
| Vane | https://github.com/ItzCrazyKns/Vane — `7dc5d088f7262fbc5e39037f84940a8a2193c5fb` | pesquisa com fontes via SearxNG/LLMs | MIT; dependências/containers exigem SBOM próprio | **encapsular**, apenas como candidato a `ResearchProvider`; não substitui Radar. |
| HyperFrames | https://github.com/heygen-com/hyperframes — `2ca578f9455ca928ab168e7dd08a1a3a9d834788` | composição HTML, preview, captura e render determinístico | Apache-2.0; dependências, browser e FFmpeg exigem SBOM/build próprios | **encapsular/spike prioritário** como candidato a `VideoRenderProvider`. |
| HyperFrames Launch Video | https://github.com/heygen-com/hyperframes-launch-video — `930f89186b8e155d632d9afe49054c02d4d7d85a` | referência real de composição complexa | sem arquivo LICENSE; README limita composição e mídia a uso de referência | **referenciar apenas**; não copiar mídia ou composição para produção. |
| Duix-Avatar | https://github.com/duixcom/Duix-Avatar — `1328feb5871448c8fa3d0e45b3bbc87e7c1d458a` | avatar/voz offline | DUIX.COM Community License, não SPDX/permissiva | **rejeitar por ora**; gate jurídico e benchmark isolado. |
| HeyGem (Caladog) | https://github.com/Caladog/HeyGem — `a0053f7cd6440203d76737ac2920db8b293fb3f6` | avatar/voz offline | Silicon Intelligence Community License; atribuição e licença comercial acima de 1.000 MAU | **rejeitar** pelo critério “somente open source”; manter clone apenas como evidência. |
| OpenVoice | https://github.com/myshell-ai/OpenVoice — `74a1d147b17a8c3092dd5430504bd83ef6c7eb23` | clonagem de voz | repositório e pesos V2 MIT; wheel WavMark exige revisão | **encapsular para benchmark** com Kokoro; inventário `incomplete` `6e744823...496e1`, imagem local isolada, sem pesos/inferência/ativação. |
| Chatterbox | https://github.com/resemble-ai/chatterbox — `5de7a54aa4e5e2baadb0182dde554908b48b85c2` | TTS/clonagem zero-shot multilíngue | código MIT; pesos V3 e pack pt-BR MIT | **candidato primário de benchmark**, inventário `review_required` `45242126...e0819`; pack pt-BR local verificado, mas 4 GiB < piso 16 GiB, sem inferência/biometria/ativação. |
| PersonaPlex | https://github.com/NVIDIA/personaplex — `3428dfd95309a7f3c84fd93259ded0f810d1ff91`; modelo `fdaf4090a61cb315c138a1faee287ffd6c716309` | conversa speech-to-speech full-duplex com role/voice prompt | código MIT; pesos sob NVIDIA Open Model License customizada, acesso gated e `license: other` | checkpoint **rejeitado** pela política open-source-only; usar somente padrões de protocolo/métricas. Não é TTS PT-BR de anúncio. |
| Kokoro | https://github.com/hexgrad/kokoro — `dfb907a02bba8152ca444717ca5d78747ccb4bec` | TTS stock leve e TTS-base | código/pesos Apache-2.0; Misaki Apache-2.0; eSpeak NG GPL-3.0+ | **candidato em avaliação** atrás de `SpeechSynthesisProvider`; adapter e runner existem, mas pesos, lock revisado, imagem, benchmark humano e licença do container ainda bloqueiam promoção. |
| MuseTalk | https://github.com/TMElyralab/MuseTalk — `0a89dec45a0192b824e3cf4daf96c239440c5ed8` | lip-sync/dublagem sobre vídeo existente | código MIT; pesos CreativeML OpenRAIL-M; SyncNet OpenRAIL++ | **rejeitar para produção** pelo critério open-source-only; manter somente evidência documental/sintética. |
| LatentSync | https://github.com/bytedance/LatentSync — `a229c3948406bc2cf6eaf4873e662e70c6a04746` | lip-sync por difusão | código Apache-2.0; pesos OpenRAIL++; InsightFace não comercial | **rejeitar para produção** pelo critério open-source-only; manter somente evidência documental. |
| LivePortrait | https://github.com/KwaiVGI/LivePortrait — `9b294b3d0536135442ea73cb01e6cb3ca7029dd3` | motion/retarget de retrato | core/pesos MIT; detectores InsightFace não comerciais | **condicional**: somente após substituir detector, piná-lo e repetir licença/benchmark. |
| FFmpeg | https://github.com/FFmpeg/FFmpeg — `1019f8f036602a8464185baa4857654337eeca14` | probe/transcode/composição/render | LGPL por padrão; GPL/nonfree depende do build e libs | **encapsular depois de auditar binário**, provável infraestrutura de vídeo. |
| Fabric.js | https://github.com/fabricjs/fabric.js — `2bd4992cabf4ec9609aa349ea09b723cadc94bef` | canvas e serialização | MIT | **referenciar**, spike somente se engine atual falhar contrato. |
| Konva | https://github.com/konvajs/konva — `aa3432ebf1c48606764fef0918e68bfc4aec3684` | cena canvas, eventos e transforms | arquivo LICENSE MIT | **referenciar**, comparar com Fabric sem adoção antecipada. |
| Lexical | https://github.com/facebook/lexical — `3984d88bf28960dfcb6fa36977b923396ad9ae70` | edição rich text estruturada | MIT | **spike condicionado** para Editorial, sem tornar seu JSON canônico. |
| wavesurfer.js | https://github.com/katspaugh/wavesurfer.js — `666ba74d4d1138137b235b5aeeac2cb383b7e022` | waveform, regiões e timeline de áudio | BSD-3-Clause | **spike** para interação de áudio. |
| React Timeline Editor | https://github.com/xzdarcy/react-timeline-editor — `4148f4a837dd767ea66807560d05bc7b65c7e578` | interação básica de timeline | MIT | **spike de UI**, sem acoplamento ao documento canônico. |
| OpenCut rewrite | https://github.com/opencut-app/opencut — `400f097becba5db0fbc305d5a65348cb81c20356` | editor web/desktop/mobile futuro | MIT | **acompanhar/referenciar**; Editor API, plugins, headless e MCP ainda são roadmap, não capacidade entregue. |
| OpenCut Classic | https://github.com/opencut-app/opencut-classic — `cf5e79e919144200294fb9fed22a222592a0aeea` | editor CapCut-like, timeline e compositor local | MIT; repositório arquivado | **piloto seletivo/referência**, comparar módulos com timeline Clicko; não forkar a aplicação. |
| WhisperX | https://github.com/m-bain/whisperX — `2cfd7b7c5c7bba144954364db747319b50e8232b` | transcrição, alinhamento e diarização | BSD-2-Clause; modelos auxiliares têm termos próprios | **spike futuro** atrás de `TranscriptionProvider`. |
| SAM 2 | https://github.com/facebookresearch/sam2 — `2b90b9f5ceec907a1c18123530e92e794ad901a4` | segmentação e tracking | Apache-2.0 no código; checkpoints e datasets exigem inventário próprio | **referenciar**, posterior ao fluxo básico de vídeo. |
| V-JEPA 2 | https://github.com/facebookresearch/vjepa2 — `204698b45b3712590f06245fbfba32d3be539812` | representação e predição latente de vídeo | código majoritariamente MIT com arquivos Apache-2.0; checkpoints/datasets exigem manifest próprio | **benchmark condicionado** como `VideoWorldModelProvider`; não é árbitro nem gate autônomo. |
| TAPNet/TAPIR | https://github.com/google-deepmind/tapnet — `c2cbab81cc06092b5f05bfe2da7bfec54e2079c9` | point tracking persistente | código e checkpoint panning Apache-2.0; checkpoint `628611c6...09daa` | **candidato PGV-1 aprovado para build futuro**, ainda sem provider. |
| RAFT | https://github.com/princeton-vl/RAFT — `2888e15a51fa41140771d3f498ed8023cff098d1` | fluxo óptico denso | código BSD-3-Clause; Things `fcfa4125...9a7e1`; direitos do checkpoint não explícitos | **review_required**; não ativar antes de decisão jurídica ou substituição. |
| Depth Anything V2 | https://github.com/DepthAnything/Depth-Anything-V2 — `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf` | profundidade monocular | Small Apache-2.0 e `715fade1...e1378`; Base/Large/Giant CC-BY-NC | **usar somente Small em benchmark**; bloquear variantes NC. |
| OpenCV | https://github.com/opencv/opencv — `8b7dc43c227746366213a65ad1477ed37fb8d365` | visão/geometria clássica | código Apache-2.0; wheel 4.13.0.92 pinado contém FFmpeg LGPL e notices terceiros | **baseline PGV-1 implementada em avaliação**, sem registro; revisar wheel/SBOM antes de promover. |
| Supervision | https://github.com/roboflow/supervision — tag `0.30.1`, `5f25aa0ee6dc22891415b6e3d2e1689ce7a32952` | normalização model-agnostic, annotations, zones, datasets e métricas CV | código MIT; dependências/binários/modelos conectados exigem inventários próprios | **encapsular em spike** como toolkit efêmero; inventário `review_required` `2ad5d4ad...da88`, OCI/runtime hardened materiais, assinatura e revisão humana abertas; nunca contrato canônico ou modelo de física. |
| Physics-IQ | https://github.com/google-deepmind/physics-iq-benchmark | avaliação de princípios físicos em experimentos reais | software Apache-2.0; materiais/dados CC BY 4.0 | **adotar como referência de benchmark**, não como runtime. |
| IntPhys2 | https://github.com/facebookresearch/IntPhys2 | permanência, imutabilidade, continuidade e solidez | dataset CC BY-NC com restrições declaradas | **evidence-only**, nunca corpus de produção/comercial. |
| MVPBench | https://github.com/facebookresearch/minimal_video_pairs | pares mínimos anti-atalho para física em vídeo | CC BY-NC | **evidence-only** para desenhar paired accuracy e holdouts privados. |
| CausalVQA | https://github.com/facebookresearch/CausalVQA | raciocínio causal, contrafactual, antecipação e planejamento | código/dados sujeitos à licença do EgoExo e manifest próprio | **evidence-only** até auditoria completa. |
| CoTracker | https://github.com/facebookresearch/co-tracker | tracking de pontos | CC BY-NC | **rejeitar produção**; comparação documental apenas. |
| Perspective Fields | https://github.com/jinlinyi/PerspectiveFields | up-vector, latitude e calibração de câmera | Adobe Research License, uso não comercial | **rejeitar produção**; usar o problema/taxonomia, não o código. |
| VGGT | https://github.com/facebookresearch/vggt | geometria visual 3D | checkpoint original não comercial; checkpoint alternativo sob licença não padronizada | **rejeitar** sob open-source-only. |
| Remotion | https://github.com/remotion-dev/remotion — `e624eb770082630dd596fa6783ee1be96db64bba` | composição/render programático React | Remotion License, gratuita apenas para indivíduos/organizações elegíveis; não é licença open source permissiva | **rejeitar** pelo critério “somente open source”. |
| Ditto TalkingHead | https://github.com/antgroup/ditto-talkinghead — `c3e47eee2e626500017a0556b470d6d4182f85e8` | talking head controlável e de baixa latência | repositório Apache-2.0; checkpoint oficial inclui detector/landmarks InsightFace | upstream **rejeitado** no inventário `fcc0ebfd...9f64`; somente uma nova variante com detector permissivo e rebenchmark pode voltar. |
| EchoMimicV3 | https://github.com/antgroup/echomimic_v3 — `7e89489ca51c0d008fc1963ec6c03fc5bd0b9397` | retrato, meio-corpo e corpo dirigidos por áudio | código/modelos declarados Apache-2.0; RetinaFace, Wav2Vec2, CLIP e componentes Wan exigem inventário transitivo | inventário **`incomplete`** `33696f22...49a1`; sintético apenas até pesos, detector, lock e imagem serem aprovados. |
| Wan2.2 | https://github.com/Wan-Video/Wan2.2 — `42bf4cfaa384bc21833865abc2f9e6c0e67233dc` | geração de vídeo e character animation/replacement | código/modelos declarados Apache-2.0; dependências/checkpoints auxiliares exigem manifest | inventário **`incomplete`** `2ba98e49...1470`; lane avançada separada, fora do MVP 24 GB. |
| Motion Canvas | https://github.com/motion-canvas/motion-canvas — `7b91435c301d530351dcf5ebb91dd139c002e405` | motion graphics vetorial programável e sincronizado a voice-over | MIT | inventário **`incomplete`** `69051427...f9a2`; spike AI-2 atrás de `MotionGraphV1`, sem provider anunciado. |
| OpenTimelineIO | https://github.com/AcademySoftwareFoundation/OpenTimelineIO — `bc5fe2d78dc3f8b2a8feb7e04483d85a12e80072` | interchange de informação editorial | Apache-2.0 + NOTICE | inventário **`incomplete`** `bb5f3a7b...14816`; adapter de import/export futuro, nunca fonte canônica. |
| PySceneDetect | https://github.com/Breakthrough/PySceneDetect — `4fc4cdbe969f347f77eea996a18cae85eaa3ce58` | cuts, fades e segmentação temporal | BSD-3-Clause; imagem oficial inclui FFmpeg/mkvmerge a auditar | inventário **`incomplete`** `a8c02666...d5afc`; analyzer futuro para `MediaIndexV1`, sem provider anunciado. |
| Qwen3-VL | https://github.com/QwenLM/Qwen3-VL — `96588727e44c78b25ba03ea03b8e12f7e64fd0da` | compreensão multimodal/vídeo e planejamento visual self-hosted | Apache-2.0 no repositório; cada variante/checkpoint/container precisa de manifest | inventário **`incomplete`** `12d48fcf...f192`; benchmark 4B/8B em GPU externa, nunca na VPS atual. |
| Qwen3 (texto) | https://github.com/QwenLM/Qwen3 — `7a2f61ffc7a20d47efcd2bf97f6f2bf52729042e` | copy, planejamento, revisão e raciocínio estruturado self-hosted | pesos pinados 4B/30B Apache-2.0; repo de referência sem `LICENSE` raiz nesse commit; GGUF oficial licencia separadamente | inventário **`incomplete`** `b81d6325...6f67`; Qwen3-4B GGUF Q4 local (4.022.468.096 parâmetros) passou API loopback autenticada; tiers Instruct/30B e worker Linux continuam pendentes. |
| Kimi K2.5 | https://github.com/MoonshotAI/Kimi-K2.5 — `c119f68d1a9a13f88f6a59b8e5e0840983b22689` | challenger de teto para planejamento/raciocínio e visão agentic | Modified MIT; uso comercial permitido, com atribuição de UI acima de 100M MAU ou USD 20M/mês; não equivale a MIT padrão | inventário **`incomplete`** `2f747a15...251d`; ~595 GB/H200 TP8, somente depois de Qwen e com gate jurídico/custo. |

Os digests completos, tamanhos, URLs imutáveis e evidências de licença do PGV-1 ficam em `benchmarks/studios/reality/pgv1-artifact-inventory.v1.json`; o status agregado é `review_required`, nunca uma aprovação implícita do conjunto.

Os sete candidatos adicionados em 26/08/2026 foram clonados com histórico raso e Git LFS sem baixar pesos, sempre fora do monorepo. A decisão detalhada, benchmark de seis avatares, API e arquitetura de edição autônoma estão em `research/AI_AVATAR_AND_AUTONOMOUS_EDITING_STRATEGY_2026-08-26.md`.

## Fichas de avaliação

### HyperFrames

- Framework Apache-2.0 para transformar HTML/CSS, mídia e animações seekable em vídeo determinístico usando Chrome headless e FFmpeg.
- Oferece CLI, core, engine, producer, Studio web, player e render distribuído em AWS Lambda; a arquitetura por packages permite avaliar somente o núcleo necessário.
- A composição HTML não se torna o domínio Clicko: deve ser projeção reconstruível do `CreativeDocument`, atrás de `VideoRenderProvider`.
- É candidato preferencial para o primeiro spike de render programático porque não possui taxa por render nem limite comercial na licença do framework.
- Smoke próprio, sem copiar composição/mídia do exemplo: HyperFrames `0.8.12`, 1080×1920, 30 fps, 60 frames, H.264, 843.884 bytes. Lint passou com `0 errors, 0 warnings`; dois renders foram byte a byte idênticos, SHA-256 `EE5F09C01D0FFE67C5164670F15D514EDABA423AF58A437E8A55A6A34AE9C74F`.
- Segunda prova: uma fixture válida `studio.creative-document.v1` foi projetada para uma visão descartável do HyperFrames. Dois renders de 843.713 bytes foram idênticos, SHA-256 `3448032BE22E89F5618CF30FE83655365C16D78F143B73CB56857D1CE08DE4B7`, com lint limpo. O documento canônico permaneceu independente de HTML/HyperFrames.
- Terceira prova: o adapter Clicko real projetou o contrato atual, passou lint, cancelamento e smoke HyperFrames `0.8.12`; saída H.264 360×640/30 fps/1 s, 15.043 bytes, SHA-256 `A0D65A68D662A274DA34C548CFA793D6030C9B4BA23B7505D097F3754DB658BA`. Registry permanece opt-in e exige worker isolado.
- Quarta prova: imagem `media-cpu` local non-root/read-only/no-egress renderizou H.264 1080×1920/30 fps/2 s em 24,4 s. A imagem tem digest OCI `sha256:bbfdabed...cb7595`; o CycloneDX catalogou 809 componentes e tem SHA-256 `AF5531A3...E65204`.
- O spike evitou GSAP, cuja licença npm atual é “Standard no charge”, usando timeline seekable própria. O install auditou 187 packages sem vulnerabilidades conhecidas, mas emitiu depreciação para `boolean@3.2.0` e `node-domexception@1.0.0`.
- Mesmo sem font URL na composição, a compilação buscou e cacheou Inter via Google Fonts. A VPS precisa de cache/fontes pré-empacotados e teste sem egress antes de qualquer adoção.
- Gates restantes: build/licença FFmpeg aprovada, packages Debian reproduzíveis, provenance de CI, isolamento por job com credenciais reais, progresso detalhado, benchmark multimídia e worker externo dedicado. Nunca usar a VPS Nexus como worker.

### HyperFrames Launch Video

- Exemplo real com 17 subcomposições, GSAP, Lottie, shaders, Three.js, captions, SFX e footage.
- O repositório não possui arquivo `LICENSE`; o README diz apenas que composição e mídia são publicadas para referência.
- Com HyperFrames `0.8.12`, `hyperframes lint` retornou `8 errors` e `32 warnings`; entre os erros estavam travessia `../` para assets, uso de GSAP incompatível com clips e fonte ausente. O exemplo não é baseline executável confiável na versão auditada.
- Serve como corpus de leitura e benchmark de complexidade. Nenhum asset, áudio, vídeo ou composição será copiado para a Clicko.

### HeyGem (Caladog)

- URL confirmada pelo usuário e clone auditado.
- A licença contém atribuição obrigatória e exige licença comercial acima de 1.000 usuários ativos mensais.
- “Código público” não satisfaz o critério definido de usar somente open source; não integrar, executar com dados reais ou usar como base de produto.
- O clone externo permanece apenas para registrar a decisão e permitir comparação documental.

### Vane

- Resolve pesquisa/answering com fontes; oferece execução Docker e usa SearxNG.
- Não resolve scoring proprietário, aderência à marca, saturação, risco ou aprendizado do Radar.
- API/headless: precisa de spike; a documentação é centrada na aplicação completa.
- SaaS/atribuição: MIT do código; imagem Docker, SearxNG, modelos e providers precisam de inventário separado.
- PT-BR/qualidade/custo: não benchmarkados; dependem de engine de busca e LLM configurados.
- Privacidade/multi-tenancy: self-host ajuda, mas o produto completo não é assumido tenant-safe para Clicko.
- Observabilidade/cancelamento: não validados contra o contrato Clicko.
- Saída: adapter substituível; guardar query, fontes, timestamps e provider, nunca banco/UI do Vane como domínio.

### Duix-Avatar

- Licença exige atribuição visível e traz limite comercial. O arquivo LICENSE auditado fala em mais de 1.000 MAU, enquanto o README observado menciona limiares diferentes; a divergência por si só exige jurídico.
- O repositório também distribui acordo separado para modelos e containers GPU; não se presume que código, pesos e imagens tenham os mesmos termos.
- Hardware: GPU/CUDA e múltiplos serviços; manutenção e custo operacional altos.
- PT-BR, latência, qualidade, isolamento, revogação e deleção: não benchmarkados.
- Privacidade: execução offline é positiva, mas face/voz continuam dados de alto risco.
- Saída: nenhuma integração; se houver autorização futura, ambiente isolado, dados consentidos e adapter descartável.

### OpenVoice

- Código e pesos V2 observados declaram MIT e uso comercial. O checkpoint auditado no Hugging Face está em `f36e7edfe1684461a8343844af60babc2efbb727`.
- README lista suporte nativo V2 a inglês, espanhol, francês, chinês, japonês e coreano; PT-BR não está comprovado.
- O fluxo oficial usa um TTS-base e depois converte o timbre. Para a Clicko, Kokoro pt-BR substitui o MeloTTS nesse papel experimental; essa composição precisa provar pronúncia, prosódia e perda de identidade.
- Requer extração de speaker embedding, conversão e possivelmente GPU; latência/custo não medidos.
- Não oferece governança de consentimento, finalidade, expiração ou revogação da Clicko.
- O lock `studio.openvoice-model-assets.v1` (`035360cd...9d7c`) fixa converter/config em `f36e7edf...bb727`, WavMark `0.0.3` e seu checkpoint em `0ad3c7b...5bfef`. O wheel contém licença MIT com copyright placeholder, portanto permanece `review_required`.
- A cadeia mínima exclui MeloTTS, Whisper/faster-whisper, Silero e downloads dinâmicos: Kokoro pt-BR produz o WAV base; OpenVoice extrai source/target embeddings diretamente e converte; WavMark recebe caminho local pinado.
- O entrypoint composto e o lock CUDA 12.4 com 130 pacotes estão congelados. O recipe passou source audit, instalação e import smoke offline em Docker Linux AMD64, inclusive a substituição verificável do runtime eSpeak. A imagem local final também passou smoke isolado sem rede e sem pesos; não houve inferência.
- Saída: registry exclusivo `VoiceCloneProvider`; o executor materializa uma referência por job, normaliza WAV mono/24 kHz por FFmpeg, verifica checksums e apaga o arquivo efêmero ao encerrar. O adapter candidato usa sidecar offline, revalida o asset manifest por job e exige watermark/result binding; ele não se registra sozinho. O provider nunca recebe chave ampla de storage nem pode ser satisfeito pelo registry de TTS stock.

### Chatterbox

- Código `5de7a54...` e pesos Multilingual V3 `5bb1f6ee...` são MIT. O pack dedicado `pt-BR` está fixado em `b3952f18...`, também MIT; seu model card registra o checkpoint principal com SHA-256 próprio.
- V3 oferece clone por referência e 23+ idiomas; o pack regional existe para comportamento brasileiro. Isso é claim do fornecedor, não resultado Clicko.
- O watermark PerTh é uma vantagem de safety/proveniência, mas sua sobrevivência a MP3, recorte e render final precisa ser medida no corpus Clicko.
- O `pyproject.toml` upstream aponta `resemble-perth` para `master`; o lock Clicko já substitui isso pelo commit MIT auditado `ce86c49d...`. A imagem local existe, mas o artefato de promoção ainda deve emitir SBOM, notices, provenance revisada e assinatura.
- Não existe serviço headless multi-tenant pronto: o adapter Clicko deve controlar fila, limites, assets privados, cancelamento, cleanup e observabilidade.
- A fronteira sidecar Clicko já cobre esses controles com processo cancelável, timeout, attestation e revalidação de assets, mantendo loaders separados para V3 e pack pt-BR. A execução do entrypoint contra o runtime ML/pesos reais continua pendente e nada foi anunciado.
- O entrypoint candidate chama `ChatterboxMultilingualTTS.from_local` com o checkpoint correto de cada variante, exige runtime offline/CUDA e preserva o roteiro sem truncar. O lock CUDA 12.4 com 125 pacotes passou instalação integral; a imagem local final passou smoke isolado sem rede e sem pesos externos. O loader ainda não executou inferência, portanto qualidade, watermark e GPU real não estão comprovados.
- Decisão: comparar Multilingual V3 e pack pt-BR sob a mesma política; nenhum deles está homologado por qualidade/custo.

### PersonaPlex

- O código pinado é MIT, mas os pesos são regidos pela NVIDIA Open Model License Agreement, marcados `license: other` e exigem aceite no Hugging Face. Uso comercial declarado não satisfaz a política Clicko de licença open-source.
- É speech-to-speech full-duplex: escuta e fala simultaneamente, suporta interrupção/backchannel/overlap e combina prompt textual de papel com prompt de voz. Isso é outra capability, não `SpeechSynthesisProvider` de anúncio.
- O model card limita input/output a inglês, 24 kHz, Linux/PyTorch e hardware A100/H100. O safetensor pinado tem aproximadamente 16,74 GB; não cabe na VPS control plane.
- O servidor upstream compartilha estado e serializa sessões por lock, recebe voice prompt por query/path, usa `torch.load` em `.pt`, baixa artefatos em runtime, registra prompts/IP e roda como root na imagem. Não é fronteira SaaS tenant-safe.
- Valor aproveitável sem pesos: protocolo full-duplex, eventos e métricas de interrupção/turn-taking, separação role/voice prompt e replay offline determinístico.
- Decisão: inventory `rejected`, nenhum download, aceite, imagem, provider ou dado humano. Só reabrir por necessidade de conversa ao vivo, mudança explícita de política e sidecar redesenhado.

### Kokoro

- Código `dfb907a0...` e pesos `Kokoro-82M` `f3ff3571...` são Apache-2.0. O model card fornece SHA-256 do modelo v1.0 e descreve três vozes brasileiras.
- A pipeline implementa `pt-br`/`lang_code='p'`, usa Misaki para G2P e eSpeak NG para idiomas não ingleses. Isso torna siglas, marcas, números e nomes próprios foco obrigatório do benchmark.
- É TTS stock, não clone de identidade. Também serve como TTS-base para o conversor de timbre OpenVoice.
- Misaki é Apache-2.0; eSpeak NG é GPL-3.0-or-later. Uso comercial é possível, mas distribuição de imagem/edge worker precisa cumprir source/notice e ser revisada separadamente do uso SaaS interno.
- Modelo pequeno não prova CPU/latência/custo na infraestrutura Clicko; esses números continuam vazios até execução reproduzível.
- O adapter Clicko aceita somente `pf_dora`, `pm_alex` e `pm_santa`, exige cache
  offline pinado e não está no registry do worker. O runner dos 64 casos só mede a
  faixa automatizável e não pode fabricar avaliação humana ou licença.
- O `uv.lock` upstream do commit auditado está desalinhado com o `pyproject`
  (0.9.2 versus 0.9.4). A resolução Linux usa projeto/lock Clicko separado e só vira
  input de imagem depois de SBOM e revisão transitiva.
- Misaki importa `espeakng-loader==0.2.4`. O wheel Linux auditado tem SHA-256
  `08721baf...`, inclui `libespeak-ng.so.1.52.0` do commit `4870adfa...` e não traz
  arquivo nem metadata de licença. Isso diverge do eSpeak `7d426728...` congelado na
  policy; o wheel é inventariado como input `review_required`, nunca como runtime final.
- O runtime válido deve vir do workflow manual `studios-speech-espeak-runtime.yml`:
  build do commit exigido, biblioteca/dados completos, `COPYING`, corresponding source,
  ambiente/flags e manifesto SHA-256 de todos os arquivos. A receita existe, mas ainda
  não foi executada nem incorporada a uma imagem candidata.
- Decisão: primeiro candidato de voz stock, em `evaluation`, nunca um clone de voz e
  sempre atrás de `SpeechSynthesisProvider`.

### MuseTalk

- Código `0a89dec4...` é MIT e o README diz que o modelo pode ser usado comercialmente. Porém o repositório oficial de pesos `3ef28bc5...` declara **CreativeML OpenRAIL-M**, uma licença de modelo com restrições de uso, não OSI.
- A cadeia ainda baixa VAE MIT, Whisper Apache-2.0, DWPose Apache-2.0, face parsing WTFPL e o `latentsync_syncnet.pt` de um repositório OpenRAIL++. Todos foram fixados por revisão na política; o SyncNet mantém o bloqueio.
- O projeto afirma 30+ fps em Tesla V100, mas também relata cerca de 5 minutos para 8 s em RTX 3050 Ti 4 GB/fp16. Portanto “real-time” depende fortemente de hardware e preprocessamento.
- O pipeline trabalha em 25 fps/região facial 256×256 e declara limitações de bigode, formato/cor dos lábios e jitter; é `LipSyncProvider`, não identidade, motion ou cenário.
- Test data do próprio repositório é apenas não comercial e não entra no benchmark Clicko.
- Decisão: rejeitado para produção e para benchmark com pessoas reais sob a regra open-source-only; somente evidência documental/sintética, sem provider ativado.

### LatentSync

- O código `a229c394...` é Apache-2.0, mas os pesos oficiais `c42c7e6c...` declaram **OpenRAIL++**. Tratar o projeto inteiro como Apache-2.0 seria incorreto.
- A versão 1.6 pede no mínimo 18 GB de VRAM, 25 fps/16 kHz, 20–50 diffusion steps e usa InsightFace para landmarks; os modelos distribuídos do InsightFace são não comerciais.
- O repositório oferece CLI/Gradio, não um serviço Clicko; cancelamento, isolamento, cleanup e métricas teriam de vir do adapter/worker.
- Decisão: rejeitado para produção e benchmark com pessoas reais sob a regra atual. Pode permanecer como referência documental de qualidade/arquitetura; não é fallback operacional.

### LivePortrait

- Código `9b294b3d...` e pesos core `82a4fa67...` são MIT. A própria LICENSE manda remover/substituir os detectores InsightFace antes de uso comercial.
- A distribuição oficial inclui `buffalo_l` dentro do repositório de pesos; portanto ocultar o import ou usar apenas humans mode não encerra o problema de licença.
- Os autores medem módulos em RTX 4090 com `torch.compile`, mas isso não inclui toda a cadeia de detecção, I/O, encode e lip-sync. A aceleração precisa ser medida end-to-end.
- Resolve pose/expressão/retarget, não gera roteiro, voz, identidade autorizada, cenário ou boca sincronizada. No Photo Avatar seria composto com um `LipSyncProvider` separado.
- Decisão: candidato condicional a `MotionProvider` apenas depois de selecionar detector/landmarks permissivo, fixar seus pesos/digest e comprovar paridade.

### FFmpeg

- Bom candidato commodity para probe, conversão e render.
- A licença efetiva depende de `./configure` e bibliotecas: x264/x265 elevam a GPL; opções `nonfree` impedem redistribuição compatível.
- Antes de uso: registrar fonte do binário, versão, `ffmpeg -buildconf`, codecs, libs e obrigações.
- O binário local usado no smoke é `8.1.1-full_build-www.gyan.dev`, estático, com `--enable-gpl`, `--enable-version3`, `libx264` e `libx265`: serve somente como ferramenta de desenvolvimento e não foi aprovado como build redistribuível da Clicko.
- O adapter inicial `builtin.ffmpeg-proxy` já opera atrás de `MediaProxyProvider`, grava derivado com checksum/lineage e passou smoke H.264/AAC real. Isso valida a fronteira, não aprova o binário para produção.
- Headless, observável e cancelável por processo; progresso precisa ser parseado e normalizado pelo adapter.
- Multi-tenancy depende do worker/storage Clicko, não do FFmpeg.
- Saída: comandos reconstruíveis a partir do documento canônico; nunca fazer do filtergraph o formato do domínio.

### Fabric.js e Konva

- Ambos têm licença MIT e ecossistema browser; nenhum é necessário para o primeiro wrapper do canvas atual.
- Fabric possui serialização/SVG e backend Node com dependências nativas; Konva possui cena/eventos/transforms e adapters React.
- Spike futuro deve medir: texto PT-BR, máscaras, filtros, grupos, history, round-trip, 10 páginas, 100 camadas, memória, export e acessibilidade.
- Dados permanecem no `CreativeDocument`; JSON específico da engine é cache opcional.
- Decisão só após ADR comparativo. Não instalar ambos em produção.

### WhisperX

- Código BSD-2-Clause; usa faster-whisper/CTranslate2 e modelos de alignment/VAD/diarização que precisam de licença e acesso próprios.
- Documentação atual menciona modelo de diarização Pyannote sob CC-BY-4.0; tokens/termos do hub não são implicitamente aprovados.
- GPU é recomendável para throughput; CPU, PT-BR, diarização, memória e custo precisam de benchmark com mídia consentida.
- Headless é adequado, mas cancelamento/progresso/idempotência devem vir do worker Clicko.
- Saída: timestamps/palavras/speakers normalizados em contrato; payload WhisperX fica no lineage.

### OpenCut e OpenCut Classic

- O repositório principal está em rewrite com Rust/GPUI e shells web/API/desktop iniciais. No commit auditado, a rota web do editor ainda mostra `Coming soon` e o desktop é um shell de painéis; as promessas de Editor API, plugins, headless/batch render, scripting e MCP não podem fundamentar adoção hoje.
- O próprio projeto aponta o OpenCut Classic como versão utilizável. O Classic contém timeline, snapping, placement, group move/resize, keyframes, masks, effects, waveform, comandos/undo, migrations de storage e compositor Rust/WASM/WebGPU.
- O Classic foi arquivado e o README registra preview/export em refatoração. Não existe garantia de manutenção, API headless estável ou compatibilidade futura com o rewrite.
- Valor além da proposta: referência prática para timebase/frame accuracy, arquitetura de comandos, migração de documento local, correção de máscaras, keyframes e separação compositor/editor.
- Estratégia Clicko: projetar `CreativeDocument` em componentes selecionados, comparar com React Timeline Editor e HyperFrames, e trazer somente módulo MIT isolável que vença benchmark. O primeiro spike novo é a **Reality Lane**: markers/bookmarks e overlays localizados para ocorrências físicas, com commands/undo, snapping, keyframes/masks e hit testing onde necessário. Auth, banco, projeto, Zustand store e documento OpenCut não entram.
- Gates: 1.000/10.000 clipes, 20 tracks, snapping a frame, ripple, undo, teclado/a11y, memória, reconform proxy/original e paridade preview/render.

### Stack de inteligência de realidade

- **V-JEPA 2** é candidato de representação/predição, não “modelo de física pronto”. O adapter deve receber frames/proxies e devolver features/surpresa/estado normalizados; explicações e decisões ficam fora dele. Pin de código, checkpoint, preprocessamento e datasets reabre licença e benchmark.
- **TAPIR**, **RAFT** e **Depth Anything V2 Small** formam uma baseline permissiva de trajetórias, movimento e profundidade aproximada. Nenhum sinal isolado prova gravidade, causalidade ou erro; eles alimentam `RealityModelV1` com confiança e lineage.
- **SAM 2** pode estabilizar entidades/máscaras, mas checkpoint e cadeia precisam de manifest antes de dados privados.
- **Physics-IQ** ajuda a desenhar experimentos reais/multiview e métricas. **IntPhys2**, **MVPBench** e **CausalVQA** ajudam a definir propriedades, pares mínimos e contrafactuais, mas não são automaticamente material comercial reutilizável.
- **CoTracker**, **Perspective Fields**, variantes Base/Large/Giant de Depth Anything V2 e o checkpoint original do **VGGT** são bloqueados por termos não comerciais. O sistema deve permitir substituí-los por adapters permissivos ou implementação própria.
- Nenhum benchmark público será o único gate: haverá corpus Clicko privado, holdout, técnicas cinematográficas declaradas, localização temporal, calibração, abstenção, false-block e revisão humana.
- PGV-0 foi materializado em contratos e policies sob `benchmarks/studios/reality/`. Os pins acima entram nas policies como `review_required`; isso congela o protocolo sem fingir que pesos ou cadeia transitiva já foram homologados.

### Supervision

- É um toolkit model-agnostic, não um detector, segmentador ou modelo de física. `Detections` e seus conversores podem funcionar como anti-corruption layer efêmera antes de `RealityContributionV1`.
- Componentes úteis: adapters de output, NMS/NMM, annotations, `PolygonZone`/`LineZone`, dataset converters e métricas mAP/precision/recall/F1/confusion matrix.
- Valor além da proposta: overlays ligados a `evidence_id`, harness único de benchmark/troca de modelo e QA de safe areas/contagem sem usar VLM.
- O `ByteTrack` incluído está depreciado desde 0.28.0 e marcado para remoção em 0.31.0. Um spike Clicko não pode criar dependência nova nele; tracking permanece capability separada.
- O inventory `supervision-toolkit-artifacts-2026-08-27` está `incomplete`: fonte MIT aprovada, lock Linux minimizado e imagem/SBOM ainda ausentes. Worker continua com `providers: []`.
- Decisão: executar primeiro conversão/overlay/métricas em fixtures sintéticas; promover apenas módulos que vencem a baseline, sem persistir objetos Supervision.

### Remotion

- Site oficial informa licença gratuita apenas para indivíduos/organizações pequenas e licença empresarial/automação paga para empresas e produtos de render.
- A Clicko é um produto de automação/render; não presumir gratuidade pela disponibilidade do código.
- Pode ser útil para templates React, mas adiciona custo, Chromium e superfície operacional.
- FFmpeg/Pillow e o motor atual devem ser avaliados primeiro.
- Pelo critério atual de usar apenas open source, foi rejeitado antes do spike. O clone externo permanece apenas como evidência comparativa.
- Estratégia de saída: `VideoRenderProvider`; composição canônica não depende de componentes Remotion.

## Evidência de aquisição

- Trinta e oito repositórios foram clonados com histórico raso e Git LFS sem baixar os pesos/mídias grandes. Em 27/08/2026 entraram Supervision e PersonaPlex em `.candidate-build/sources/`, área ignorada pelo Git; nenhum peso PersonaPlex foi baixado ou teve licença aceita. Os demais clones continuam fora do monorepo e sem pesos ativados.
- Todos os demais clones ficaram limpos e com remote oficial registrado.
- Exceção reproduzível: o checkout V-JEPA 2 no Windows mostra nove arquivos modificados porque o upstream contém paths que diferem apenas por caixa (`vitG`/`vitg`). O commit/remote estão corretos; o benchmark futuro deve fazer checkout limpo em Linux. Não houve edição manual desses arquivos.
- Nenhum clone foi copiado para o monorepo da Clicko.
- HyperFrames reportou arquivos de baseline LFS inconsistentes com ponteiros durante o checkout; o código ficou limpo, mas os golden assets não são considerados evidência válida até um clone completo em ambiente de spike.
- Docker Desktop foi iniciado e o daemon respondeu na versão `29.1.3`.
- Telemetria do CLI HyperFrames foi desabilitada no ambiente de avaliação.
- O smoke próprio está em `C:\Users\edugu\Downloads\clicko-oss-evaluation\spikes\hyperframes-minimal`; o MP4 e o frame de inspeção permanecem fora do monorepo.
- O acesso SSH da VPS foi validado sem ler ou copiar a chave privada. A inspeção somente leitura encontrou 2 vCPUs, 956 MiB de RAM, ausência de GPU/Node/FFmpeg e seis contêineres Nexus ativos. A VPS foi rejeitada como worker de mídia para não criar contenção; detalhes de acesso não são registrados no repositório.

## Checklist antes de mudar uma decisão para “adotar”

### Candidato adiado — Voicebox (30/08/2026)

O usuário informou um projeto chamado Voicebox aberto no navegador local e pediu explicitamente
para avaliá-lo somente depois do plano/meta atual. URL exata e licença ainda não verificadas;
clonagem em 23 idiomas e comparações com ElevenLabs/WhisperFlow são alegações relatadas, não
capacidades comprovadas. Nenhum clone, peso, serviço ou provider foi instalado. Na avaliação futura,
identificar o repositório correto e comparar clonagem, ditado/transcrição, PT-BR, hardware, privacidade,
consentimento e cadeia de licenças com os adapters de voz existentes.

### Challenger local — YAMNet ONNX (31/08/2026)

- Uso restrito: preflight offline de foley/ambiência para o lote UGC sem voz; não é
  gerador de voz, aprovação automática nem provider da API.
- Export de terceiro: `anchor-flux/yamnet-onnx`, revisão
  `d8b2365b3cdaa367185a620305bd93683d8e3840`. Arquivos e SHA-256 no manifesto local
  `artifacts/models/yamnet-onnx-d8b2365/model-manifest.json`.
- Estado: `conversionProvenanceVerified=false`, `productionReady=false`. Paridade
  com checkpoint oficial, proveniência/licenças da cadeia e calibração ainda
  precisam de qualificação. A aquisição não significa adoção.
- Dependências opcionais fixadas em `backend/requirements-audio-audit.txt`;
  avaliação em `backend/scripts/audit_ugc_sound_asset.py`.
- Os sons candidatos de café tiveram resultados inconclusivos de fala/eventos;
  nenhum foi aprovado. Escuta humana e sincronismo com take continuam pendentes.
- Evidência e limites: `evidence/ASSISTED_VIDEO_EDITORIAL_CAPTIONS_AUDIT_2026-08-30.md`
  e `evidence/VIDEO_SOURCE_AUDIO_MUTE_AUDIT_2026-08-31.md`.

### Gate de adoção

1. Tag/commit fixado e SBOM de código, modelos, datasets e container.
2. Uso comercial SaaS e atribuição revisados.
3. Benchmark PT-BR com dataset consentido e critério de qualidade.
4. Hardware, latência, throughput e custo por artefato medidos.
5. Isolamento de tenant, retenção e exclusão demonstrados.
6. Retry, progresso, cancelamento e observabilidade integrados.
7. Provider fake e segundo adapter provam substituição.
8. Estratégia de saída e migração de artefatos documentada.
