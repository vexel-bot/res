# ADR-019 — Supervision como toolkit de borda, nunca domínio canônico

**Status:** aceita para spike; provider não aprovado  
**Data:** 27/08/2026

## Contexto

A Reality Lane precisa normalizar resultados de detectores/segmentadores, produzir overlays e calcular métricas sem repetir plumbing por modelo. O Supervision 0.30.1 (`5f25aa0ee6dc22891415b6e3d2e1689ce7a32952`) é MIT e fornece `Detections`, conversores, zonas, annotators, datasets e métricas. Ele não é um modelo de visão ou física. Seu `ByteTrack` embutido está depreciado e será removido em 0.31.0.

## Decisão

Avaliar somente um subset minimizado do Supervision dentro do worker de visão:

- `Detections` é tipo efêmero da anti-corruption layer;
- adapters de modelos produzem e consomem tipos Clicko nas fronteiras;
- persistência usa exclusivamente `RealityContributionV1`, `RealityModelV1`, asset refs, checksums e lineage;
- overlays são assets derivados tenant-scoped ligados por `evidence_id`;
- métricas finais, policies e thresholds continuam Clicko;
- nenhum código novo pode depender de `sv.ByteTrack`;
- cada modelo/conector mantém inventory de código, pesos, runtime e licença próprio;
- o provider permanece ausente do worker até lock, SBOM, OCI, benchmark e promoção explícita.

## Alternativas consideradas

- **Reimplementar tudo:** preserva controle, mas repete conversores/annotators/métricas e aumenta risco de bugs.
- **Persistir `Detections`:** reduz conversão inicial, mas acopla banco/API a arrays e semântica upstream.
- **Usar aplicação/modelos Roboflow completos:** introduz credenciais, egress e licenças fora do problema avaliado.
- **Adotar ByteTrack do pacote:** cria dívida imediata em API já depreciada.

## Consequências

Positivas:

- menos código incidental;
- troca de modelo mais barata;
- overlays e benchmarks consistentes;
- saída simples: remover adapter e manter contratos/dados Clicko.

Custos/riscos:

- conversão adicional por job;
- dependências PyAV/NumPy/SciPy e bins exigem lock/SBOM;
- upstream evolui rápido e precisa de pin/testes;
- “model-agnostic” não significa que modelos conectados estão licenciados ou homologados.

## Gate de promoção

1. spike `SV-1` sem egress e sem dado humano;
2. fidelity/determinism benchmark `SV-2` aprovado;
3. lock Linux minimizado, notices, SBOM e OCI atestada;
4. worker non-root/read-only, cancelamento e cleanup;
5. registry opt-in, shadow mode e rollback para baseline OpenCV;
6. `workers/vision-gpu/worker.manifest.json` alterado apenas na mesma revisão de promoção.

## Rollback

Desregistrar o adapter e usar os providers OpenCV/scene existentes. Nenhuma migration de domínio ou documento é necessária porque objetos Supervision não são persistidos.
