# Clicko speech CPU preflight

Este manifest reserva a fila `studio.speech.cpu` para a capability `stock_voice`.
Ele é uma fronteira de runtime, não um provider: `providers` permanece vazio e o
worker não anuncia Kokoro enquanto a política stock, a cadeia eSpeak/Misaki, a
imagem, o SBOM e o benchmark sintético não forem aprovados.

Digest canônico atual do manifest: `36f45dd041744f671a68c8980711c44088592da1b06a3ce77c725bce074b4837`.

O path de policy aponta para `voice-stock-pt-br-policy.v1.json`, que exige corpus
sintético, zero sujeitos, revisão humana cega, cleanup e custo/RTF em CPU. O path
de lock é deliberadamente um contrato de imagem futura; nenhum lock de provider
foi colocado no repositório antes da escolha de wheels e notices.

Antes de promover a imagem:

1. fechar a revisão jurídica da distribuição e notices do eSpeak NG;
2. fixar Python/wheels e a imagem Linux/AMD64 por digest;
3. gerar SBOM/provenance e provar no-egress, quotas, cancelamento e cleanup;
4. repetir/otimizar os 64 casos sintéticos até o p95 RTF passar sem relaxar a policy;
5. somente então trocar o manifest para um runtime aprovado e anunciar um provider.

A VPS Nexus não é destino deste worker.

Estado local de 26/08/2026: a candidata Linux/AMD64 foi construída com lock
CPU-only, pesos pinados e replacement eSpeak verificado. O run `pf_dora` produziu
64/64 casos, mas reprovou latência (`p95 RTF 2,338 > 1,0`), então continua
`evaluation/providers=none`. O limite de threads está gravado na imagem para impedir
oversubscription acidental; isso não transforma um resultado falho em aprovado.

O `Dockerfile.preflight` e o workflow manual `.github/workflows/studios-speech-cpu-preflight.yml`
constroem somente uma imagem Linux/AMD64 de fronteira, com base Python pinada,
proveniência/SBOM e `providers: []`. O verificador recalcula o digest do manifest,
da policy stock e do contrato de dependências antes do BuildKit; depois do build,
`backend/scripts/verify_preflight_oci.py` inspeciona o OCI, a plataforma amd64, os
attestations de SBOM/provenance e o label de providers vazio. O artefato OCI fica
retido por sete dias para inspeção; não há push, registro de provider, download de
peso ou deploy automático.
