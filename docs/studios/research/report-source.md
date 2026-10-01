# Clicko Studios — fonte canônica da pesquisa de mídia e identidade

**Data:** 2026-08-24  
**Status:** pesquisa técnica; decisões de adoção dependem dos gates do plano mestre.  
**Escopo:** criação de conteúdo, vídeo assistido, voz, identidade, avatar, cenário, render, fábrica e proveniência.

**Atualização especializada (26/08/2026):** `AI_AVATAR_AND_AUTONOMOUS_EDITING_STRATEGY_2026-08-26.md` aprofunda API própria open-source-first, workers self-hosted externos, comparadores hospedados posteriores, seis apresentadores, Studio Replica, edição autônoma, motion e o protocolo 6 → 24 → 96.

## 1. Pergunta de pesquisa

Como transformar o Clicko Studios em uma fábrica de conteúdo na qual uma pessoa pode fornecer contexto, materiais e — quando autorizado — rosto e voz, recebendo um anúncio editável, revisável e rastreável, sem acoplar o domínio Clicko a aplicações open source, modelos ou licenças específicas?

## 2. Critérios e suposições

- produto SaaS multi-tenant, inicialmente orientado a português brasileiro;
- somente componentes com uso comercial compatível podem chegar à produção;
- licença de código não prova licença de pesos, datasets, containers ou dependências;
- identidade sintética exige consentimento específico, revogável e auditável;
- revisão humana é obrigatória antes de publicação;
- a VPS atual permanece como control plane e não recebe processamento pesado;
- repositórios externos entram por capabilities e adapters, nunca como aplicação copiada para o monorepo.

## 3. Decomposição causal do produto

“Clonar o rosto” não é uma operação atômica. O resultado depende de:

1. prova de autorização e finalidade;
2. captura e controle de qualidade;
3. criação de uma versão de identidade;
4. geração ou conversão de voz;
5. geração de performance facial/corporal;
6. sincronização labial;
7. segmentação, cenário e composição;
8. render, QC, revisão, proveniência e exportação.

Isso produz três jornadas diferentes:

- **UGC real assistido:** a pessoa grava; Clicko organiza, transcreve, corta, legenda, aplica marca e cria variações.
- **Apresentador híbrido:** uma captura real ou vídeo-base recebe nova voz e/ou lip-sync, preservando controle editorial.
- **Apresentador sintético:** imagem/identidade e áudio geram uma performance; possui maior risco jurídico, reputacional e técnico.

## 4. Evidência primária consolidada

### Voz

- [OpenVoice](https://github.com/myshell-ai/OpenVoice) libera V1/V2 sob MIT e oferece clonagem de timbre e conversão cross-lingual. O próprio fluxo depende de um TTS-base; V2 não lista português entre os idiomas nativos. Portanto, OpenVoice é um conversor de timbre, não o pipeline PT-BR completo.
- [Chatterbox](https://github.com/resemble-ai/chatterbox) está sob MIT. O repositório oficial descreve Multilingual V3 com 23+ idiomas, clonagem por áudio de referência, modelo dedicado a português brasileiro e watermark PerTh embutido. É o candidato primário de benchmark zero-shot PT-BR.
- [Kokoro](https://github.com/hexgrad/kokoro) e o [model card Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) estão marcados Apache-2.0; a pipeline oficial inclui `pt-br` e três vozes brasileiras. É candidato a TTS-base leve, não a clone completo de identidade.
- Piper oferece vozes `pt_BR`, mas o código atual é GPL-3.0 e cada voz possui licença própria. Só pode ser considerado como serviço isolado depois de revisão das obrigações.
- XTTS v2 suporta português, mas os pesos usam licença não compatível com o requisito de uso comercial aberto; fica rejeitado.

### Rosto, performance e lip-sync

- [MuseTalk](https://github.com/TMElyralab/MuseTalk) possui código MIT e o README declara uso comercial, mas o [model card oficial dos pesos](https://huggingface.co/TMElyralab/MuseTalk) usa CreativeML OpenRAIL-M e o SyncNet baixado pelo script vem de um [repositório OpenRAIL++](https://huggingface.co/ByteDance/LatentSync). VAE/Whisper/DWPose/face parsing foram identificados e fixados; o bloqueio OpenRAIL permanece. Altera a região da boca em vídeo existente, não cria identidade/performance completa e foi rejeitado sob a regra open-source-only.
- [LivePortrait](https://github.com/KlingAIResearch/LivePortrait) é uma base MIT para animação/retarget de retrato. A própria [licença](https://github.com/KlingAIResearch/LivePortrait/blob/main/LICENSE) alerta que os modelos InsightFace usados na detecção são apenas para pesquisa não comercial; produção exige substituí-los.
- [EchoMimic](https://github.com/antgroup/echomimic) é Apache-2.0 e produz retrato dirigido por áudio/landmarks. A distribuição depende de vários modelos auxiliares e foi testada pelos autores em GPUs de 16–80 GB; pesos e dependências precisam de inventário separado.
- [LatentSync](https://github.com/bytedance/LatentSync) tem código Apache-2.0, mas os [pesos 1.6](https://huggingface.co/ByteDance/LatentSync-1.6) são OpenRAIL++ e a inferência depende de InsightFace. É referência de lip-sync, não fallback operacional nem gerador de avatar; foi rejeitado para produção sob a regra open-source-only.
- Hallo/Hallo2 são alternativas de retrato dirigido por áudio; licença de código permissiva não encerra a auditoria de pesos e dependências.
- [InsightFace](https://github.com/deepinsight/insightface) declara modelos distribuídos para pesquisa não comercial e licenciamento separado para `inswapper`. Nenhum pipeline Clicko pode herdar silenciosamente esses modelos.

### Edição, mídia e render

- HyperFrames é Apache-2.0 e já foi provado em spike externo com projeção descartável do `CreativeDocument`, render determinístico e MP4 válido.
- `hyperframes-launch-video` não possui LICENSE na raiz; é corpus de referência, não fonte copiável.
- FFmpeg pode ser LGPL ou GPL conforme flags e bibliotecas da build. A build observada localmente é GPL e serve apenas ao desenvolvimento; produção exige imagem fixada, `-buildconf`, SBOM e parecer de redistribuição/serviço.
- Fabric.js e Konva são MIT; resolvem scene graph/canvas, mas não o documento canônico nem a UX Clicko.
- Lexical é MIT; serve à interação editorial, mas seu JSON não será a fonte de verdade do roteiro.
- wavesurfer.js é BSD-3-Clause; serve a waveform, regiões, captura e QA.
- React Timeline Editor é MIT; serve a gestos de timeline, sem assumir tracks canônicas.
- WhisperX é BSD-2-Clause; combina transcrição, alinhamento de palavras e diarização, mas os modelos auxiliares precisam de registro próprio.
- SAM 2 possui código Apache-2.0; checkpoints, dados e qualidade para pessoas/produtos precisam ser auditados antes da produção.
- Remotion possui licença própria restritiva; permanece referência arquitetural, não dependência.
- Vane é MIT e pode acelerar pesquisa citada; não substitui scoring nem evidência do Radar.
- [OpenCut](https://github.com/opencut-app/opencut) é MIT, mas está em uma reescrita inicial: a UI web ainda é placeholder e o desktop contém apenas o shell/painéis. O roadmap oficial promete Rust core, Editor API, plugins, headless, batch render e MCP; essas promessas não são capabilities entregues hoje.
- O [OpenCut Classic](https://github.com/opencut-app/opencut-classic) também é MIT e contém uma base material de timeline, snapping, keyframes, masks, effects, preview, armazenamento versionado e compositor Rust/WASM/WebGPU. Porém foi arquivado em 17/05/2026 e o próprio projeto alerta que export/preview estavam em refatoração.
- Decisão OpenCut: acompanhar o rewrite e usar o Classic como fonte seletiva de padrões/testes. Não adotar a aplicação, autenticação, banco ou documento; comparar seus módulos de timeline com o React Timeline Editor e seu compositor com a projeção HyperFrames.

### HeyGem e Duix

- Os clones locais HeyGem e Duix são clientes Electron quase equivalentes e não contêm o backend/modelo principal de avatar.
- Ambos chamam imagens Docker externas/opacas e fluxos que incluem Fish Speech; o backend não é uma base auditável dentro dos repositórios entregues.
- As licenças locais introduzem obrigação comercial acima de um limite de usuários e entram em conflito com números divulgados nos READMEs.
- [Fish Speech](https://github.com/fishaudio/fish-speech/blob/main/LICENSE) exige acordo separado para qualquer uso comercial, inclusive serviço hospedado.
- Decisão: rejeitar integração e containers; aproveitar somente ideias de captura, fila e composição em ambiente de referência.

### Lei e proveniência

- A [LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm) classifica dado biométrico ligado a pessoa natural como dado pessoal sensível e exige finalidade, necessidade, transparência, segurança e base legal; quando consentimento for a base, ele deve ser específico, demonstrável e revogável.
- A especificação [C2PA 2.4](https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html) fornece estrutura de proveniência, ingredientes e ações. Ela prova a cadeia declarada, não a veracidade material do anúncio.
- O [EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj?locale=en) introduz transparência para conteúdo sintético/deepfake; o produto deve nascer pronto para disclosure mesmo quando o lançamento inicial for no Brasil.

## 5. Evidência do sistema Clicko atual

- `CreativeDocumentV1` já representa visual, carrossel, vídeo ou presenter e possui páginas, layers, tracks genéricas, assets, lineage, review e exports.
- `VideoRenderRequestV1`/`VideoRenderResultV1` e `VideoRenderProvider` já estabelecem a primeira fronteira de render.
- `StudioGenerationJob` persiste estado, capability, idempotência, cancelamento e retry; filas isoláveis e o worker `media_cpu` foram comprovados localmente, enquanto workers GPU externos ainda não foram provisionados.
- uploads privados, object storage/lineage, ingest, FFprobe, proxy e contratos de lifecycle já existem; rollout S3/multipart em produção e reconform proxy/original permanecem gates.
- a VPS existente possui 2 vCPU, menos de 1 GB de RAM e não possui GPU/FFmpeg/Node; hospeda serviços Nexus saudáveis e não deve receber workers de mídia.

## 6. Inferências de arquitetura

- prioridade comercial: UGC real assistido antes de clone de identidade;
- clonagem inicial deve ser zero-shot e versionada, sem treinamento por usuário;
- Chatterbox V3 PT-BR deve enfrentar OpenVoice + Kokoro no benchmark de voz, porque os dois últimos compõem uma pipeline em vez de um clone completo;
- LivePortrait + detector comercialmente compatível é candidato a movimento; não há lip-sync aprovado porque MuseTalk e LatentSync falharam a regra open-source-only; EchoMimic/Hallo permanecem laboratório avançado;
- cenário é uma capability independente: SAM 2 para máscaras/tracking, HyperFrames/FFmpeg para composição, e assets próprios/licenciados como primeira fonte;
- todo output sintético deve carregar lineage, disclosure e manifest C2PA quando tecnicamente disponível;
- identidade/voz não podem ficar dentro do `CreativeDocument`: o documento guarda refs para versões imutáveis e autorizadas.
- OpenCut aumenta a confiança de que timeline, keyframes e compositor podem ser componentes separados. A Clicko deve importar apenas módulos/ideias que vencem benchmark e se ajustam ao `CreativeDocument`, nunca criar um fork do editor completo.

## 7. Lacunas que exigem experimento

- qualidade real do Chatterbox V3 e do modelo dedicado `pt-br` em sotaques, números, siglas e nomes de marca;
- semelhança e preservação de prosódia em Chatterbox versus OpenVoice+Kokoro;
- licença exata e transitiva do futuro detector LivePortrait, EchoMimic, Hallo, WhisperX e SAM 2; MuseTalk e LatentSync já falharam o gate atual;
- detector/landmarks substituto do InsightFace com uso comercial permissivo;
- VRAM, latência, cold start e custo por minuto em hardware contratado;
- comportamento em diferentes tons de pele, idades adultas, óculos, barba, oclusão e movimento;
- resistência de watermarks após render, recorte, compressão e publicação;
- base legal e texto final de consentimento, a serem revisados por jurídico.

## 8. Conclusão de pesquisa

Os open sources eliminam grande parte da implementação de baixo nível, mas não resolvem produto, integração, licença, consentimento, QA, multi-tenancy, custo e operação. A vantagem da Clicko virá da linha de produção governada e do contexto de marca, não da posse de um único modelo.

## 9. Atualização open-source-first para inteligência

### Resposta direta

É viável validar a API de inteligência da Clicko sem começar por GPT ou Gemini. O mecanismo inicial deve usar, nessa ordem:

1. `Qwen3-4B-Instruct-2507` para classificação, copy curta e volume;
2. `Qwen3-30B-A3B-Instruct-2507` para brief, roteiro e revisão;
3. `Qwen3-30B-A3B-Thinking-2507` para raciocínio difícil;
4. Kimi K2.5 somente como comparação de teto, depois que o mecanismo Qwen estiver funcionando;
5. `Qwen3-VL-4B/8B` para vídeo, sempre complementado por transcript, shot detection, frames críticos e sinais temporais determinísticos.

GPT/Gemini permanecem adapters opcionais para comparação de qualidade ou fallback posterior. A VPS Oracle não recebe esses modelos: ela conserva API, autorização, filas, políticas e auditoria; a inferência roda em workers GPU externos e descartáveis.

### Evidência e limites

- Os model cards pinados do Qwen3 4B e 30B usam Apache-2.0. A variante Thinking possui 30,5 bilhões de parâmetros totais, 3,3 bilhões ativos e distribuição oficial de aproximadamente 61,08 GB; vLLM e SGLang expõem endpoint compatível com OpenAI.
- O repositório de referência Qwen3 não contém `LICENSE` raiz no commit auditado. Portanto, os pesos pinados podem avançar no gate de licença, mas código auxiliar do repositório não é automaticamente aprovado.
- Kimi K2.5 tem cerca de 595 GB, 1T de parâmetros totais/32B ativos e guia oficial self-host em H200 TP8. Sua Modified MIT permite uso comercial, mas cria obrigação de UI acima de 100M MAU ou USD 20M de receita mensal; revisão jurídica permanece obrigatória.
- O caminho self-hosted de vídeo do Kimi é descrito como experimental/limitado no material oficial. Kimi não substitui o primeiro benchmark de Qwen3-VL.
- Nenhuma afirmação de qualidade pt-BR, latência ou custo é resultado observado. Nenhum peso foi baixado ou executado nesta etapa.

### Matriz de lacunas

| Lacuna | Evidência atual | Experimento necessário | Gate de saída |
| --- | --- | --- | --- |
| qualidade de copy pt-BR | apenas model cards/benchmarks gerais | corpus sintético mínimo de 60 casos + três revisores nativos | MOS ≥ 4,0; claims sem evidência = 0 |
| schema e segurança | contratos/policy congelados | outputs estruturados, prompt injection e abstention | validade 100%; controles 100% |
| hardware Qwen 4B/30B | tamanhos e serving oficiais | preflight em GPU externa, quantizações separadas | sem OOM; p95/custo dentro da policy |
| Kimi como teto | requisitos multi-GPU e licença conhecidos | executar somente se Qwen deixar lacuna material | ganho justifica custo e gate jurídico |
| vídeo rápido/temporal | VLM pode perder eventos curtos | Qwen3-VL + sampler/shot/flow/tracks | evidências/timecodes e false-block aprovados |
| operação comercial | nenhum container promovido | lock Linux, SBOM, provenance, no-egress e cleanup | inventory `approved` + worker atestado |

### Decisão

Congelar o benchmark open-source-first e manter todos os inventories `incomplete` e os manifests de provider vazios. O contrato e o adapter HTTP provider-neutral para vLLM/SGLang já foram testados com transporte falso. A capability `llm_gpu`, sua fila, app Celery, manifest e imagem preflight isolada também foram materializados e verificados sem endpoint, runtime de inferência ou peso real. O build Linux AMD64 local resultou em imagem não-root com digest `sha256:efc205d4...ab326` e provider label `none`; um workflow manual prepara OCI com SBOM/provenance sem push. O corpus de 60 fixtures sintéticas foi preparado fora do Git e ligado ao manifesto `4b625660...4698`, mas ainda não executado. O próximo incremento é construir a imagem Qwen funcional, atestá-la e executar esse corpus em GPU externa; Kimi não deve consumir orçamento antes de uma lacuna comprovada no Qwen.
