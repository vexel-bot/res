# Clicko Studios — estratégia de IA, avatares e edição autônoma

**Data:** 2026-08-26  
**Status:** decisão de pesquisa e plano executável; nenhum provider ou peso foi ativado.  
**Escopo:** API de IA, voz PT-BR, catálogo inicial de seis apresentadores, Studio Replica, avatar, edição autônoma, motion e infraestrutura.  
**Documentos superiores:** `docs/CLICKO_STUDIOS_STRATEGY.md` e `docs/studios/STUDIOS_MEDIA_IDENTITY_MASTER_PLAN.md`.

## 1. Decisão executiva

É viável oferecer uma API própria da Clicko e usar modelos open source. Não é viável colocar os modelos pesados na VPS Oracle atual.

A arquitetura recomendada é híbrida e reversível:

1. A VPS atual continua sendo o **control plane**: autenticação, workspace, banco, filas, políticas, jobs, consentimento, custo, status e auditoria.
2. Modelos de voz, visão e avatar rodam em **workers GPU externos e efêmeros**, nunca nos containers existentes da VPS.
3. A Clicko expõe uma API única, assíncrona e provider-neutral; o cliente não conhece RunPod, Chatterbox, Qwen, EchoMimic ou qualquer SDK externo.
4. O primeiro mecanismo é validado com modelos de pesos abertos em workers próprios. APIs proprietárias ficam reservadas a comparadores de teto ou fallback posterior; continuam adapters substituíveis, nunca o domínio do produto.
5. O primeiro teste publicável não será “geração cinematográfica completa”. Será a cadeia controlada: **roteiro aprovado → voz → apresentador → composição determinística → QC → revisão humana**.

O primeiro stack de benchmark será:

- planejamento/copy: `Qwen3-4B-Instruct-2507` para volume, `Qwen3-30B-A3B-Instruct-2507` para planejamento/revisão, `Qwen3-30B-A3B-Thinking-2507` para escalonamentos difíceis e Kimi K2.5 apenas como challenger de teto multi-GPU;
- compreensão nativa de vídeo: `Qwen3-VL-4B/8B` em GPU externa, combinado a transcript, shots e sinais determinísticos; Gemini fica como comparador opcional posterior;
- voz clonada PT-BR: Chatterbox Multilingual V3 e pack `pt-BR` como candidato primário; OpenVoice V2 como challenger e Kokoro como baseline de voz stock;
- cabeça/apresentador: Ditto como candidato condicional depois de remover InsightFace; EchoMimicV3 Flash como candidato de meio-corpo/corpo depois de inventário completo de pesos e dependências;
- geração avançada: Wan2.2 Animate apenas depois do MVP, pois os fluxos 14B exigem uma classe de GPU e custo muito maior;
- render/motion: HyperFrames + FFmpeg como caminho principal; Motion Canvas para motion vetorial especializado; OpenTimelineIO somente como fronteira de import/export; OpenCut como referência de UX e componentes, não como núcleo do produto.

## 2. Método de pesquisa e qualidade da evidência

A pergunta foi tratada como uma **scoping review técnica**, acrescida de matriz de licenças, feasibility review e premortem.

Pergunta operacional:

> Qual combinação de API hospedada, modelos self-hosted e render determinístico permite validar seis avatares e uma réplica consentida em PT-BR, com qualidade publicável, custo mensurável e caminho comercial, sem transformar a VPS atual em worker pesado?

Critérios de inclusão:

- repositório, documentação, model card, licença ou artigo primário;
- capacidade útil para uma etapa identificável da cadeia;
- execução headless ou possibilidade real de encapsulamento;
- licença de código e pesos comercialmente auditável;
- informações mínimas de hardware e limitações;
- integração possível por contrato substituível.

Critérios de exclusão ou quarentena:

- somente demo, marketing ou screenshot;
- pesos não comerciais, OpenRAIL sob a regra vigente de open-source-only, container opaco ou cadeia de assets sem licença;
- dependência obrigatória de InsightFace sem substituição;
- termos territoriais ou limiares comerciais incompatíveis;
- ausência de caminho seguro para consentimento, isolamento, cancelamento e deleção.

Nível de confiança:

| Área | Confiança | Motivo |
| --- | --- | --- |
| inadequação da VPS atual para GPU/mídia pesada | alta | inspeção read-only do host e requisitos oficiais dos modelos |
| arquitetura control plane + workers externos | alta | compatível com o Kernel/jobs existentes e com execução assíncrona de GPU |
| Chatterbox como primeiro clone PT-BR | média-alta | licença/model card oficiais; qualidade Clicko ainda não medida |
| EchoMimicV3 Flash como primeiro challenger corporal | média | licença e sizing oficiais; cadeia transitiva e qualidade ainda não auditadas completamente |
| Ditto como candidato de baixa latência | média-baixa | proposta forte, mas pipeline oficial inclui InsightFace |
| editor autônomo sobre intermediários tipados | alta | converge com literatura e com o `CreativeDocument` já implementado |
| Qwen-first para copy/planejamento | média-alta | pesos selecionados Apache-2.0 e serving compatível; qualidade/custo pt-BR ainda não medidos |
| Kimi K2.5 como teto self-hosted | média-baixa | capacidade forte, mas distribuição de ~595 GB, TP8 H200 e licença modificada tornam o benchmark caro e juridicamente condicionado |
| qualidade/custo dos seis avatares | baixa antes do benchmark | não existem outputs Clicko reais nem avaliação cega ainda |

## 3. Por que a VPS não deve hospedar os modelos

A VPS inspecionada possui 2 vCPUs, aproximadamente 956 MiB de RAM, sem GPU e já executa seis containers do Nexus. Ela não comporta Chatterbox de forma segura junto dos serviços existentes, muito menos Qwen-VL, Ditto, EchoMimic ou Wan.

Mesmo um modelo “pequeno” introduziria:

- disputa de RAM/swap e risco de OOM;
- latência imprevisível da API e do banco;
- dependências CUDA/FFmpeg/Chrome incompatíveis com o host atual;
- maior blast radius para falha, atualização e segurança;
- impossibilidade de escalar voz, visão e render independentemente.

A regra é: **a VPS agenda e governa; workers executam**.

```text
Clicko Web
  → API Clicko na VPS
      → autorização, consentimento, quota e idempotência
      → PostgreSQL/Redis existentes
      → object storage privado por workspace
      → fila por capability
          ├─ media_cpu: FFmpeg + HyperFrames
          ├─ speech_gpu: Chatterbox/OpenVoice/ASR
          ├─ llm_gpu: Qwen text; Kimi somente em lane de teto
          ├─ vision_gpu: Qwen-VL/QC/segmentação
          └─ avatar_gpu: Ditto/EchoMimic/Wan
      ← artefatos + métricas + attestation + provenance
  → revisão humana
  → exportação/publicação
```

Para validação, um endpoint serverless de GPU com fila, retry e `workersMin=0` reduz operação ociosa. RunPod é uma opção inicial, não um acoplamento; o contrato Clicko precisa permitir trocar por outro fornecedor ou GPU dedicada.

### 3.1 Classes de worker para o laboratório

| Classe | Configuração de referência | Uso |
| --- | --- | --- |
| `media_cpu` | 8 vCPU / 16 GB RAM | FFmpeg, HyperFrames, thumbnails, waveform e QC técnico |
| `speech_gpu_small` | GPU 12–16 GB | Chatterbox/OpenVoice em benchmark sequencial |
| `llm_gpu_small` | GPU externa dimensionada após preflight | Qwen3-4B quantizado/servido para volume; memória, throughput e quantização precisam de benchmark |
| `llm_gpu_standard` | GPU externa de 48–80 GB ou configuração equivalente | Qwen3-30B-A3B Instruct/Thinking com contexto limitado e custo medido |
| `llm_gpu_ceiling` | nó multi-GPU H200 TP8 | Kimi K2.5 somente após o mecanismo Qwen passar; nunca default do MVP |
| `avatar_gpu_standard` | RTX 4090/A5000/A6000, 24 GB | EchoMimicV3 Flash e challengers de talking head |
| `avatar_gpu_large` | 48–80 GB | modelos 14B, alta resolução ou throughput avançado |

O laboratório começa serverless e mede cold start, fila, geração, encode, falha e custo por minuto final. GPU dedicada só passa a fazer sentido quando utilização sustentada e SLA superarem o desperdício de idle; essa decisão será tomada com telemetria, não por preferência de fornecedor.

## 4. Estratégia de modelos e APIs

### 4.1 Planejador, copy e direção criativa

Um LLM não renderiza nem edita pixels. Ele transforma contexto em artefatos tipados:

- `CreativeBriefV1`;
- `ScriptVersionV1`;
- `ShotPlanV1`;
- `EditProposalV1`;
- `MotionDirectionV1`;
- `QcCritiqueV1`.

Roteamento inicial:

| Tarefa | Primeira opção | Challenger | Regra |
| --- | --- | --- | --- |
| classificação, tags, variações curtas | Qwen3-4B-Instruct-2507 | API proprietária posterior | alto volume, schema rígido e teto de custo |
| roteiro, storyboard e revisão editorial | Qwen3-30B-A3B-Instruct-2507 | Qwen3-30B-A3B-Thinking-2507 | modelo precisa citar contexto/evidências e respeitar campos travados |
| caso ambíguo ou revisão crítica | Qwen3-30B-A3B-Thinking-2507 | Kimi K2.5 | Kimi só entra depois do Qwen e com autorização de custo multi-GPU |
| compreensão de vídeo completo | Qwen3-VL-4B/8B | Gemini video API posterior | nunca ser único árbitro de QC |

APIs hospedadas como GPT e Gemini não desaparecem do desenho: elas podem ser ligadas depois, pelo mesmo contrato, para medir o teto de qualidade ou cobrir indisponibilidade. Não são necessárias para provar a primeira cadeia. O adapter de texto recebe contratos/contexto delimitado; o adapter de vídeo recebe frames, transcript, shots e índices. Mesmo quando Gemini for comparado, sua amostragem padrão de 1 fps pode perder ação rápida, por isso a Clicko preserva sinais temporais próprios.

Os repositórios de pesos selecionados do Qwen usam Apache-2.0. O freeze textual usa 4B para volume e as variantes MoE 30B-A3B Instruct/Thinking para planejamento e raciocínio; a distribuição 30B pinada tem cerca de 61,08 GB. `Qwen3-VL` possui variantes 2B–235B e pode ser servido por vLLM em API compatível com o estilo OpenAI. O primeiro benchmark visual compara 4B e 8B em GPU externa.

Kimi K2.5 não é equivalente a um modelo Apache/MIT padrão: usa uma **Modified MIT License** com obrigação de exibir “Kimi K2.5” acima de 100 milhões de MAU ou USD 20 milhões de receita mensal. A distribuição oficial tem aproximadamente 595 GB e o guia self-host usa H200 TP8; além disso, o vídeo em self-host é descrito como experimental/limitado. Portanto, é challenger de teto após Qwen, com revisão jurídica e autorização explícita de custo, não baseline de texto nem de vídeo.

### 4.2 Voz PT-BR

| Candidato | Papel | Licença observada | Decisão |
| --- | --- | --- | --- |
| Chatterbox Multilingual V3 / pt-BR | clone zero-shot e voz expressiva | MIT no código e pack oficial pt-BR | **benchmark primário** |
| OpenVoice V2 | conversão de timbre sobre TTS-base | MIT | **challenger**, pois PT-BR não é idioma nativo V2 declarado |
| Kokoro | três vozes stock PT-BR e TTS-base | Apache-2.0; eSpeak exige tratamento GPL no runtime | **baseline stock**, não clone |
| F5-TTS pretrained | TTS/clone | código MIT, pesos oficiais CC-BY-NC | **rejeitar** para produção comercial |

O pack oficial Chatterbox pt-BR tem checkpoint identificado e se declara otimizado para português brasileiro e voice cloning. Isso é uma hipótese do fornecedor; a promoção depende de teste cego Clicko de naturalidade, similaridade, pronúncia, alucinação, custo e sobrevivência do watermark ao render final.

### 4.3 Rosto, performance e lip-sync

| Candidato | Resolve | Hardware declarado | Risco decisivo | Decisão |
| --- | --- | --- | --- | --- |
| Ditto | talking head controlável/baixa latência | upstream testa A100/TensorRT | checkpoints incluem detector/landmarks InsightFace | **condicional; substituir e rebenchmarkar** |
| EchoMimicV3 Flash | áudio → retrato/meio-corpo/corpo | 12 GB para Flash; 16/24/80 GB testados | RetinaFace e cadeia Wav2Vec2/CLIP/Wan a inventariar | **challenger principal em ambiente isolado** |
| LivePortrait | pose/expressão/retarget | benchmark upstream em RTX 4090 | licença alerta sobre detectores InsightFace não comerciais | **condicional à substituição** |
| Wan2.2 Animate | character animation/replacement | 24 GB para TI2V-5B; fluxos 14B tipicamente 80 GB | custo, latência e complexidade | **horizonte avançado** |
| MuseTalk | lip-sync sobre vídeo | V100/RTX conforme fluxo | pesos OpenRAIL e cadeia auxiliar | **rejeitado na regra vigente** |
| LatentSync | lip-sync por difusão | mínimo declarado de 18 GB em versão auditada | pesos OpenRAIL++ + InsightFace | **rejeitado na regra vigente** |
| HeyGem / Duix | aplicação de avatar | GPU/containers opacos | licenças comunitárias e limiar comercial divergente | **rejeitados; somente referência** |
| Wav2Lip | lip-sync | variável | repo/pesos oficiais proíbem uso comercial | **rejeitado** |

Não há hoje um pipeline completo de avatar “aprovado”. Há candidatos para benchmark. O primeiro vencedor será o que passar a cadeia inteira, não o que tiver a melhor demo.

## 5. Jornada “colocar o rosto e o anúncio sair pronto”

### 5.1 Matrícula

1. Explicar finalidade, marcas, canais, duração, disclosure, retenção e revogação.
2. Registrar consentimentos separados para `face.capture`, `voice.clone`, `avatar.generate` e `publish.synthetic`.
3. Fazer desafio de liveness e frase aleatória; liveness reduz fraude, não prova autorização sozinho.
4. Capturar rosto frontal, giros, expressões e, se necessário, meio-corpo/corpo; coletar voz limpa separadamente.
5. Executar QA de foco, luz, oclusão, terceiros, clipping, ruído, múltiplos speakers e duração.
6. Criar `IdentityVersion` e `VoiceVersion` imutáveis, com hashes, escopo e expiração; nenhuma payload interna do motor vira o domínio.

### 5.2 Produção

1. Direção cria 2–4 conceitos e o usuário escolhe um.
2. Editorial gera copy, pronúncia, beats, CTA e `ShotPlan`.
3. Voz é gerada e aprovada antes do vídeo.
4. `AvatarProvider` produz performance com identidade/versionamento fixados.
5. Cenário, máscara, B-roll, produto, captions, música e overlays entram como tracks independentes.
6. O editor autônomo propõe cortes e motion; um reducer determinístico aplica operações válidas ao `CreativeDocument`.
7. HyperFrames/FFmpeg renderizam a revisão fixada.
8. QC técnico, identidade, lip-sync, continuidade, realidade, marca, direitos e texto produzem relatórios separados.
9. A revisão humana compara source, áudio, composição e resultado; só então exporta.
10. Export registra ingredients/actions e prepara Content Credentials/C2PA; revogação bloqueia novo uso e aciona a DAG de deleção.

## 6. Catálogo inicial de seis avatares

O catálogo não será formado por rostos raspados da internet. As identidades devem vir de seis performers contratados com digital-replica release ou de personagens originais cujos direitos pertençam à Clicko. No laboratório privado, voluntários da equipe podem participar somente com consentimento específico e expiração curta.

Especificação v0 do catálogo:

| ID | Apresentação | Faixa | Direção de performance | Voz | Uso de teste |
| --- | --- | --- | --- | --- | --- |
| `AV-M-01` | homem | 25–34 | conversacional, próximo, sorriso leve | quente/neutra | problema → solução |
| `AV-M-02` | homem | 35–44 | energético, demonstração de produto | direta/dinâmica | demo |
| `AV-M-03` | homem | 45–55 | calmo, seguro, autoridade sem rigidez | grave/moderada | oferta de maior consideração |
| `AV-F-01` | mulher | 25–34 | storytelling, espontânea | quente/expressiva | depoimento narrativo |
| `AV-F-02` | mulher | 35–44 | ritmo alto, foco em benefício | clara/dinâmica | hook/performance |
| `AV-F-03` | mulher | 45–55 | precisa, premium, acolhedora | neutra/elegante | prova/CTA premium |

O casting deve variar tons de pele, cabelo, formato de rosto e energia de câmera sem associar demografia a profissão ou valor. Os IDs não impõem nomes, sotaques ou estereótipos; isso será decidido com casting e revisão de representação.

Cada avatar terá uma cápsula:

- identidade e versão;
- release, territórios, marcas, canais, contextos proibidos, prazo e revogação;
- fotos/vídeos/voz de origem e respectivos checksums;
- modelo, adapter, parâmetros e assets derivados;
- cenários, enquadramentos, roupas e expressões aprovadas;
- voz e dicionário de pronúncia;
- disclosure e política de publicação;
- previews aprovados e histórico de uso;
- plano e recibo de deleção.

## 7. Benchmark dos seis avatares

O benchmark será incremental para não gastar GPU antes de validar a cadeia.

### Rodada A — smoke privado: 6 outputs

- 6 avatares;
- 1 copy comum de 15 s;
- cenário “Studio neutro”;
- plano médio, 9:16;
- sem publicação.

Objetivo: provar contracts, storage, consentimento, job, voz, avatar, render, QC, review e cleanup.

### Rodada B — comparação criativa: 24 outputs

- 6 avatares × 4 arquétipos de copy;
- `problema-solução`, `depoimento`, `demo`, `oferta`;
- mesma duração/cenário para isolar a performance.

Objetivo: selecionar correspondência entre voz, energia, copy e identidade sem confundir qualidade do motor com qualidade do roteiro.

### Rodada C — matriz completa: 96 outputs

- 6 avatares;
- 4 arquétipos;
- 2 durações: 15 s e 30 s;
- 2 cenários: Studio neutro e contexto de produto.

Objetivo: medir robustez, custo e variância. Os mesmos scripts, seeds quando suportadas, codecs, loudness e assets devem ser congelados por versão.

### Métricas e gates

| Dimensão | Métricas |
| --- | --- |
| voz | preferência cega, naturalidade/MOS, similaridade percebida, WER, pronúncia de marcas/números, off-script, repetição, watermark |
| rosto/avatar | preservação de identidade, A/V sync, flicker, pose, olhos, dentes, boca, mãos/corpo, fundo, taxa de regeneração |
| anúncio | clareza do hook, tese, benefício, CTA, consistência de marca, segurança de claims |
| técnico | tempo de fila, tempo de geração, RTF, VRAM pico, falha/retry, tamanho, custo por minuto final |
| governança | consentimento válido, rights manifest, lineage, isolamento, cleanup, disclosure e revisão |
| realidade | horizonte, contato, oclusão, escala/profundidade, continuidade, trajetória e intenção cinematográfica declarada |

Regras:

- pelo menos três avaliadores humanos; pacote cego quando possível;
- nenhum missing value vira zero ou aprovação;
- métricas faciais não usarão silenciosamente pesos InsightFace não comerciais;
- um modelo não pode ser juiz único do próprio output;
- falha crítica de consentimento, direito, identidade, texto ou QC impede publicação independentemente da média;
- o vencedor é promovido com digest exato de imagem/pesos/policy, nunca pelo nome genérico do modelo.

## 8. Editor autônomo: arquitetura de especialização

O sistema não precisa de um “agente mágico especialista em tudo”. Ele precisa de uma cadeia de papéis com entradas, saídas, ferramentas e rubricas explícitas. Vários papéis podem compartilhar o mesmo modelo; a especialização vem de contratos, exemplos, memória correta, ferramentas e avaliação.

| Papel | Responsabilidade | Saída permitida |
| --- | --- | --- |
| Creative Director | intenção, público, formato e tese | `CreativeBriefV1` |
| Copy/Hook | hook, beats, claims, CTA e variações | `ScriptVersionV1` |
| Media Analyst | shots, transcript, áudio, objetos, qualidade e evidência | `MediaIndexV1` |
| Story/Shot Planner | arco, selects, cobertura e ordem | `LStoryboardV1` |
| Edit Decision Agent | trim, split, reorder, J/L cut, B-roll e captions | `EditProposalV1` |
| Motion Director | hierarquia, entrada/saída, curvas, ritmo e transições | `MotionGraphV1` |
| Audio Mixer | loudness, ducking, pausas, música e SFX | `AudioMixProposalV1` |
| Brand Guardian | tokens, safe areas, legibilidade e exceções | `BrandQcV1` |
| Reality/Continuity | física, causalidade, oclusão, identidade e continuidade | `PhysicalPlausibilityEvaluationV1` |
| Rights/Consent | licenças, consentimento, escopo e disclosure | `RightsDecisionV1` |
| Render/QC Critic | visual diff, codec, sync e defects | `QcReportV1` |

Regra central:

> Modelos propõem operações tipadas e citam evidências; o `CreativeDocument` valida/aplica; engines determinísticas renderizam.

O LLM/VLM nunca recebe permissão para:

- executar um comando FFmpeg arbitrário;
- escrever diretamente no storage ou banco;
- mudar consentimento, rights manifest ou approval;
- alterar um asset bloqueado;
- publicar;
- substituir toda a timeline sem diff e rollback.

Essa estrutura segue a direção dos trabalhos LAVE, Generative Timelines, L-Storyboard/StoryFlow e sistemas agentic de vídeo: descrição/indexação intermediária, planejamento explícito, operações de timeline interpretáveis e refinamento humano.

## 9. Linguagem de motion da Clicko

Motion não será um prompt aberto. Será uma gramática com tokens, presets e restrições editáveis.

### Princípios

- staging e hierarquia antes de efeitos;
- antecipação para preparar mudança;
- easing coerente com massa e intenção;
- arcos para movimento orgânico;
- follow-through e overlap em elementos secundários;
- overshoot/spring com limites de marca;
- continuidade espacial, direção de olhar e screen direction;
- ritmo de corte ligado à fala, música e densidade de informação;
- transições motivadas por movimento, forma, luz ou narrativa;
- motion blur e parallax somente quando sustentam profundidade;
- alternativas `reduce-motion` para UI/preview e templates acessíveis.

### Técnicas editoriais suportadas

- hard cut, match cut, cut on action, jump cut intencional;
- J-cut e L-cut;
- punch-in/out, reframe e safe-area por canal;
- speed ramp, slow motion, reverse, timelapse e freeze com intenção declarada;
- kinetic typography, captions por ênfase, lower thirds e end card;
- B-roll por evidência do roteiro;
- ducking, beat markers, risers, impacts e silêncio intencional;
- masks, text-behind-person, tracking e parallax;
- transições compartilhando direção/velocidade, não pacotes aleatórios.

### `MotionGraphV1`

O contrato deve conter:

- targets por layer/track e intervalo em frames racionais;
- propriedade animada, valor inicial/final e unidades;
- curva de easing ou spring versionada;
- duração, delay, stagger, overshoot máximo e motion blur;
- anchor, trajetória, máscara e relação pai/filho;
- gatilho semântico: palavra, beat, evento ou entrada de shot;
- intenção: emphasis, reveal, transition, continuity ou decoration;
- confidence, evidence refs e source agent;
- variante reduce-motion;
- renderer capabilities e fallback determinístico.

Tokens iniciais de marca:

- `motion.duration.instant/fast/base/slow`;
- `motion.ease.enter/exit/standard/emphasis`;
- `motion.spring.soft/medium/firm`;
- `motion.overshoot.max`;
- `motion.transition.maxPer10s`;
- `caption.wordsPerBeat`;
- `safeArea.9x16` e `safeArea.1x1`.

## 10. Frameworks de edição e motion

| Projeto | Papel Clicko | Decisão |
| --- | --- | --- |
| HyperFrames | projeção HTML, preview e render frame-exact | **motor open principal atrás de `VideoRenderProvider`** |
| FFmpeg | probe, transcode, filtros limitados, mix e encode | **primitiva determinística com build/SBOM aprovados** |
| Motion Canvas | motion vetorial 2D sincronizado a voice-over | **adapter especializado**, não timeline canônica |
| OpenCut rewrite | futura Editor API/plugin/headless/MCP | **acompanhar; capabilities ainda são roadmap** |
| OpenCut Classic | padrões de timeline, commands, snapping, masks e keyframes | **referenciar/importar seletivamente após benchmark** |
| OpenTimelineIO | interchange de informações editoriais | **import/export**, não armazena mídia e não substitui o documento |
| PySceneDetect | cuts, fades e segmentação inicial | **analyzer candidato**, BSD-3-Clause |
| SAM 2 / TAPIR / Depth Anything Small | masks, tracking e profundidade | **providers de análise condicionais aos manifests** |
| Remotion | referência de ergonomia/ecossistema React | **fora do core pela licença vigente** |

O HyperFrames é especialmente adequado porque captura cada instante por seek e permite render determinístico com HTML/CSS/JS comum. Mesmo assim, o HTML continua sendo uma projeção reconstruível; o `CreativeDocument` é a fonte de verdade.

### 10.1 Corpus de exemplos, sem copiar aplicações

- `hyperframes-launch-video`: referência de uma produção de aproximadamente 50 s com 17 subcomposições, captions, SFX, Lottie, shaders e Three.js. Como o repositório não oferece licença clara para a composição/mídia, serve apenas para decompor complexidade e criar fixtures próprias.
- OpenCut Classic: referência de commands/undo, snapping, keyframes, masks, waveform e hit testing. Os módulos só entram se forem isoláveis, mantidos e melhores que a implementação Clicko no benchmark.
- Motion Canvas examples: referência para explicadores, diagramas, gráficos e kinetic typography sincronizados a voice-over.
- LAVE: referência de coedição em que o usuário alterna entre agente e manipulação direta.
- Generative Timelines: referência para instruções de montagem que produzem uma timeline compacta e verificável.
- L-Storyboard/StoryFlow: referência para converter shots em linguagem estruturada e transformar geração divergente em seleção convergente.

O corpus Clicko derivado desses padrões será original: pelo menos 20 fixtures de motion, cada uma com documento, assets próprios, render dourado, tolerância visual, fallback e intenção registrada.

## 11. Contratos novos na sequência correta

Não é necessário criar um `CreativeDocumentV2` monolítico. A evolução pode ocorrer por contratos versionados e referências v1.x:

1. `MediaIndexV1`: shots, transcript, palavras, áudio, objetos, tracks, pose/depth/motion e evidência.
2. `LStoryboardV1`: beat narrativo, propósito, candidate shots, fala, visual, B-roll e constraints.
3. `EditProposalV1`: operações, timecodes/frames, evidências, confiança, impacto e rollback.
4. `MotionGraphV1`: animações, tokens, constraints, renderer fallback e reduce-motion.
5. `AvatarRenderRequestV1/ResultV1`: identidade/voz/consentimento fixados, cenário, motion, model digest e métricas.
6. `QcReportV1`: findings independentes por dimensão e decisão fail-closed.
7. `RenderManifestV1`: codecs, fps, duração, assets, checksums, engine, image digest e custo.
8. `ProvenanceManifestV1`: ingredients, actions, modelo, disclosure e binding ao export.

## 12. API pública da Clicko

Endpoints propostos:

```text
POST /api/v1/studios/v1/identity-enrollments
POST /api/v1/studios/v1/voice-profiles
POST /api/v1/studios/v1/media-indexes
POST /api/v1/studios/v1/edit-proposals
POST /api/v1/studios/v1/avatar-renders
POST /api/v1/studios/v1/video-renders
POST /api/v1/studios/v1/qc-evaluations
GET  /api/v1/studios/v1/jobs/{jobId}
POST /api/v1/studios/v1/jobs/{jobId}/cancel
POST /api/v1/studios/v1/reviews
```

Regras:

- async por padrão, com idempotency key;
- workspace e actor obrigatórios;
- inputs/outputs por signed URL curta e object refs, não base64 no banco;
- workers recebem job envelope assinado e credencial mínima;
- nenhuma porta de modelo é pública;
- logs nunca incluem mídia, embedding, chave, voz bruta ou prompt com dado sensível;
- cancelamento mata o subprocesso e remove output parcial;
- resultado liga provider/model/image/policy/asset digests;
- retry não cria nova identidade, cobrança ou publicação;
- webhook opcional assinado; polling continua disponível.

## 13. Opções de edição na experiência

O usuário poderá controlar:

- conceito, hook, copy, duração e CTA;
- avatar stock, Studio Replica ou UGC real;
- voz, energia, velocidade, pausas, ênfase e pronúncia;
- cenário, background, roupa aprovada, enquadramento e eye line;
- 9:16, 1:1, 4:5 e 16:9;
- densidade de B-roll e produto em cena;
- captions, palavras destacadas, safe area e acessibilidade;
- música, SFX, ducking e intensidade de transições;
- preset de motion e intensidade `sutil / equilibrada / alta`;
- brand kit, logo, lower third e end card;
- linguagem, regionalização e variantes de copy;
- comparar A/B, regenerar somente um shot e travar rosto/voz/cenário/copy;
- aceitar/rejeitar cada sugestão do agente;
- abrir timeline manual, restaurar versão e exportar OTIO quando aplicável;
- disclosure e destino de publicação.

## 14. Plano de execução incorporado à meta

### AI-0 — congelar protocolo e candidatos

- adicionar candidatos/pins ao registro OSS;
- criar artifact inventories para Qwen3 texto, Kimi K2.5, Qwen3-VL, Chatterbox, Ditto, EchoMimicV3, Wan2.2, Motion Canvas, OTIO e PySceneDetect;
- congelar corpus, métricas, thresholds e orçamento por rodada;
- jurídico aprova release, consentimentos e disclosure.

**Gate:** nenhum provider anunciado; manifests e policies são recomputáveis.

**Checkpoint executado em 26/08/2026:** policies canônicas foram adicionadas para avatar-ad
pt-BR (`c7cfb589...bd8e`) e planner de edição (`1e07d491...a8ed`), além do protocolo tipado
6/24/96 (`6bab1ba9...674f`). A policy open-source-first de planejamento/copy
(`88a37ca0...bc54`) acrescenta Qwen3 4B, Qwen3 30B-A3B Instruct/Thinking e Kimi K2.5 em ordem
de custo/complexidade. Dez inventories separam código, pesos, runtime e container para Chatterbox,
Qwen3 texto, Kimi, Qwen3-VL, Ditto, EchoMimicV3, Wan2.2, Motion Canvas, OTIO e PySceneDetect.
Todos falham fechados: nove estão `incomplete` e Ditto upstream está `rejected`; nenhum provider
foi anunciado e nenhum peso/container foi baixado ou ativado.

### AI-1 — inteligência por API e intermediários tipados

- `MediaIndexV1`, `LStoryboardV1` e `EditProposalV1`;
- adapters de planner/VLM com structured output;
- frame sampler próprio + transcript + PySceneDetect;
- diff, evidência, confidence e aplicação manual.

**Gate:** duas implementações produzem o mesmo contrato; operação inválida nunca altera o documento.

**Checkpoint parcial executado em 26/08/2026:** `MediaIndexV1`, `LStoryboardV1` e
`EditProposalV1` já existem como contratos provider-neutral testados, com lineage/evidence,
checksums e bindings fail-closed. `PlanningCopyRequestV1`/`ResultV1` e um adapter HTTP
OpenAI-compatible para vLLM/SGLang também foram provados contra transporte falso: o adapter fixa
modelo/revisão/lineage, exige JSON Schema, preserva restrições e bloqueia claims/evidências
inventadas. A aplicação exige decisão humana literal e hoje materializa somente `remove_range` no
caminho existente; captions, B-roll, gain e motion permanecem propostas visíveis e bloqueadas.
Nenhum endpoint real foi chamado. A capability dedicada `llm_gpu`, queue `studio.gpu.llm`, app
Celery exclusiva, manifest `102c8eda...c6c1` e imagem preflight também foram adicionados; o boot
registra somente o probe comum, exige GPU/isolamento e mantém `providers: []`. Persistência/API,
imagem funcional com vLLM/SGLang, run Qwen em GPU externa e uma segunda implementação ainda são
necessários para fechar o gate AI-1.

O preflight foi construído de verdade em Docker Desktop/Linux AMD64: digest local
`sha256:efc205d4...ab326`, usuário não-root `clicko`/UID 10001, label de providers `none` e
verificação interna bem-sucedida. O workflow manual produz OCI efêmero com SBOM/provenance e não
faz push. Essa evidência valida a fronteira; não valida CUDA/GPU, vLLM/SGLang nem inferência Qwen.

O corpus planning/copy agora materializa 60 fixtures sintéticas balanceadas, com revisão humana,
abstenção, claims/evidência, storyboard e payloads adversariais. O manifesto `4b625660...4698`
foi gerado fora do Git; nenhum modelo foi executado e nenhuma métrica de qualidade foi alegada.

O `MotionGraphV1` também foi materializado como intenção canônica de motion, com keyframes
frame-accurate, easing determinístico, unidades e limites por propriedade, constraints de design e
constraints físicas que só existem quando ligadas por digest/evidência a um `RealityModelV1`.
As projeções HyperFrames/Motion Canvas ficam `preview_only` enquanto o grafo não estiver revisado;
adapters de execução, paridade entre renderers e benchmark visual continuam pendentes.

### AI-2 — motion determinístico

- `MotionGraphV1` e tokens;
- presets Clicko e adapter HyperFrames;
- spike Motion Canvas para uma cena vetorial;
- preview/render parity, visual regression e fallback.

**Gate:** 20 fixtures repetem frames e áudio dentro da tolerância aprovada.

### AI-3 — voz real PT-BR

- construir imagens Linux/AMD64 do Chatterbox V3/pt-BR, OpenVoice e Kokoro;
- SBOM, provenance, no-egress, cleanup e watermark;
- benchmark cego de voz stock e clone consentido.

**Gate:** provider aprovado por licença, qualidade, custo, privacidade e deleção.

### AI-4 — seis apresentadores stock

- casting/release e cápsulas de identidade;
- rodada A de seis vídeos e rodada B de 24;
- escolher candidato avatar apenas após substituir dependências bloqueadas;
- UI de catálogo, locks e comparação.

**Gate:** seis perfis aprovados individualmente; nenhum “score médio” esconde falha de um avatar.

### AI-5 — primeira Studio Replica

- uma pessoa consentida;
- gravação-base + nova voz/lip-sync/cenário;
- side-by-side e review por intervalo;
- revogação e deleção física exercitadas.

**Gate:** anúncio privado aprovado pela pessoa; publicação ainda requer `publish.synthetic`.

### AI-6 — editor autônomo completo

- roles especializados, memory por projeto e rubricas;
- montagem, motion, áudio, captions e brand QA;
- 96 outputs do catálogo;
- avaliação humana e custo por minuto final.

**Gate:** supera baseline manual assistida sem aumentar critical defects, tempo total ou custo acima do teto.

### AI-7 — avatar avançado e escala

- EchoMimicV3/Wan Animate somente após AI-4/5;
- GPU dedicada versus serverless conforme utilização;
- batching, cache seguro, autoscaling e quotas;
- Content Credentials/C2PA no export.

**Gate:** licença transitiva, estabilidade temporal, mãos/corpo/cenário, custo e throughput aprovados.

## 15. Premortem

Supondo que o projeto falhou em seis meses, as causas mais prováveis seriam:

| Falha | Sinal precoce | Prevenção |
| --- | --- | --- |
| “modelo Apache” escondia peso/dependência não comercial | LICENSE do repo diverge do model card/container | inventory por artefato, SBOM, digest e gate jurídico |
| demo bonita, mas PT-BR artificial | nomes/números errados, MOS baixo e muitas regenerações | corpus local, dicionário de pronúncia e review cega |
| editor autônomo destrói intenção | timeline muda sem explicação ou rollback | propostas tipadas, evidence refs, diff e aplicação humana |
| VPS fica instável | swap/OOM, latência do banco, containers reiniciando | nenhum worker pesado na VPS; quotas e filas externas |
| custo explode | cold start, baixa utilização, regenerações e 14B cedo demais | smoke 6 → 24 → 96, 24 GB primeiro, custo por minuto como gate |
| avatar parece pessoa errada | drift entre cenas, dentes/olhos/mãos críticos | identity QC por trecho, locks, escopo de planos e fallback híbrido |
| consentimento não cobre o anúncio | scope genérico, ator/brand/canal ausentes | grants específicos, recheck no submit/export e revogação testada |
| agentes se contradizem | motion, copy e brand aplicam mudanças concorrentes | orchestrator, ownership de campos e prioridade de policies |
| o produto vira um fork difícil de manter | documentos HyperFrames/OpenCut viram fonte de verdade | `CreativeDocument` canônico e adapters descartáveis |
| VLM perde movimentos rápidos | análise falha em cortes/gestos abaixo da amostragem | shot detection, frames críticos, optical flow/tracks e human QC |

## 16. Evidências primárias selecionadas

- OpenAI model routing e capacidades: https://developers.openai.com/api/docs/models
- Gemini video understanding, arquivos, timestamps e limite de 1 fps: https://ai.google.dev/gemini-api/docs/video-understanding
- Qwen3-VL, variantes, vídeo e serving vLLM: https://github.com/QwenLM/Qwen3-VL
- Qwen3 texto e serving: https://github.com/QwenLM/Qwen3
- Qwen3-30B-A3B-Thinking-2507: https://huggingface.co/Qwen/Qwen3-30B-A3B-Thinking-2507
- Kimi K2.5, licença e deploy: https://github.com/MoonshotAI/Kimi-K2.5
- Chatterbox V3 e pack regional: https://github.com/resemble-ai/chatterbox
- Chatterbox pt-BR model card/checksum/licença: https://huggingface.co/ResembleAI/Chatterbox-Multilingual-pt-br
- Ditto: https://github.com/antgroup/ditto-talkinghead
- EchoMimicV3: https://github.com/antgroup/echomimic_v3
- Wan2.2 Animate: https://github.com/Wan-Video/Wan2.2
- LivePortrait e alerta InsightFace: https://github.com/KlingAIResearch/LivePortrait/blob/main/LICENSE
- HyperFrames: https://github.com/heygen-com/hyperframes
- OpenCut: https://github.com/opencut-app/opencut
- Motion Canvas: https://github.com/motion-canvas/motion-canvas
- OpenTimelineIO: https://github.com/AcademySoftwareFoundation/OpenTimelineIO
- PySceneDetect: https://github.com/Breakthrough/PySceneDetect
- LAVE: https://arxiv.org/abs/2402.10294
- Generative Timelines: https://arxiv.org/abs/2411.12293
- From Shots to Stories / L-Storyboard: https://arxiv.org/abs/2505.12237
- Prompt-Driven Agentic Video Editing: https://arxiv.org/abs/2509.16811
- RunPod Serverless endpoints: https://docs.runpod.io/serverless/endpoints/overview
- C2PA: https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html
- LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm

## 17. Limitações e decisões ainda necessárias

- nenhum output real de Qwen, Kimi, Ditto, EchoMimicV3, Wan2.2 ou Chatterbox pt-BR foi produzido nesta rodada;
- nenhum custo real de GPU foi medido;
- nenhuma licença transitiva foi juridicamente aprovada;
- os seis avatares são uma especificação de catálogo, não pessoas/rostos já adquiridos;
- os thresholds biométricos e perceptuais ainda precisam ser calibrados com avaliadores humanos;
- o teto de custo por vídeo, volume mensal e SLA ainda precisam de decisão de produto;
- este documento define requisitos técnicos de privacidade, mas não substitui parecer jurídico;
- nenhuma configuração da VPS, serviço, registry, provider, banco ou worker foi alterada.

## 18. Regra de promoção

Um candidato só sai de `evaluation` para `ready` quando o mesmo digest de código, pesos, runtime e policy comprovar:

1. licença comercial e direitos dos dados;
2. qualidade PT-BR e de identidade;
3. custo, latência, VRAM e throughput;
4. isolamento, retenção, revogação e deleção;
5. retry, cancelamento, progresso e observabilidade;
6. substituição por outro adapter;
7. QC e revisão humana;
8. rollback sem perder `CreativeDocument` ou lineage.

O objetivo não é provar que um repositório executa. É provar que uma pessoa autorizada recebe um anúncio bom, editável, rastreável e seguro — e que a Clicko consegue trocar o motor sem refazer o produto.
