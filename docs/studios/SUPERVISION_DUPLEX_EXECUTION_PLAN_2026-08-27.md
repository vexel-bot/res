# Plano de execução — Supervision e voz full-duplex aberta

**Data de corte:** 27/08/2026  
**Status:** em execução na meta ativa  
**Base:** relatório final dos Studios, ADR-019, ADR-020 e pesquisa Supervision/PersonaPlex  
**Princípio:** avaliar, provar e só então promover. Instalar uma biblioteca não equivale a entregar uma capability.

## 1. Resultado pretendido

Entregar duas fronteiras independentes:

1. uma lane de visão que use seletivamente Supervision `0.30.1` como detalhe efêmero para normalização, overlays, zonas e métricas, preservando `RealityContributionV1` como contrato canônico;
2. uma lane de conversa de voz full-duplex provider-neutral, inspirada nas boas ideias do PersonaPlex, mas sem código de servidor, pesos ou licença NVIDIA no runtime e sem confundi-la com TTS/clonagem de voz para anúncio.

Ao final, cada lane terá uma decisão reproduzível de `promote`, `keep_evaluating` ou `reject`. Até uma decisão `promote`, os manifests continuam com `providers: []` e a VPS continua somente como control plane, sem alteração.

## 2. Estado inicial congelado

- Supervision: fonte MIT pinada em `0.30.1` / `5f25aa0ee6dc22891415b6e3d2e1689ce7a32952`; inventory `incomplete`; nenhum pacote no runtime.
- PersonaPlex: código pinado em `3428dfd95309a7f3c84fd93259ded0f810d1ff91`; checkpoint `fdaf4090a61cb315c138a1faee287ffd6c716309` rejeitado pela política open-source-only; nenhum peso baixado.
- `workers/vision-gpu/worker.manifest.json`: `providers: []`.
- `workers/speech-gpu/worker.manifest.json`: `providers: []`.
- Baseline visual: providers clássicos OpenCV em avaliação atrás dos contratos `RealityContributionV1`/`RealityModelV1`.
- Baseline do produto: 368 testes backend aprovados, três integrações opt-in ignoradas e 18 jornadas E2E aprovadas na auditoria final anterior.

Qualquer regressão nessa baseline bloqueia a fase corrente antes de se avaliar qualidade do candidato.

## 3. Arquitetura alvo

### 3.1 Supervision

```text
asset privado + checksum + time map
  → resultado de detector/segmentador/tracker separadamente aprovado
  → SupervisionAdapter (Detections somente em memória)
  → validação Clicko de bounds, frames, IDs, NaN/Inf e lineage
  → RealityContributionV1
  → overlay derivado tenant-scoped por evidence_id
  → RealityModelV1 / Reality Lane / revisão humana
```

Regras invioláveis:

- nenhum objeto, array ou schema do Supervision é persistido ou exposto pela API;
- nenhum conector herda aprovação/licença do toolkit;
- nenhuma URL é buscada no job e nenhum modelo é baixado em runtime;
- `sv.ByteTrack` é proibido; IDs de tracking chegam de um tracker aprovado separadamente;
- o adapter deve ser removível sem migration ou reconform de documentos;
- Supervision fornece observações, nunca uma conclusão de gravidade, contato, causalidade ou física.

### 3.2 Conversa full-duplex

```text
sessão tenant-scoped + policy digest + role prompt ref + voice profile ref aprovado
  → DuplexConversationProvider
  ↔ input_audio / agent_audio / agent_text
  ↔ interrupt / backchannel / error / session_closed
  → replay manifest + métricas + retention/deletion receipt
```

Essa capability não pode usar `SpeechSynthesisProvider` nem `VoiceCloneProvider`. O caso de uso é conversa ao vivo; a narração de anúncio continua em sua lane própria.

## 4. Workstreams e gates

### Fase 0 — freeze e contratos de teste

Entregas:

- manifesto de baseline com pins, digests, comandos de teste e invariantes;
- teste arquitetural que impede import de Supervision no domínio e nos routers;
- teste que impede `supervision`/`personaplex` nos manifests antes da promoção;
- teste que proíbe `sv.ByteTrack`, downloads de modelos e paths/URLs vindos do payload;
- matriz de ownership: domínio Clicko, adapter, modelo conectado e worker.

Gate: baseline reproduzível e testes de proibição falhando fechado.

### Fase SV-1 — spike funcional offline

Entregas:

- `SupervisionDetectionAdapter` isolado em `backend/app/providers/studios/`;
- DTO interno mínimo para boxes, masks, class IDs, confidence, tracker IDs externos e frame binding;
- conversão para `RealityContributionV1` com lineage completo;
- overlay de evidência ligado a `evidence_id`, sem PII no nome do arquivo;
- fixtures sintéticas de empty set, boxes, masks, classes, tracks e zonas;
- cleanup idempotente em sucesso, erro e cancelamento.

Gate:

- 100% de preservação semântica nas fixtures válidas;
- entradas fora de bounds, NaN/Inf, masks incompatíveis e timebase inválido rejeitadas;
- saída determinística sob a mesma configuração;
- nenhum egress, persistência upstream ou uso de ByteTrack.

### Fase SV-2 — benchmark comparativo

Corpus mínimo:

- cenas sintéticas 16:9, 9:16 e 1:1;
- zero, uma e múltiplas detecções;
- cruzamento de line zone e polygon zone, incluindo anchors no limite;
- oclusão, saída/retorno ao frame e IDs externos;
- vídeo corrompido, frame ausente e cancelamento;
- conjunto público somente se licença, hash e redistribuição forem registrados.

Métricas congeladas antes do run:

| Dimensão | Critério mínimo |
| --- | --- |
| fidelidade do adapter | 100% de boxes, masks, classes, confiança e frame bindings válidos |
| determinismo | JSON canônico idêntico e overlay pixel-identical nas fixtures congeladas |
| métricas | precision, recall, F1 e mAP conferidos por implementação independente em casos pequenos |
| zonas | 100% dos eventos esperados, inclusive bordas/anchors |
| robustez | 100% das entradas inválidas falham sem asset órfão |
| isolamento | zero path cross-tenant e zero acesso de rede |
| desempenho | registrar fps, startup, RAM p50/p95 e custo; threshold de promoção definido antes do run final |

Comparador: baseline OpenCV existente, usando o mesmo corpus, timebase e máquina. O objetivo não é “vencer OpenCV” em tudo; é provar que o plumbing removido compensa custo, tamanho e complexidade.

### Fase SV-3 — supply chain e runtime

Entregas:

- lock Linux/AMD64 minimizado e com hashes;
- inventário de cada wheel/binário, notices e decisão comercial;
- SBOM válida, provenance e assinatura da imagem candidata;
- OCI pinada por digest, usuário não-root, rootfs read-only, capabilities removidas e no-egress;
- attestation de toolchain/hardware, healthcheck e limites de recursos;
- teste de cancelamento, retry, cleanup e storage tenant-scoped.

Gate: inventory muda de `incomplete` somente quando todos os digests fecharem. A imagem continua `evaluation/providers=none` até a fase de promoção.

### Fase SV-4 — shadow e promoção

**Checkpoint 28/08/2026:** candidate manifest governado e shadow sintético executados. O OpenCV primitive reference permaneceu autoritativo, com divergência, falha, abstention e órfãos iguais a zero; rollback sem migration passou. Este checkpoint cobre apenas plumbing sintético. Shadow com mídia humana consentida, dashboard operacional, revisão humana e todos os gates de OCI/licença/attestation continuam pendentes, e o worker permanece com `providers: []`.

O promotion gate foi endurecido para exigir binding do digest de shadow. A verificação OCI exige statements in-toto estruturados e ligados ao manifest da imagem; o workflow manual também testa non-root, rootfs read-only, no-egress, capabilities zeradas e limites de processo/recursos antes de reter o artefato efêmero.

Entregas:

- registro governado do candidato sem anúncio automático;
- shadow mode ao lado da baseline OpenCV;
- comparação de outputs e divergências por corpus/job;
- dashboards de latência, RAM, falha, abstention e assets órfãos;
- rollback documentado e testado.

Gate de promoção:

- benchmark, licença, SBOM, provenance, assinatura e attestation aprovados;
- divergências revisadas e thresholds atingidos;
- revisão humana não revela piora operacional;
- alteração do manifest ocorre na mesma revisão da decisão de promoção;
- rollback para OpenCV comprovado sem migration.

### Fase DX-1 — contrato full-duplex provider-neutral

Entregas:

- `DuplexConversationProvider` como port assíncrono separado;
- `DuplexSessionPolicyV1`, `DuplexSessionRequestV1`, `DuplexEventV1`, `DuplexReplayManifestV1` e `DuplexBenchmarkResultV1`;
- sequence number, monotonic timestamp, idempotency key e policy digest em todos os eventos;
- estados `created`, `listening`, `speaking`, `interrupted`, `closing`, `closed`, `failed`;
- eventos tipados de áudio, texto, interrupção, overlap, backchannel e fechamento;
- referências opacas para role prompt e voice profile; nunca path local ou token de hub;
- retention policy e deletion receipt por sessão.

Gate: dois providers fake com comportamentos diferentes passam o mesmo contrato, replay determinístico e isolamento cross-tenant. Nenhum código PersonaPlex entra no runtime.

### Fase DX-2 — pesquisa de alternativas abertas

Para cada candidato:

- separar licença de código, pesos, datasets, codecs e voice assets;
- exigir licença realmente compatível com a política Clicko, uso comercial e redistribuição pretendida;
- verificar PT-BR real, streaming/full-duplex real, formatos, GPU/VRAM e manutenção;
- inspecionar servidor, estado por sessão, concorrência, paths, serialização, downloads, logs e containers;
- fixar commit/revision e produzir artifact inventory antes de baixar pesos grandes;
- rejeitar candidatos que só sejam cascata ASR→LLM→TTS se estiverem sendo vendidos como modelo nativamente full-duplex; eles podem competir como baseline separado.

Gate: shortlist com pelo menos um candidato legalmente aceitável ou decisão explícita de que nenhum atende. Ausência de candidato não autoriza PersonaPlex automaticamente.

### Fase DX-3 — harness PT-BR

Corpora separados:

- sintético e sem biometria para protocolo, estados, interrupção e falhas;
- fala stock licenciada para benchmark técnico inicial;
- corpus humano somente após consentimento, minimização e retention aprovados.

Métricas:

- time-to-first-audio p50/p95;
- interruption latency p50/p95 e false interruption rate;
- overlap, turn-order ratio, pause handling e backchannel frequency;
- WER/semantic accuracy e role adherence;
- naturalidade cega PT-BR e sotaques regionais quando houver consentimento;
- VRAM/RAM por sessão, sessões simultâneas, recovery e custo/minuto;
- prompt injection falado, vazamento em logs, traversal, payload malicioso e revogação durante sessão.

Gate: thresholds congelados antes do run, avaliação cega e lineage completo. O resultado pode ser `reject`; não há obrigação de promover um modelo.

## 5. Sequência de implementação

1. Concluir Fase 0 e preservar a baseline.
2. Executar SV-1 apenas com fixtures sintéticas.
3. Congelar corpus e thresholds, então executar SV-2.
4. Só construir SV-3 se SV-2 provar valor material.
5. Colocar SV-4 em shadow antes de qualquer anúncio.
6. Em paralelo lógico, mas sem compartilhar runtime, entregar DX-1 com fakes.
7. Executar pesquisa DX-2 sem aceitar licenças ou baixar pesos condicionados.
8. Executar DX-3 somente para candidatos aprovados; voz humana exige gate adicional.
9. Consolidar ADR, benchmark, custos e decisão final.

## 6. Critérios de parada

O trabalho para imediatamente se:

- um modelo/conector tentar herdar a licença do Supervision;
- tipos Supervision aparecerem em schema, banco ou API;
- o lock exigir egress ou dependência não inventariada;
- algum teste usar `sv.ByteTrack`;
- pesos PersonaPlex forem baixados ou a licença for aceita sem mudança explícita de política;
- full-duplex for misturado a TTS/clone de anúncio;
- biometria aparecer em logs, query strings, nomes de arquivo ou corpus sem consentimento;
- qualquer etapa exigir alteração da VPS sem nova autorização explícita.

## 7. Evidências de conclusão

A meta só poderá ser encerrada com:

- relatório de baseline e comandos reproduzíveis;
- adapters e contratos cobertos por testes;
- corpus, thresholds e resultados versionados;
- inventories com decisão honesta por componente;
- prova de que os manifests ficaram vazios ou foram alterados somente após promoção aprovada;
- full suite backend/frontend/E2E e migrations sem regressão;
- registro de qualquer limitação, rejeição ou gate externo ainda pendente;
- confirmação de que a VPS não foi tocada.

## 8. Resultado de produto esperado

Supervision pode reduzir tempo de implementação de visão e melhorar evidência visual sem virar dependência do domínio. A contribuição útil do PersonaPlex é transformar “voz ao vivo” em uma capability explícita, mensurável e governada. O checkpoint NVIDIA não é necessário para capturar esse valor arquitetural e permanece rejeitado enquanto a política open-source-only estiver vigente.
