# Auditoria de bloqueio — Supervision e duplex aberto

**Data:** 28/08/2026  
**Decisão:** execução local material concluída; promoção bloqueada somente pelos gates humanos/externos remanescentes  
**Invariantes:** providers desabilitados, pesos PersonaPlex/Qwen3-Omni ausentes, assets locais Qwen3-4B/Chatterbox apenas em avaliação, VPS intocada

## Requisitos comprovados

| Requisito | Evidência | Estado |
| --- | --- | --- |
| Supervision 0.30.1 isolado | adapter converte `sv.Detections` efêmero para `RealityContributionV1`; domínio não importa tipos upstream | comprovado |
| overlays explicáveis | PNGs ligados a `evidence_id`, checksum e lineage | comprovado |
| corpus/benchmark OpenCV | SV-2 sintético, fidelidade/determinismo 1,0, zones/overlay parity 1,0 | comprovado |
| supply chain preparada | lock de 29 wheels, hashes, SPDX 2.3, notices nativos e recipe no-egress | comprovado |
| OCI e runtime hardened | Linux/AMD64 `92dbfe13...d6a6`, provenance/SBOM in-toto, uid 10001, rede `none`, rootfs read-only, capabilities removidas e probe `ready` | comprovado |
| shadow reversível | SV-4 sintético com divergência/falha/abstention/órfãos zero; OpenCV autoritativo; rollback sem migration | comprovado |
| promoção apenas por gates | candidate manifest `evaluation`, benchmark/shadow ligados por digest, manifest do worker vazio | comprovado |
| port duplex provider-neutral | sessão assíncrona, eventos, áudio por checksum, consentimento, retenção e replay determinístico | comprovado |
| estados e dois fakes | state machine completa; dois providers fake distintos passam o mesmo contrato | comprovado |
| harness PT-BR | dez cenários e thresholds para latência, interrupção, overlap, turn-order, pausa, recovery, segurança, WER, hardware, custo e julgamento | comprovado |
| PersonaPlex rejeitado | código apenas como referência; checkpoint custom NVIDIA rejeitado e não baixado | comprovado |
| alternativas abertas | seis candidatos classificados; Qwen pinado e 25 arquivos inventariados sem pesos | comprovado |
| self-hosted local | Qwen3-4B Q4, 4.022.468.096 parâmetros, API loopback autenticada; Chatterbox pt-BR verificado e recusado por 4.095 < 16.384 MiB | comprovado sem promoção |
| fail-closed integrado | `vision_gpu.providers=[]`, `speech_gpu.providers=[]` e `llm_gpu.providers=[]`; regressões alvo listadas no baseline | comprovado |

## Evidência ainda ausente

| Gate obrigatório | Por que não pode ser concluído localmente agora | Condição de retomada |
| --- | --- | --- |
| assinatura do OCI | OCI, digest, provenance/SBOM e runtime existem; signer/identidade autorizada não foi fornecida | definir política e identidade de assinatura de promoção |
| parecer das dez wheels nativas | revisão jurídica/humana não pode ser autoaprovada pelo código | reviewer autorizado registrar decisão |
| licença dos pesos Qwen3-Omni | model card pinado diz `license: other`, só nomeia Apache-2.0 e não contém LICENSE | parecer jurídico ou termos inequívocos do fornecedor; não afeta o GGUF Qwen3-4B Apache-2.0 local |
| shadow humano/operacional | não há mídia consentida, consent grant, reviewers ou janela operacional | fornecer corpus consentido e reviewers independentes |
| PT-BR real e julgamento cego | calibração atual é sintética, sem biometria | corpus de fala aprovado e protocolo cego |
| voz/duplex concorrente, VRAM/RAM e custo | Qwen3-Omni tem 70,5 GB não baixados; Chatterbox falhou o piso local de VRAM | GPU externa, budget e autorização de benchmark consentido |
| promoção | depende de todos os gates acima e alteração do manifest na mesma revisão | revisão final aprovada; nunca promoção automática |

## Artefatos de retomada

- `workers/vision-gpu/supervision/Dockerfile.evaluation`
- `benchmarks/studios/reality/supervision-oci-build-run-2026-08-28.v1.json`
- `.github/workflows/studios-supervision-evaluation.yml`
- `benchmarks/studios/reality/supervision-shadow-run-2026-08-28.v1.json`
- `workers/vision-gpu/providers/supervision-toolkit.provider.json`
- `benchmarks/studios/duplex/duplex-ptbr-corpus.v1.json`
- `workers/speech-gpu/qwen3-omni-30b-a3b.vendor-manifest.v1.json`
- `workers/local-evaluation/self-hosted-model-assets.v1.json`
- `benchmarks/studios/self-hosted/local-self-hosted-readiness-2026-08-28.v1.json`
- `backend/scripts/start_local_qwen_server.ps1`
- `backend/scripts/verify_local_qwen_api.py`
- `backend/scripts/verify_duplex_research.py`

Nenhum item ausente pode ser substituído por fixture, declaração documental ou dado fabricado. O trabalho técnico local seguro está materializado; promoção depende de assinatura autorizada, revisão humana/legal, corpus consentido e GPU externa elegível.
