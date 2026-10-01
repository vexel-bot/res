# ADR-014 — Orquestração provider-neutral e preflight do worker vision_gpu

**Status:** aceito; preflight implementado, providers/modelos reais não ativados  
**Data:** 2026-08-25

## Contexto

PGV-0 definiu contratos, policies e digests, mas isso ainda não provava que providers de geometria, tracking, scene understanding, world model e Physical QC poderiam ser compostos e substituídos sem adulterar bindings. Também existia apenas um manifest de worker `media_cpu`; chamar uma queue de `vision_gpu` não provava presença, VRAM ou compute capability da GPU.

Executar TAPIR, RAFT, Depth Anything V2 ou V-JEPA antes de fechar essas fronteiras criaria acoplamento ao primeiro payload/modelo e poderia permitir que um adapter avaliasse um input e devolvesse resultado ligado a outro.

## Decisão

Introduzir dois orquestradores provider-neutral:

- `RealityAnalysisOrchestrator`: valida o arquivo pelo checksum, executa geometria e tracking, opcionalmente cria um modelo preliminar e chama world model, sintetiza o `RealityModelV1` final e comprova que lineage/evidência das contributions não foram removidos ou alterados;
- `PhysicalQualityOrchestrator`: valida `PhysicalPlausibilityRequestV1` contra modelo, constraints e policy, executa o provider advisory e prova que o resultado corresponde ao mesmo documento, revisão, render job, asset/checksum, Reality Model, constraint set e policy.

Todo provider recebe progresso monotônico normalizado e cancelamento. Progressão inválida, regressão, checksum trocado, kind/provider divergente, range fora da fonte, colisão de IDs, lineage alterado, evidência descartada ou binding trocado falham fechados.

O manifest `workers/vision-gpu/worker.manifest.json` reserva apenas `reality_analysis` e `video_physical_qc` em `studio.gpu.vision`. A lista de providers fica vazia até homologação. O runtime exige attestation NVIDIA/CUDA com:

- pelo menos uma GPU elegível;
- no mínimo 22.528 MiB de memória visível;
- compute capability mínima 8.0;
- driver em família explicitamente permitida;
- isolamento non-root/read-only, concorrência 1 e temp efêmero.

O validador interpreta o inventário de `nvidia-smi` e rejeita hardware insuficiente. Em produção, as regras existentes continuam exigindo object storage S3 e digest da imagem.

## Evidência

- adapters fakes existem apenas nos testes e não aparecem como providers disponíveis no manifest;
- testes provam composição com/sem world model, substituição de provider, progresso, cancelamento, checksum, provider/kind, lineage/evidence preservation e bindings exatos do Physical QC;
- manifest GPU é versionado/digest-bound e rejeita uma NVIDIA T4 de 15 GiB/CC 7.5 para a classe planejada;
- 43 testes focados de orquestração, contratos, runtime, execução e benchmarking passaram;
- a regressão completa do backend terminou com 137 passes e 1 skip esperado;
- nenhum peso, CUDA runtime, mídia privada ou GPU foi usado; a VPS não foi acessada.

## Consequências

O primeiro provider real se torna descartável e precisa produzir contributions Clicko válidas. Um world model só adiciona evidência; não substitui percepção ou policy. O runtime não pode alegar GPU por configuração textual. O ADR-015 fechou o contrato/inventário de artefatos e a definição da imagem preflight; ainda faltam persistência/API/job service de Reality, cache por checksum, build/SBOM/assinatura da imagem e execução física externa.

## Próximo gate

Não registrar provider real antes de:

1. resolver as revisões jurídicas ainda abertas no inventário ADR-015;
2. aprovar o artifact/license manifest e o futuro source/build manifest;
3. construir a definição pinada `vision_gpu` em Linux com SBOM, provenance e assinatura;
4. provar attestation, object storage privado, isolamento, cancelamento e cleanup em worker GPU externo;
5. adicionar persistência tenant-scoped e idempotência/cache por asset checksum + policy digest;
6. somente então implementar a primeira baseline PGV-1.
