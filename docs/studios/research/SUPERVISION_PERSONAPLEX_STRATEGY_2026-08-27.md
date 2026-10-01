# Clicko Studios — estratégia Supervision e PersonaPlex

**Data de corte:** 27/08/2026  
**Escopo:** análise de código, arquitetura, licença, operação, segurança e encaixe no produto.  
**Pins auditados:** Supervision `0.30.1` / `5f25aa0ee6dc22891415b6e3d2e1689ce7a32952`; PersonaPlex `3428dfd95309a7f3c84fd93259ded0f810d1ff91`; modelo PersonaPlex `fdaf4090a61cb315c138a1faee287ffd6c716309`.  
**Regra preservada:** nenhum peso baixado, nenhuma licença aceita, nenhum provider anunciado, nenhuma VPS alterada e nenhum dado humano usado.

## 1. Decisão executiva

As duas tecnologias agregam, mas em camadas e tempos diferentes:

| Projeto | O que realmente é | Decisão Clicko | Por quê |
| --- | --- | --- | --- |
| Supervision | toolkit Python model-agnostic para normalizar detecções, métricas, zonas, anotação, datasets e utilidades de vídeo | **encapsular em spike prioritário**, sem ativação | código MIT, maduro e útil para reduzir plumbing; não é detector, world model nem motor de física. |
| PersonaPlex | modelo e servidor speech-to-speech full-duplex com prompt textual de papel e prompt de voz | **rejeitar o checkpoint sob a política atual; referenciar padrões** | código MIT, mas pesos sob licença customizada NVIDIA, acesso condicionado, inglês-only e classe A100/H100; não resolve narração PT-BR de anúncios. |

Supervision entra como detalhe descartável do worker de visão. `RealityContributionV1`, `RealityModelV1`, os checksums e o lineage continuam sendo a linguagem Clicko. PersonaPlex não entra no `VoiceCloneProvider` usado para render de anúncio: essa capability continua comparando Chatterbox V3/pt-BR, Kokoro e OpenVoice. Se no futuro existir um produto de conversa ao vivo, ele terá um port separado, `DuplexConversationProvider`, e não reutilizará diretamente o servidor upstream.

## 2. Método da pesquisa

### 2.1 Classificação

- **Use case:** technology assessment + architecture + evidence synthesis.
- **Pergunta:** quais partes dos dois repositórios reduzem trabalho real no Clicko Studios sem contaminar o domínio, violar a política open-source-only ou criar risco biométrico/operacional?
- **População:** vídeo UGC, Reality Lane, benchmarks de visão, voz PT-BR renderizada e possíveis experiências conversacionais.
- **Intervenção:** adotar bibliotecas/arquiteturas upstream atrás de adapters Clicko.
- **Comparador:** OpenCV e contratos próprios já implementados; Chatterbox/Kokoro/OpenVoice na voz; nenhum produto full-duplex atual.
- **Outcomes:** fidelidade de contrato, qualidade mensurável, latência/custo, segurança, licença, isolamento, saída reversível e esforço evitado.

### 2.2 Evidência incluída

Foram priorizados repositórios oficiais fixados por commit, código executável, metadados de pacote, model card oficial, artigo científico oficial e licença do fornecedor. Popularidade foi observada apenas como sinal de manutenção, nunca como critério de adoção. Claims de qualidade publicados pelos próprios autores foram tratados como evidência de fornecedor até reprodução Clicko.

### 2.3 Evidência excluída

- demos e opiniões de terceiros como prova de qualidade;
- números de benchmark sem protocolo/fonte primária;
- inferir licença dos pesos a partir da licença do código;
- inferir suporte PT-BR a partir de generalização em inglês;
- executar modelos ou aceitar termos sem os gates do produto.

## 3. Supervision em profundidade

### 3.1 Proposta e anatomia

O Supervision é uma biblioteca de utilidades, não um modelo. No pin estável auditado:

- `src/supervision/detection/core.py`: `Detections`, conversores de outputs, NMS/NMM e metadados alinhados por detecção;
- `detection/tools` e `line_zone.py`: zonas, contagem, suavização, slicing e sinks;
- `annotators`: overlays composáveis para caixas, máscaras, labels, traces e heatmaps;
- `dataset`: leitura/conversão YOLO, COCO, Pascal VOC e outros formatos;
- `metrics`: mAP, precision, recall, F1 e confusion matrix;
- `utils/video.py`: metadata, leitura e escrita de vídeo;
- `tracker/byte_tracker`: implementação ainda presente, porém depreciada desde `0.28.0` e marcada para remoção em `0.31.0` em favor do pacote externo `trackers`.

O núcleo depende de Python 3.10+, NumPy, SciPy, Pillow, matplotlib, PyAV e utilitários. OpenCV deixou de ser instalado por padrão, embora módulos visuais ainda o carreguem quando necessário. Isso favorece um lock minimizado por subset, não `pip install` irrestrito em todo worker.

### 3.2 Valor direto para a Clicko

1. **Normalização na borda.** Converte resultados heterogêneos de detector/segmentador em uma estrutura temporária uniforme antes da projeção para `RealityContributionV1`.
2. **Evidência visual.** Annotators, crops e sinks podem produzir overlays de revisão e pacotes cegos sem reinventar desenho e serialização.
3. **Métricas reproduzíveis.** mAP, precision/recall/F1 e confusion matrix ajudam o benchmark dos analyzers; as métricas finais e thresholds continuam versionados pela Clicko.
4. **Zonas e contagem.** `PolygonZone` e `LineZone` ajudam safe areas, entrada/saída, permanência e QA de enquadramento.
5. **Datasets.** Conversão COCO/YOLO pode reduzir custo de preparação de corpora consentidos e sintéticos.
6. **Compatibilidade de modelos.** Conectores evitam adapters repetitivos, mas cada modelo conectado mantém licença, runtime e lineage próprios.

### 3.3 Valor além da proposta

- Uma `Detections` efêmera pode ser a **anti-corruption layer** entre modelos e contratos Clicko.
- Annotators servem como **explicabilidade operacional**, não só visualização de demo: cada overlay pode ligar `evidence_id`, frame e contribuição.
- Métricas e conversores permitem um **harness único de troca de modelo**, reduzindo lock-in do detector.
- Zonas e anchors podem alimentar **safe-area e composition QC** antes de qualquer modelo de linguagem visual.
- Dataset converters ajudam criar um corpus privado exportável sem tornar o formato upstream canônico.

### 3.4 O que não usar

- `Detections` como payload persistido ou API pública;
- `tracker_id` como identidade Clicko durável entre versões/jobs;
- Supervision como prova de gravidade, contato, causalidade ou física;
- conectores que baixam ou chamam modelos sem inventário separado;
- `sv.ByteTrack`, porque o próprio upstream já definiu sua remoção;
- utilidades de URL ou cache com egress aberto em jobs privados;
- annotators como substitutos do Review Room ou do `CreativeDocument`.

### 3.5 Fronteira alvo

```text
Detector / segmentador / tracker aprovado
  → adapter específico do modelo
  → Supervision Detections (somente memória do job)
  → normalização Clicko + validação de bounds/timebase
  → RealityContributionV1 + evidence assets + lineage
  → CanonicalContributionSceneProvider
  → RealityModelV1
  → policy / benchmark / Reality Lane / revisão humana
```

O digest registra o modelo e o código do adapter, não apenas a versão do Supervision. Toda box/mask deve usar coordenadas e frame range definidos no contrato Clicko; nenhum array NumPy é persistido por acidente.

### 3.6 Plano de adoção Supervision

| Fase | Entrega | Gate de saída |
| --- | --- | --- |
| `SV-0` — concluída | pin 0.30.1, licença, anatomia e inventory `incomplete` | código identificado; nenhum provider ativado. |
| `SV-1` | spike offline com conversor `Detections ↔ RealityContributionV1`, overlays por `evidence_id` e subset mínimo | round-trip sem perda semântica, bounds e timebase; sem egress e sem ByteTrack. |
| `SV-2` | benchmark sintético/consentido contra baseline OpenCV | fidelidade 100% das fixtures, determinismo, memória/throughput, zones e métricas conferidas por implementação independente. |
| `SV-3` | lock Linux com hashes, SBOM, notices, OCI digest e attestation | inventário `approved`, imagem read-only/non-root/no-egress e cancelamento sem leak. |
| `SV-4` | promoção gradual somente das capabilities vencedoras | registry explícito, shadow mode, rollback para baseline e zero mudança do contrato canônico. |

## 4. PersonaPlex em profundidade

### 4.1 Proposta e arquitetura

PersonaPlex é um finetune da arquitetura Moshi para conversa de áudio full-duplex. Ele recebe continuamente fala do usuário enquanto gera texto e áudio do agente. Antes da conversa, aplica dois prompts:

- **voice prompt:** áudio ou embeddings que condicionam timbre/estilo;
- **text prompt:** papel, cenário, fatos e persona em tags de sistema.

O fluxo usa o codec neural Mimi, um Temporal Transformer e um Depth Transformer. Entrada e saída são 24 kHz. O repositório oferece:

- servidor `aiohttp`/WebSocket em 8998 com stream Opus;
- cliente web de microfone/playback;
- execução offline determinística por seed, WAV de entrada e WAV/JSON de saída;
- 18 embeddings pré-empacotados: 9 femininos e 9 masculinos nas famílias NAT/VAR;
- CPU offload opcional, além do caminho GPU.

O model card declara inglês de entrada e saída, Linux/PyTorch e suporte A100/H100. O repositório do modelo possui um `model.safetensors` de aproximadamente 16,74 GB, além de tokenizer neural, tokenizer de texto e voice pack. Isso não é dimensionamento para a VPS atual.

### 4.2 O que ele resolve bem

- escuta e fala simultâneas;
- interrupção, barge-in, overlap, backchannel e troca rápida de turnos;
- consistência de papel por prompt textual;
- condicionamento de voz zero-shot;
- avaliação offline reprodutível;
- separação conceitual entre **o que o agente é/faz** e **como ele soa**.

O artigo reporta, para o checkpoint liberado, latência de interrupção de `0,240 s` no Full-Duplex-Bench e treinamento adicional com 7.303 conversas/1.217 horas de Fisher English. Esses são resultados do autor, não resultados Clicko.

### 4.3 O que ele não resolve para o produto atual

- não é TTS offline otimizado para narrar uma copy pronta;
- não é PT-BR;
- não edita vídeo, anima rosto nem sincroniza lábios;
- não oferece governança de consentimento, revogação, retenção ou deleção;
- não oferece isolamento multi-tenant ou quotas Clicko;
- não integra ferramentas externas no checkpoint/artigo atual;
- não cabe na VPS control plane e não substitui o speech worker renderizado.

### 4.4 Achados de código que impedem uso direto do servidor

1. Um `ServerState` mantém `Mimi`, `LMGen` e streaming state compartilhados; um `asyncio.Lock` serializa as conversas. O comportamento é coerente para demo de uma GPU, não para SaaS concorrente.
2. `voice_prompt` vem da query string e é unido ao diretório com `os.path.join`, sem prova de `resolve()` dentro da raiz. A fronteira precisa rejeitar traversal e aceitar somente IDs opacos.
3. Arquivos `.pt` de voice prompt são carregados com `torch.load`; objetos não confiáveis não podem chegar a esse caminho.
4. O servidor baixa weights, tokenizer, UI e `voices.tgz` automaticamente do Hugging Face, além de poder baixar `mkcert`. Produção Clicko exige build hermético e runtime no-egress.
5. Prompt textual, caminho de voz e IP/porta aparecem em logs. Isso conflita com minimização de PII e dados biométricos.
6. O Dockerfile roda como root, usa `uv:latest`, não fixa digest, não inclui healthcheck/SBOM/provenance e monta cache em `/root/.cache`.
7. O pacote restringe Torch `<2.5`, Hugging Face Hub `<0.25` e outras dependências antigas; uma imagem futura exigiria auditoria de CVEs e compatibilidade.

Esses achados não afirmam que o modelo é inseguro por definição. Eles provam que a aplicação upstream é uma demo/referência que precisa ser substituída por um sidecar mínimo antes de qualquer produto.

### 4.5 Licença e política

- Código: MIT no commit auditado.
- Pesos: NVIDIA Open Model License Agreement, marcada como `license: other` no Hugging Face e com aceite automático condicionado.
- A licença declara uso comercial e derivados, mas inclui condições sobre guardrails, Trustworthy AI, redistribuição/NOTICE, atualizações de licença, indenização e compliance.

Portanto, “commercially usable” não equivale a “open source OSI”. Sob a decisão explícita da Clicko de usar somente open source, o checkpoint fica **rejeitado**. Não se aceitou a licença nem se baixou qualquer byte de modelo.

### 4.6 Valor que pode ser aproveitado sem o checkpoint

- contrato de eventos full-duplex: `input_audio`, `agent_audio`, `agent_text`, `interrupt`, `backchannel`, `session_closed`;
- métricas de latência, turn-taking, interruption e backchannel;
- prompts de voz e papel como artefatos separados e versionados;
- modo offline determinístico para replay/auditoria;
- catálogo explícito de vozes stock, que inspira a seleção de seis avatares/vozes Clicko, sem copiar os embeddings;
- UX de sessão ao vivo como possível produto futuro de briefing, direção ou atendimento, não como render de anúncio.

### 4.7 Plano PersonaPlex

| Fase | Decisão | Gate |
| --- | --- | --- |
| `PX-0` — concluída | code pin registrado; checkpoint/modelo `rejected`; nenhum download/provider | política open-source-only preservada. |
| `PX-1` | incorporar apenas taxonomia/protocolo de duplex ao backlog futuro | nenhum código/modelo NVIDIA no runtime; privacy threat model aprovado. |
| `PX-2` | só se a política mudar: ADR jurídico e benchmark inglês em GPU externa isolada | aceite explícito da entidade, digests, sidecar reescrito, no-egress, safetensors/formatos seguros, concurrency e deleção. |
| `PX-3` | buscar primeiro alternativa permissiva com PT-BR para `DuplexConversationProvider` | naturalidade PT-BR, interrupção, custo e segurança vencem baseline; não confundir com TTS de anúncio. |

## 5. Mapa produto × tecnologia

| Componente Clicko | Supervision | PersonaPlex |
| --- | --- | --- |
| Video Studio UGC | overlays, zonas, normalização e métricas | nenhum uso direto. |
| Reality Lane | evidencia tracks/boxes/masks e facilita visualização | nenhum uso. |
| Compreensão física | fornece observações, nunca conclusões físicas | nenhum uso. |
| Benchmark de visão | dataset converters e métricas conferidas | nenhum uso. |
| Narração PT-BR | nenhum uso | rejeitado; inglês/conversa, não TTS de copy. |
| Clonagem de voz | nenhum uso | tecnologia relevante conceitualmente, checkpoint fora da política. |
| Avatar/presenter | ajuda tracking/QC quando combinado com modelos aprovados | voz conversacional apenas; não produz rosto/vídeo. |
| Agente de briefing ao vivo | nenhum uso | padrão arquitetural futuro; modelo atual não adotado. |
| Factory | batch/metrics via adapter, sem estado canônico | servidor upstream não é escalável/multi-tenant como está. |

## 6. Contratos e fronteiras recomendadas

### 6.1 Visão

Nenhum novo contrato canônico é necessário para o spike: `RealityContributionV1` já contém lineage, evidence, camera, entities, tracks, relations, events e hypotheses. O adapter Supervision deve ser uma implementação de worker que:

1. recebe asset ref/checksum e time map;
2. recebe resultados de modelo já auditado;
3. converte para `Detections` apenas em memória;
4. produz `RealityContributionV1` validado;
5. grava overlays como assets derivados tenant-scoped;
6. descarta arrays/objetos upstream ao terminar;
7. reporta limitações e abstém princípios não observados.

### 6.2 Voz conversacional futura

Não estender `SpeechSynthesisProvider` para esconder conversa full-duplex. Quando houver necessidade de produto comprovada, definir uma capability separada:

```text
DuplexConversationProvider
  start(session policy, role prompt ref, approved voice profile ref)
  push(audio frame)
  receive(agent audio/text events)
  interrupt(reason)
  close(retention receipt)
```

O contrato deve proibir caminhos de filesystem, tokens de hub, prompt biométrico inline e estado compartilhado entre workspaces. Eventos usam sequence number, monotonic timestamp, idempotency key e digest da policy.

## 7. Benchmark proposto

### 7.1 Supervision

- **adapter fidelity:** 100% das boxes, masks, classes, confidence e frame bindings nas fixtures;
- **determinismo:** JSON Clicko e overlays idênticos sob seed/config iguais;
- **cross-check:** precision/recall/F1/mAP comparados com uma implementação de referência em fixtures pequenas;
- **tracking:** não usar `sv.ByteTrack`; medir somente preservação de IDs provenientes de tracker aprovado;
- **zones:** casos de borda, anchors, entrada/saída e safe areas;
- **performance:** fps, pico de RAM, tempo de startup e tamanho do lock/image;
- **robustez:** empty detections, NaN/inf, boxes fora do frame, masks incompatíveis, cancelamento e arquivo corrompido;
- **segurança:** no URL fetch, no egress, paths tenant-scoped e cleanup verificado.

### 7.2 Conversa full-duplex futura

- time-to-first-audio, interruption latency p50/p95, overlap correto e false interruption;
- turn-order ratio, backchannel frequency, pause handling e smooth turn taking;
- WER/semantic accuracy, role adherence, speaker similarity e drift;
- naturalidade humana cega PT-BR e sotaques regionais;
- sessões simultâneas, VRAM por sessão, custo/minuto e recovery;
- red-team de prompt injection falado, reprodução de voz não consentida, traversal, arquivos maliciosos e vazamento em logs;
- revogação durante sessão, retenção zero/definida e recibo de deleção.

Nenhum número publicado pelo PersonaPlex é copiado como threshold Clicko. Thresholds serão congelados antes de um futuro run.

## 8. Contradições e resolução

| Tensão observada | Resolução |
| --- | --- |
| A página de docs do Supervision ainda menciona Python 3.9+, enquanto o `pyproject.toml` 0.30.1 exige 3.10+. | O pin executável manda: Python 3.10+. Confiança alta. |
| O nome/model card diz 7B, enquanto a UI do Hugging Face mostra 8B params e o safetensor tem ~16,74 GB BF16. | Não dimensionar por rótulo; usar bytes do revision pinado e benchmark de VRAM. Confiança alta na divergência, não na contagem exata. |
| O model card diz “ready for commercial use”, mas a política Clicko o rejeita. | Não há contradição jurídica: uso comercial pode ser permitido sob termos customizados; a política interna é mais restritiva e exige licença open-source. |
| O paper chama PersonaPlex de “open model”. | “Open model” não implica licença OSI. Registrar código e pesos separadamente. |
| Supervision oferece tracker, mas recomenda pacote externo. | Não iniciar nova integração sobre API depreciada; adapter deve aceitar IDs de tracker selecionado separadamente. |

## 9. Reliability audit e confiança

| Achado | Confiança | Base |
| --- | --- | --- |
| Supervision é MIT e model-agnostic. | alta | licença, README, docs e código pinado. |
| Ele reduz plumbing, mas não entende física. | alta | escopo do código e ausência de modelo de física. |
| `sv.ByteTrack` está depreciado. | alta | decorator, docstring e changelog no pin. |
| PersonaPlex é full-duplex, inglês e 24 kHz. | alta | repo, model card, código e paper. |
| Pesos não atendem à política open-source-only. | alta | licença customizada, tag `other` e política Clicko. |
| O servidor upstream não atende isolamento SaaS. | alta | inspeção do `ServerState`, lock, paths, logs, downloads e Dockerfile. |
| PersonaPlex teria valor futuro em conversa ao vivo. | moderada | inferência de produto; demanda Clicko ainda não validada. |
| Supervision melhorará velocidade de implementação. | moderada | hipótese a provar no spike SV-1/SV-2. |
| Qualidade/latência dos dois no corpus Clicko. | desconhecida | nenhum benchmark Clicko executado. |

## 10. Pre-mortem

1. **Supervision vira novo domínio.** Sintoma: JSON/NumPy upstream aparece no banco/API. Mitigação: teste que persiste apenas contratos Clicko e adapter de saída único.
2. **Modelo conectado herda aprovação da biblioteca.** Sintoma: “suportado pelo Supervision” usado como licença. Mitigação: inventory obrigatório por modelo/checkpoint/container.
3. **API depreciada cria retrabalho.** Sintoma: novo código usa `sv.ByteTrack`. Mitigação: lint/teste de import proibido e tracker como capability separada.
4. **PersonaPlex é usado como TTS de anúncio.** Sintoma: roteiro convertido em diálogo artificial ou inglês. Mitigação: manter `DuplexConversationProvider` separado de synthesis/clone.
5. **Servidor de demo chega à internet.** Sintoma: 8998 público, tokens HF e cache compartilhado. Mitigação: decisão `rejected`, sem Docker recipe/provider; qualquer reabertura exige sidecar do zero.
6. **Biometria vaza em prompt/log/cache.** Sintoma: path/nome/voz em query e log. Mitigação: IDs opacos, logs redigidos, object storage tenant-scoped, retenção e deletion receipt.
7. **“Open model” é tratado como OSI.** Sintoma: aceite automático em CI. Mitigação: artifact inventory bloqueado e revisão jurídica explícita.

## 11. Limitações

- Não houve benchmark de inferência, pois seria impróprio baixar pesos condicionados ou usar voz humana sem os gates.
- A licença não recebeu parecer jurídico; a decisão é de engenharia/política e falha fechada.
- Métricas do paper são autorreportadas e não foram reproduzidas.
- O Supervision foi auditado no release estável 0.30.1; o branch `develop` já aponta para 0.31.0.dev0 e pode alterar APIs.
- O inventário de dependências binárias e CVEs será feito somente se SV-1 provar valor.

## 12. Fontes primárias

1. [Supervision — repositório oficial](https://github.com/roboflow/supervision)
2. [Supervision 0.30.1 — release pinado](https://github.com/roboflow/supervision/releases/tag/0.30.1)
3. [Supervision — documentação oficial](https://supervision.roboflow.com/latest/)
4. [Supervision — licença MIT](https://github.com/roboflow/supervision/blob/5f25aa0ee6dc22891415b6e3d2e1689ce7a32952/LICENSE.md)
5. [PersonaPlex — repositório oficial](https://github.com/NVIDIA/personaplex)
6. [PersonaPlex — model card oficial](https://huggingface.co/nvidia/personaplex-7b-v1)
7. [PersonaPlex — artigo oficial](https://research.nvidia.com/labs/adlr/files/personaplex/personaplex_preprint.pdf)
8. [NVIDIA Open Model License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/)
9. [Full-Duplex-Bench](https://arxiv.org/abs/2503.04721)
10. [Moshi](https://arxiv.org/abs/2410.00037)

## 13. Estado entregue

- pesquisa, pins e decisões concluídos;
- inventory Supervision `incomplete`, sem provider;
- inventory PersonaPlex `rejected`, sem peso/provider;
- ADRs de fronteira incorporados;
- roadmap, registro open source, plano mestre e ledger atualizados;
- invariantes automatizadas: workers continuam com `providers: []`, PersonaPlex não pode ser anunciado e Supervision não pode virar contrato canônico por documentação/manifest.

O próximo trabalho autorizado não é “instalar os dois”: é executar `SV-1` em fixtures sintéticas. PersonaPlex só reabre por decisão explícita de política e necessidade de conversa ao vivo.

## 14. Execução SV-1/SV-2 e supply chain parcial — 28/08/2026

O trabalho autorizado foi executado sem alterar a decisão sobre PersonaPlex:

- `SupervisionDetectionAdapter` usa `sv.Detections` somente em memória e projeta boxes, masks, classes, confiança e IDs externos para `RealityContributionV1`;
- overlays PNG determinísticos carregam `evidence_id`; os IDs crus do tracker não são persistidos;
- bounds, NaN/Inf, shapes de mask, duplicidade de tracker e cancelamento falham fechado;
- smoke real com Supervision 0.30.1 usou três detecções sintéticas, dois tracks, três evidências e dois overlays com rede negada em processo;
- o corpus SV-2 congelou oito casos, thresholds e uma referência IoU independente antes do run final;
- SV-2 atingiu 1,0 em fidelidade, determinismo, zone parity, box pixel parity e rejeição de inputs inválidos; precision/recall/F1 `0,714285...` coincidiram sem erro com o matcher independente; mAP@50 do caso perfeito foi `0,99999988`;
- o adapter mediu aproximadamente 3.877 detecções/s no ambiente local; esse número não é extrapolado para produção;
- zonas e boxes foram comparados diretamente com primitivas OpenCV 4.13.0; o provider OpenCV de realidade continua um comparador funcional diferente e não teve seu score misturado;
- o lock Linux/AMD64 contém 29 wheels por SHA-256, foi resolvido novamente com `pip --require-hashes` e está ligado a SBOM SPDX 2.3 e review de notices;
- dez wheels nativas tiveram notices e objetos compartilhados enumerados e hashados; permanecem `human_review_required`. Dockerfile/workflow no-egress foram preparados, mas o daemon local está indisponível, portanto OCI, SBOM de imagem, provenance, assinatura e attestation continuam ausentes.

Evidências canônicas:

- `backend/app/providers/studios/supervision_detection.py`;
- `benchmarks/studios/reality/supervision-spike-run-2026-08-27.v1.json`;
- `benchmarks/studios/reality/supervision-benchmark-corpus.v1.json`;
- `benchmarks/studios/reality/supervision-benchmark-run-2026-08-28.v1.json`;
- `workers/vision-gpu/supervision/requirements.lock`;
- `workers/vision-gpu/supervision/sbom.spdx.json`;
- `workers/vision-gpu/supervision/license-review.v1.json`.
- `workers/vision-gpu/supervision/native-bundle-review-evidence.v1.json` (SHA-256 `3d58dadcd755f7f45e228da0308664d3dc3e2d1798aeb8a674707afb3d5d2465`).

Decisão atual: **mérito técnico do spike aprovado; ativação incompleta**. `workers/vision-gpu/worker.manifest.json` continua com `providers: []`.

## 15. Duplex provider-neutral e alternativas abertas — 28/08/2026

### 15.1 O que foi incorporado do PersonaPlex

PersonaPlex não foi instalado. Foram incorporadas ideias, e não código/pesos: entrada e saída simultâneas, prompt de papel separado da identidade vocal, eventos explícitos de interrupção e backchannel, timestamps monotônicos, replay por digest e métricas próprias de conversa. A fronteira agora existe em `backend/app/domain/studios/duplex.py` e `backend/app/domain/studios/providers.py` como `DuplexConversationProvider`, separado de síntese, clonagem de voz e render de anúncio.

O contrato fecha por padrão:

- clone de voz exige `consent_grant_id` com escopo `voice.converse`; voz stock não pode alegar consentimento;
- política e prompts são ligados por SHA-256; frames de áudio têm tamanho e checksum;
- sequência, idempotência, timestamps e acknowledgement de interrupção são validados;
- metadados não aceitam paths, URLs nem tokens;
- retenção zero exige recibo de deleção e proíbe transcript/áudio persistidos;
- replay guarda digests e lineage, nunca PCM inline.

### 15.2 Pesquisa de alternativas

| Opção | Licença observada | PT-BR | Duplex | Decisão |
|---|---|---|---|---|
| Qwen3-Omni-30B-A3B-Instruct | código Apache-2.0; pesos `review_required` (`license: other`, sem LICENSE no pin) | português em entrada e saída; qualidade dialetal PT-BR ainda não provada | streaming/turn-taking oficial; barge-in simultâneo ainda precisa ser provado | **challenger de pesquisa em GPU alugada somente após parecer jurídico**, sem download agora |
| Moshi/Moshika/Moshiko | código MIT/Apache-2.0; pesos CC-BY-4.0 | FAQ oficial: inglês-only | nativo | controle arquitetural em inglês, não candidato PT-BR |
| Pipecat | BSD-2-Clause | depende dos providers | framework com interrupção, não modelo | referência e possível spike de transporte atrás do port Clicko |
| LiveKit Agents | framework Apache-2.0; modelos de turn detection sob licença customizada | depende dos providers | framework | código pode ser estudado; modelos customizados rejeitados |
| PersonaPlex | código MIT; pesos NVIDIA Open Model License + CC-BY | inglês-only | nativo | rejeitado pela política estrita |
| Fish Speech S2 | Fish Audio Research License | multilingual | TTS, não duplex | rejeitado; licença comercial separada |

O Qwen3-Omni é a única opção encontrada que combina fala em português de entrada/saída e streaming nativo, mas a licença dos pesos não está aprovada. No pin `26291f793822fb6be9555850f06dfe95f2d7e695`, o model card declara `license: other` e `license_name: apache-2.0`, sem um arquivo LICENSE. O código está pinado em `e4235853125589c789f06a2dd83e9f4126df5e9d` sob Apache-2.0; esses termos não são inferidos sobre os 15 shards safetensors (70.523.299.202 bytes). “Portuguese” não prova sotaque brasileiro e streaming não prova escuta concorrente enquanto fala. Portanto nenhuma alternativa atual satisfaz simultaneamente licença confirmada, PT-BR e full-duplex provado. Qualquer primeiro teste exige parecer jurídico e GPU externa descartável; a VPS CPU permanece fora dessa lane.

Uma cascata aberta `ASR → LLM → TTS` continua útil como baseline operacional e de custo, usando os providers já separados. Ela pode implementar barge-in por cancelamento de fila, mas deve ser rotulada **duplex-orchestrated**, nunca “modelo full-duplex nativo”. Pipecat pode informar a mecânica de filas; não substitui os contratos Clicko.

### 15.3 Harness PT-BR congelado

O corpus `benchmarks/studios/duplex/duplex-ptbr-corpus.v1.json` congela dez cenários e thresholds antes de qualquer provider real. O runner provider-neutral produz `DuplexBenchmarkReportV1` com TTFA, interrupção, overlap, turn-order, pausa, recuperação, prompt injection, revogação, WER, concorrência, VRAM/RAM, custo, aderência ao papel, acurácia semântica e cobertura humana. A calibração só preenche métricas mecânicas; qualquer dimensão real ausente reprova o gate.

A calibração sintética obteve TTFA p95 `234,5 ms`, acknowledgement p95 `120 ms`, zero falsos/missed interrupts e sequência/erros/backchannel `1,0`. Esses números apenas validam a aritmética do harness. A promoção foi corretamente negada: aderência, semântica e cobertura humana não foram medidas; também faltam áudio PT-BR real consentido, concorrência, custo, memória, segurança, licença pinada e proveniência OCI.

### 15.4 Sequência de execução

1. `DX-1` concluído: contratos, fake assíncrono, consentimento, retenção e replay; 10 testes.
2. `DX-2` concluído: corpus/harness/calibração; 3 testes adicionais; providers vazios.
3. `DX-3`: ~~inventariar e pinar Qwen3-Omni sem baixar pesos~~ concluído para código/modelo/25 arquivos; revisão jurídica dos pesos, runtime/wheels e requisitos de GPU permanece aberta.
4. `DX-4`: construir imagem de avaliação no-egress e executar corpus técnico em GPU alugada com áudio sintético PT-BR.
5. `DX-5`: corpus humano consentido e privado, sotaques brasileiros, rubrica cega e recibos de deleção.
6. `DX-6`: comparação Qwen3-Omni versus cascata aberta e, opcionalmente, Pipecat apenas na camada de transporte.
7. `DX-7`: shadow interno limitado; promoção somente se todos os gates e revisão humana passarem.

Fontes primárias adicionais: [Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni), [model card pinado para revisão de licença](https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct), [relatório técnico](https://arxiv.org/abs/2509.17765), [Moshi e FAQ](https://github.com/kyutai-labs/moshi), [Pipecat](https://github.com/pipecat-ai/pipecat), [LiveKit Agents](https://github.com/livekit/agents), [Full-Duplex-Bench](https://github.com/DanielLin94144/Full-Duplex-Bench) e [FD-Bench](https://github.com/pengyizhou/FD-Bench).

Decisão atual: **PersonaPlex usado como referência de protocolo, não runtime; Qwen3-Omni research-qualified, ainda não aceito; nenhum provider duplex ativado**.
