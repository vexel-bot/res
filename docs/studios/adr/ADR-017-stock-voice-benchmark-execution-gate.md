# ADR-017 — Gate de execução do benchmark stock PT-BR

**Data:** 2026-08-25  
**Status:** accepted — preparação concluída, execução pendente  
**Escopo:** `clicko.voice-stock.pt-br.v1` / Kokoro 82M

## Decisão

O primeiro benchmark de voz stock será executado somente em uma imagem Linux/AMD64
isolada, com o worker `speech_cpu`, lock de dependências, SBOM, provenance e notice
de todos os componentes. A suíte será a fixture sintética determinística preparada
fora do Git; nenhum áudio, peso ou dado biométrico será colocado no repositório.

O ambiente Windows local não é um substituto aceitável para esse gate: na verificação
de 25/08/2026 havia Python 3.11.9, mas não havia `uv`, PyTorch, Kokoro, WhisperX,
Chatterbox ou OpenVoice instalados e restavam aproximadamente 0,7 GB de RAM livre.
Instalar pesos/modelos nesse estado criaria um resultado instável e não reproduzível.
Nenhuma instalação foi feita e a VPS não será usada como laboratório de benchmark.

## Evidência de preparação

- policy congelada: `benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json`;
- gerador: `backend/scripts/generate_synthetic_stock_corpus.py`;
- corpus: 64 casos, oito cenários, locale `pt-BR`, `synthetic=true` em todos os casos;
- digest do corpus: `80c182fe0c43404284b3897c06a3b22d434630ecc67548f1562edb86cb2d4a90`;
- scriptbook: privado, determinístico e com digest de script vinculado por caso;
- referência local privada: `C:\Users\edugu\Downloads\clicko-private-benchmarks\voice-stock-pt-br`;
- teste de determinismo e ausência de referências biométricas: passou;
- runner `speech_benchmark.py`: executa os 64 casos pelo port tipado e produz
  observações por caso de RTF, RAM, custo e falha;
- o evaluator recompõe os agregados e mantém o run `incomplete` enquanto MOS,
  inteligibilidade, termos críticos, off-script, truncamento, cleanup e licença
  estiverem ausentes;
- scriptbook alterado é recusado antes da primeira chamada ao provider.

O preflight executável está em `workers/speech-cpu/Dockerfile.preflight`, com
verificador de digests em `workers/speech-cpu/verify_build.py` e workflow manual em
`.github/workflows/studios-speech-cpu-preflight.yml`. Ele produz somente OCI
Linux/AMD64 com SBOM/provenance e mantém `providers: []`. Depois do build, o
`backend/scripts/verify_preflight_oci.py` recalcula blobs, valida os attestations e
confirma que o label não anuncia provider; a imagem não é uma aprovação de Kokoro.

O executor provider-neutral também está materializado em
`backend/app/services/studios/speech.py`. O control plane só admite um job quando
provider e modelo estão aprovados, ambos registram benchmark passado e o provider
declara anúncio pelo worker; o worker ainda precisa carregar o adapter tipado. A
fixture gera WAV real e comprova storage privado, checksum, lineage, provenance e
rollback, mas não registra provider de produção nem produz score de Kokoro.

O adapter candidato está em `backend/app/providers/studios/kokoro_stock.py`. Ele é
CPU-only, exige cache Hugging Face offline ligado à revisão e digest esperados,
aceita somente `pf_dora`, `pm_alex` e `pm_santa`, divide roteiros longos sem alterar
o texto normalizado, grava WAV mono 24 kHz, calcula custo de CPU e remove output
parcial em cancelamento. Ele não é importado em `SPEECH_PROVIDERS`.

O inventário e o manifest de candidato ficam em `workers/speech-cpu/providers/`.
Os commits Kokoro, Misaki e eSpeak e seus textos de licença foram verificados nos
clones externos; pesos e imagem OCI continuam `unresolved`, portanto o inventário é
`incomplete` e o candidato é apenas `evaluation`. O lock upstream não foi aceito
como lock Clicko: no commit fixado, `pyproject.toml` declara Kokoro 0.9.4, enquanto
o `uv.lock` identifica o pacote editável como 0.9.2.

`workers/speech-cpu/candidate/pyproject.toml` e o workflow manual
`studios-speech-kokoro-lock.yml` geram um lock Clicko em Linux/AMD64 com uv 0.12.3,
revisões Git exatas e cutoff temporal. `verify_kokoro_candidate_lock.py` recusa
fontes locais/editáveis, commits divergentes, runtime ausente ou distribuições do
registry sem SHA-256. O artefato gerado ainda exige revisão de SBOM/licenças antes
de entrar numa imagem candidata.

A análise do lock expôs uma divergência adicional e material. Misaki importa
`espeakng-loader`; o wheel Linux `0.2.4` (SHA-256 `08721baf...`) contém
`libespeak-ng.so.1.52.0` ligado ao commit `4870adfa...`, não ao commit da policy
`7d426728...`. O wheel também não contém `LICENSE`, `COPYING` ou `NOTICE` e seu
METADATA não declara licença. Por isso o verificador do lock retorna
`requiresEspeakRuntimeReplacement=true`, mesmo quando a resolução é íntegra.

`studio.espeak-runtime-assets.v1`, `Dockerfile.espeak-runtime` e o workflow manual
`studios-speech-espeak-runtime.yml` definem a substituição: compilar exatamente
`7d426728...`, exportar biblioteca/dados, ambiente/flags de build, GPL `COPYING` e
o tar de corresponding source; então gerar um manifesto de todos os bytes. Esse
workflow foi preparado e testado estaticamente, mas ainda não executado. O runner
Kokoro agora exige manifest/root externos e liga o digest resultante ao componente
`espeak-ng-runtime`; o wheel antigo sozinho nunca satisfaz o gate.

## Ciclo privado e ordem de operação

O pacote operacional foi fechado em 26/08/2026 com quatro comandos executáveis
diretamente por `python backend/scripts/<comando>.py` a partir da raiz do checkout:

1. `run_kokoro_stock_benchmark.py` verifica lock, snapshot de modelo, inventário,
   candidato, worker, imagem e quatro attestations; sintetiza 64 casos e persiste o
   snapshot `initial`, mantendo os WAVs privados para a revisão;
2. `prepare_speech_review.py` usa um segredo de cegamento de pelo menos 32 bytes e
   cria um plano interno mais três pacotes separados, sem nome de provider/candidato;
3. `ingest_speech_review.py` exige três submissões completas e ligadas aos mesmos
   scripts, checksums e assignments; agrega 192 avaliações e persiste `post-review`,
   mas ainda preserva os WAVs;
4. `finalize_speech_benchmark_cleanup.py` só aceita o snapshot revisado completo,
   remove áudio e sidecars por caso, preserva provenance, grava recibo e snapshot
   `post-cleanup`. O comando é retomável: uma repetição valida e reutiliza exatamente
   o mesmo recibo/snapshot; divergência existente falha fechada e nunca é sobrescrita.

Corpus, scriptbook, submissions e diretório de saída são recusados quando ficam sob
o repositório. Os snapshots e recibos são append-only, e a limpeza não pode ser
antecipada para antes da revisão humana persistida. O lifecycle integrado foi testado
com 64 WAVs privados de fixture, três reviewers, 192 ratings, cleanup 64/64 e replay
idempotente; isso continua sendo prova do executor, não evidência real de Kokoro.

O total de regressão abaixo é atualizado em `TEST_BASELINE.md` depois de cada suíte
backend completa. Os skips esperados continuam restritos às duas integrações OpenCV
opcionais no Python padrão e ao smoke HyperFrames opt-in, tratados pelos ambientes
externos próprios.

## Gate de execução

Antes do primeiro áudio, o executor precisa confirmar:

1. o digest da policy, manifest e scriptbook é o esperado e o scriptbook não contém
   referências a sujeitos, assets ou consentimentos;
2. a imagem anuncia apenas `speech_cpu`, com `providers: []` até o gate de promoção;
3. Kokoro, pesos 82M e Misaki estão fixados nos commits da policy, e o eSpeak
   executado é o replacement manifestado de `7d426728...`, não o 1.52.0 do wheel;
4. o SBOM contém a cadeia GPL do eSpeak NG e os notices/source obligations estão
   materializados no artefato distribuível;
5. cada caso gera output privado com checksum, duração, RTF, pico de RAM, custo,
   estado terminal e recibo de cleanup;
6. a evidência é recomputável pelo evaluator e não contém agregados digitados à mão;
7. a revisão MOS é cega, com 3 reviewers distintos e 3 ratings por cada um dos 64
   casos (192 ratings; 180 é apenas o piso agregado da policy), além das métricas
   objetivas de inteligibilidade, termos críticos,
   off-script, repetição/truncamento, RTF, RAM, custo, falha e cleanup;
8. somente após licença, controles, revisão humana e todos os thresholds passarem
   o registro poderá ser aprovado — e ainda será necessário promover o provider no
   manifest do worker em uma mudança separada e revisável.

## Consequência

O produto já pode mostrar `stock_voice` como `blocked/review` no readiness por
workspace, sem alegar que a voz funciona. O próximo trabalho é executar os workflows
externos de lock, assets do modelo e replacement eSpeak, revisar os artefatos,
construir a imagem candidata e então rodar a suíte real; até lá, Kokoro, OpenVoice,
Chatterbox e WhisperX permanecem não
anunciados e sem execução real.
