# ADR-015 — Supply chain fail-closed e imagem preflight do PGV-1

**Status:** aceito; preparação implementada, promoção/provider real bloqueados  
**Data:** 2026-08-25

## Contexto

O ADR-014 isolou a orquestração e atestou a classe de GPU, mas nomes de repositório ou tags de container não identificam os bytes que serão executados. Licença de código também não deve ser inferida para checkpoint, dataset ou bundle CUDA. Sem um inventário verificável, uma atualização upstream poderia trocar pesos, termos ou runtime sem alterar a configuração do produto.

## Decisão

Criar `ArtifactInventoryV1` como gate canônico e fail-closed. Cada artefato registra fonte, revisão, método de verificação, digest/tamanho quando aplicável, evidência jurídica por digest e decisão comercial SaaS explícita. Código resolvido exige commit Git; modelo exige SHA-256 e tamanho; container exige digest OCI. Downloads de avaliação usam apenas referência opaca no produto — paths locais não entram no manifest.

O contrato `ProviderPromotionEvidenceV1` e `evaluate_provider_promotion_gate` agora separam preflight de promoção: uma imagem OCI, SBOM, provenance, plataforma Linux/AMD64, benchmark, licença, attestation, no-egress, cleanup, storage tenant-scoped e anúncio no worker precisam estar ligados aos digests exatos do candidato e do manifest. Qualquer binding trocado é `blocked`; evidência externa ausente é `incomplete`.

O inventário PGV-1 congela OpenCV, TAPNet, TAPIR panning, RAFT, RAFT Things, Depth Anything V2 Small e o runtime PyTorch/CUDA. TAPIR e Depth Anything V2 Small estão tecnicamente e juridicamente aprovados para este gate. Os pesos RAFT e o bundle PyTorch/CUDA continuam `review_required`; portanto o inventário inteiro não pode declarar `approved`.

Preparar `Dockerfile.preflight` com base OCI pinada, lock Python Linux AMD64 com hashes, policy/inventory/manifest copiados por digest e validação durante o build. A imagem usa um app Celery exclusivo de visão e registra somente o probe de attestation. O manifest mantém `providers: []`; nenhum código/peso de inferência é copiado.

OpenCut permanece fora do runtime de visão. Ele é candidato de ergonomia para a Reality Lane/timeline, que consumirá markers e evidências do documento Clicko.

## Evidência

- inventário canônico: `d1935d35ed3af59d792a5b0c9607d477ea661a862170f4e8574c7a94015dea0c`;
- manifest vision GPU: `fbe3c7a55ba2d98a7a12a4ae37e8b97b46d2282bcb89cfe5a657d6b60ac0efb1`;
- lock Python: `1a40b7d969f33e72e8886ff898789f0191a5c63a63d958555ea23b736ee97fe0`;
- policy física: `8f4ff3bb19caf1c50dd6a6cd627ad6cd8b58f20bd6340f2efdd9abf01712aad0`;
- testes cobrem derivação de status, licença comercial explícita, tipos de integridade, referências opacas, tamper e isolamento do app Celery;
- testes cobrem também a impossibilidade de promover o candidato OpenCV atual a partir do inventário `review_required`/manifest `providers: []`, além de adulteração do digest da evidência;
- a regressão completa terminou com 151 passes, 1 skip esperado e Ruff limpo;
- a verificação local do build context passou com providers vazios; a imagem não foi construída porque não havia Docker daemon ativo;
- nenhuma VPS, GPU, mídia privada ou serviço existente foi acessado.

## Consequências

O preflight pode ser inspecionado e reproduzido sem fingir que um provider existe. Alterar qualquer artefato exige novo inventário/digest e nova evidência. O estado `review_required` é intencional: permite pesquisa e preparação, mas bloqueia promoção e ativação.

## Próximo gate

1. obter decisão jurídica explícita sobre RAFT weights e o bundle PyTorch/CUDA ou substituir cada item por alternativa permissiva;
2. construir em runner Linux com Docker/BuildKit, gerar SBOM e provenance, assinar e registrar digest da imagem;
3. fixar por SHA-256 as dependências dos providers de visão e incluir somente artefatos aprovados;
4. provar attestation, cancelamento, cleanup e object storage privado em worker GPU externo;
5. adicionar persistência/cache tenant-scoped antes da primeira baseline real.
