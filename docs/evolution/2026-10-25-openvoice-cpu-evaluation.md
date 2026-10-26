# Clonagem de voz: conversão de timbre avaliada em CPU

O pipeline Kokoro + OpenVoice foi executado com os modelos reais no computador
local, sem CUDA. Uma referência sintética de 7,1 segundos foi usada para converter
outra fala, de 7,489 segundos. O watermark foi conferido depois de salvar o WAV.

Esta etapa registrou a avaliação inicial do motor. A ligação ao backend foi
implementada depois, no registro "Clonagem em CPU conectada ao projeto". A
qualidade da clonagem continua sem homologação.

## O que foi aprendido e corrigido

O OpenVoice original aceita CPU. Nosso adaptador exigia CUDA mesmo nesse caso;
agora a execução CPU pode ser solicitada explicitamente, mantendo CUDA como
padrão e sem troca automática de dispositivo.

Na revisão fixada, o argumento `enable_watermark` era encaminhado a um
construtor-base que não o aceita. Um patch rastreável corrige essa passagem.
O pipeline desabilita o download implícito do watermark e carrega o checkpoint
local, com checksum verificado.

Os patches e locks também passaram a preservar LF no checkout Windows. A
conversão para CRLF alterava seus hashes e interrompia o build.

O cache Hugging Face apresentou links simbólicos ao container, rejeitados pelo
sidecar. O utilitário agora materializa os cinco arquivos Kokoro em outro
diretório, preservando os mesmos bytes, a revisão e o cache original. Os pesos
OpenVoice/WavMark são obtidos por streaming e conferidos por tamanho e SHA-256.

## Evidência real

- Referência: voz stock sintética `pm_alex`, gerada localmente pelo Kokoro.
- Fala convertida: outro texto, sintetizado primeiro pela base `pf_dora`.
- Execução: 176,656 segundos para o pipeline CPU, em um único caso.
- Pico de RSS do processo: 1.797.672.960 bytes, dentro do container limitado a 3 GiB.
- Resultado: WAV mono de 24 kHz, com watermark decodificado no arquivo persistido.
- Isolamento: sem rede, filesystem principal somente leitura e modelos de leitura.
- Limpeza: container removido e ausência conferida no daemon.
- Regressão: 29 testes de dispositivo, assets, sidecars, patches e locks aprovados.

Nenhuma pessoa real participou. Os identificadores usados nesse teste são
referências sintéticas; não criaram consentimentos ou aprovações no sistema.
Áudios, logs e recibos completos permanecem privados no localhost.

O inventário local Syft identificou 820 componentes na imagem CPU. Os digests da
imagem e dos dois formatos de SBOM ficaram registrados no resumo versionado;
esse inventário não equivale à aprovação da cadeia de licenças.

## O que permanece pendente

O OpenVoice converte o timbre. Sotaque e emoção dependem da voz-base, conforme
explicado pelo próprio projeto. Não foi medida a semelhança com uma pessoa real,
a inteligibilidade, a preservação de sotaque ou o p95 de desempenho.

Na avaliação inicial descrita aqui, os jobs `voice_clone` ainda usavam o perfil
GPU. A integração seguinte acrescentou um provider e uma fila CPU próprios,
preservando os perfis GPU existentes. Nenhum worker passou a anunciar esse modelo
e nenhuma homologação foi criada nesta etapa.

A integração de rosto, personagens e avatar continua em andamento, incluindo a
validação dos modelos e de suas entregas. Este teste de voz não comprova esses
outros recursos.

## Referências

- [Implementação OpenVoice fixada](https://github.com/myshell-ai/OpenVoice/blob/74a1d147b17a8c3092dd5430504bd83ef6c7eb23/openvoice/api.py)
- [Limites da conversão de timbre](https://github.com/myshell-ai/OpenVoice/blob/74a1d147b17a8c3092dd5430504bd83ef6c7eb23/docs/QA.md)
- `workers/speech-cpu/openvoice-candidate/README.md`
- `benchmarks/studios/identity/openvoice-cpu-local-run-2026-10-25.v1.json`
- `backend/tests/test_openvoice_cpu_runtime.py`
