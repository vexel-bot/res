# Kokoro + OpenVoice em CPU: avaliação local

Este candidato executa síntese pt-BR, extração dos embeddings de origem e
referência, conversão de timbre e WavMark com pesos locais. Não usa CUDA, não
carrega Whisper/Silero e não aprova nenhum modelo ou perfil de voz no banco.

O primeiro teste real usou somente a referência sintética `pm_alex` do Kokoro. A
fala convertida tem outro texto, produzido primeiro pela base `pf_dora`. Isso não
é uma avaliação com uma pessoa real, nem demonstra fidelidade humana, preservação
de sotaque ou qualidade comercial. OpenVoice converte o timbre; a voz-base continua
responsável pelo sotaque e pela emoção.

## Fontes e preparação

- OpenVoice `74a1d147b17a8c3092dd5430504bd83ef6c7eb23`, com patches explícitos.
- Kokoro `dfb907a02bba8152ca444717ca5d78747ccb4bec`, com G2P carregado por idioma.
- Misaki `fba1236595f2d2bf21d414ba6e57d25256afada3`.
- Torch/Torchaudio `2.6.0+cpu`, NumPy `1.26.4`, WavMark `0.0.3` e lock completo.
- Modelo Kokoro, conversor OpenVoice e checkpoint WavMark fixados nos manifestos.
- eSpeak substituído pela compilação já verificada de `7d426728...`.

O patch `openvoice-explicit-watermark-toggle.patch` retira `enable_watermark`
antes de encaminhar argumentos ao construtor-base do upstream. Assim, o
conversor aceita o watermark implícito desabilitado; a aplicação usa e verifica
seu checkpoint WavMark local, depois da conversão.

As fontes e os patches são verificados no target `source-audit` do Dockerfile GPU
v2, sem instalar suas dependências CUDA. A imagem CPU recebe esse target por uma
referência imutável `nome@sha256:...` e instala seu próprio lock CPU. Os patches e
locks com digest fixado conservam LF no checkout Windows.

No checkout, com `PYTHONPATH=backend`, prepare os assets usando
`backend/scripts/download_openvoice_model_assets.py`:

```powershell
$env:PYTHONPATH = 'backend'
$studioRepo = (Get-Location).Path
& .venv/Scripts/python.exe backend/scripts/download_openvoice_model_assets.py `
  --manifest workers/speech-gpu/openvoice-model-assets.v1.json `
  --asset-root "$studioRepo/.candidate-build/model-assets/openvoice-v2" `
  --kokoro-manifest .candidate-build/kokoro-model-assets.json `
  --kokoro-source-repository "$studioRepo/.candidate-build/hf-home/hub/models--hexgrad--Kokoro-82M" `
  --kokoro-target-repository "$studioRepo/.candidate-build/model-assets/kokoro-openvoice-base"
```

O utilitário verifica downloads por streaming, tamanho e SHA-256. A preparação
Kokoro materializa os cinco arquivos em um repositório local separado, com a mesma
revisão e os mesmos hashes, preservando o cache original. Essa cópia evita os
links simbólicos do cache, rejeitados pelo sidecar. Arquivos existentes com bytes
incompatíveis provocam erro; não são sobrescritos silenciosamente.

## Build e execução

1. Construa `workers/speech-gpu/Dockerfile.openvoice-candidate-v2` com target
   `source-audit`; registre o digest da imagem de fontes.
2. Construa `workers/speech-cpu/Dockerfile.openvoice-candidate` passando
   `OPENVOICE_SOURCE_IMAGE=nome-da-imagem@sha256:...` e
   `CPU_WORKER_MANIFEST_DIGEST` com o hash canônico de
   `workers/speech-cpu/openvoice.worker.manifest.json`. O build confere o
   manifesto incluído e grava os digests nas labels da imagem.
3. Execute `backend/scripts/check_openvoice_cpu_runtime.py` com os digests das
   imagens stock e clone, o repositório Kokoro regular, os assets OpenVoice e um
   diretório privado novo.

Argumentos da verificação:

- `--stock-image-digest`: imagem sidecar Kokoro stock, pelo digest local.
- `--clone-image-digest`: imagem CPU de conversão, pelo digest local.
- `--kokoro-repository`: repositório materializado com `snapshots/` e `refs/`.
- `--openvoice-assets`: diretório dos três arquivos OpenVoice/WavMark.
- `--output-directory`: caminho absoluto privado novo.
- `--docker-executable`: executável Docker absoluto, se necessário.

O script gera uma referência sintética, prepara um pedido tipado e chama
`OpenVoiceCPUProvider`, o mesmo adaptador resolvido pelo backend. Ele executa o
container sem rede e confere manifesto, referência, roteiro, WAV e watermark.
O container usa 4 CPUs, 3 GiB, filesystem principal somente leitura, usuário não
root e volumes de modelos/entrada somente leitura. O diretório temporário
executável atende eSpeak/Numba; desaparece com o container. A remoção e a ausência
do container são verificadas antes de aceitar o resultado.

O relatório, WAV, recibo da referência e logs ficam privados. Com
`--reuse-synthetic-reference <diretório anterior>`, é possível repetir somente a
conversão depois de verificar o recibo, o texto fixo, a imagem e o checksum da
referência sintética. O recibo identifica o artefato sintético do teste; não é uma
autorização de uso de voz humana.

Com `--mode cancel`, a verificação observa no daemon que o container está em
execução antes de cancelar. Exige a remoção verificada e a ausência de áudio de
saída. Essa opção também aceita uma referência sintética anterior verificada.

## Resultado e trabalho pendente

O teste de 25/10/2026 produziu 7,489 s de WAV com watermark verificado, a partir
de uma referência sintética de 7,1 s. O pipeline CPU levou 176,656 s e registrou
pico de 1.797.672.960 bytes de RSS. Esse caso não mede p95 nem qualidade humana.

Na verificação seguinte, o adaptador da aplicação produziu outra conversão de
7,489 s. O pipeline mediu 120,007 s e pico de RSS de 1.812.307.968 bytes. O
cancelamento também foi verificado em uma execução real. Os dois casos estão
registrados separadamente em
`benchmarks/studios/identity/openvoice-cpu-adapter-local-run-2026-10-25.v1.json`.
Não são um benchmark completo ou uma avaliação de identidade humana.

O backend agora resolve o kind `kokoro-openvoice-cpu-docker`, provider
`candidate.kokoro-openvoice-v2-cpu`, com fila `studio.speech.cpu`. Os outros
providers de clonagem preservam o perfil GPU. O teste de integração do projeto
confere essa fila, a voz selecionada, a autorização, a idempotência e a reabertura
do áudio privado, usando fixtures explícitas de admissão e daemon.

Os workers de avaliação continuam sem providers anunciados. Qualidade, benchmark
completo e revisão da cadeia de licenças seguem pendentes. A configuração não
aprova modelos ou vozes. Veja `docs/studios/LOCAL_SPEECH_RUNTIMES.md`.

Fontes primárias:

- [Implementação OpenVoice fixada](https://github.com/myshell-ai/OpenVoice/blob/74a1d147b17a8c3092dd5430504bd83ef6c7eb23/openvoice/api.py)
- [Limites da conversão de timbre](https://github.com/myshell-ai/OpenVoice/blob/74a1d147b17a8c3092dd5430504bd83ef6c7eb23/docs/QA.md)
