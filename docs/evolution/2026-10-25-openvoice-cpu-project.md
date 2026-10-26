# Clonagem em CPU conectada ao projeto

O backend ganhou um adaptador próprio para Kokoro + OpenVoice em CPU. O pedido
de narração do projeto pode usar a voz selecionada por esse caminho, mantendo a
referência e a autorização correspondentes. O agendador encaminha esse provider
para a fila de voz CPU; os providers GPU conservam seus perfis.

Esta entrega conecta o software. Os modelos permanecem candidatos, com avaliação
de qualidade e homologação pendentes. A configuração local não cria aprovações.

## Integração e conservação da escolha

A configuração privada resolve o adaptador sem carregar os modelos no processo
da API. Os assets são conferidos na execução. A imagem deve corresponder aos
manifestos da base Kokoro, do conversor OpenVoice e do worker.

O pedido e o recibo vinculam a versão da voz, a autorização, o checksum da
referência e o roteiro. O adaptador verifica o WAV produzido e recusa recibos
incompatíveis antes de persistir o áudio. Não escolhe outra voz para contornar
uma indisponibilidade.

A execução fica em um container sem rede, com root filesystem somente leitura,
usuário não root, 4 CPUs e 3 GiB. O adaptador confere esses valores no daemon.
O cancelamento remove o container e exige a confirmação da limpeza.

## O que foi verificado com os modelos reais

Foi executado o mesmo adaptador usado pela aplicação, usando somente uma
referência stock sintética `pm_alex` de 7,1 segundos. Outra frase, sintetizada
primeiro pela base `pf_dora`, passou pelo conversor OpenVoice e pelo WavMark.

- Saída: 7,489 segundos de WAV mono PCM16 em 24 kHz.
- Watermark: codificado e verificado no áudio persistido.
- Tempo dentro do pipeline: 120,007 segundos, em um único caso.
- Pico de RSS do processo: 1.812.307.968 bytes.
- Container: removido, com ausência conferida no daemon.
- Cancelamento: um segundo container foi observado em execução, cancelado e
  removido, sem persistir áudio de saída.

Nenhuma pessoa real participou desses dois testes. Os WAVs e recibos completos
ficam privados. O resumo versionado identifica a imagem, os modelos, o worker e
os checksums, sem publicar amostras ou credenciais.

## O que foi verificado no fluxo do projeto

Os testes de API usam banco temporário, fixtures explícitas de admissão e daemon
simulado. Verificam seleção da voz, autorização, fila CPU, idempotência, execução
do job, armazenamento e reabertura do áudio privado. Esses testes demonstram o
contrato da integração; não medem a qualidade do modelo.

Também foram exercitados recibos adulterados, referência alterada, timeout,
cancelamento e limpeza não verificável. Esses casos não publicam áudio.

A regressão integrada passou em 104 testes de provider, runtime, workers,
síntese, narração, voz sobre materiais, avatar, assets CPU e documentos de
evolução. A conferência estática Ruff também passou.

## O que falta para a entrega completa

A avaliação com vozes humanas autorizadas, a inteligibilidade, a semelhança e o
benchmark completo ainda não foram concluídos. Um caso em CPU não estabelece
p95 ou latência de produto. Os manifestos de avaliação mantêm `providers: []`.

Rosto, personagens e avatar continuam em integração e precisam de suas próprias
verificações de modelo e de resultado. O teste de voz não comprova esses recursos.

## Evidências

- `backend/app/providers/studios/openvoice_cpu.py`
- `backend/app/services/studios/speech_runtime.py`
- `backend/app/domain/studios/execution.py`
- `backend/tests/test_openvoice_cpu_provider.py`
- `backend/scripts/check_openvoice_cpu_runtime.py`
- `workers/speech-cpu/openvoice.worker.manifest.json`
- `benchmarks/studios/identity/openvoice-cpu-adapter-local-run-2026-10-25.v1.json`
