# Runtimes locais de voz

O backend resolve os adaptadores por uma configuração privada de implantação.
`STUDIO_SPEECH_RUNTIME_CONFIG_FILE` aponta para um JSON absoluto. O launcher local
também reconhece `speech-runtimes.json` dentro de seu diretório privado de dados,
sem substituir uma configuração explícita da variável de ambiente.

O arquivo usa `schemaVersion: studio.speech-runtime-config.v1` e uma lista
`runtimes`. Não é uma API para enviar comandos, módulos Python ou endpoints pelo
navegador. A configuração pertence ao operador do servidor e não é distribuída
nos assets do frontend.

## Adaptadores

| `kind` | Uso | Campos específicos |
| --- | --- | --- |
| `kokoro-docker` | Vozes stock `pf_dora`, `pm_alex`, `pm_santa` | `dockerExecutable`, `sourceRevision`, `modelRevision`, `modelDigestSha256`, `cpuHourlyCostUsd` |
| `chatterbox-multilingual-v3` | Clonagem a partir da referência autorizada | `manifestPath`, `assetRoot`, `command`, `gpuHourlyCostUsd` |
| `chatterbox-pt-br` | Variante de clonagem em português | mesmos campos de clonagem |
| `kokoro-openvoice-v2` | Síntese stock seguida de conversão para a voz autorizada | mesmos campos de clonagem |
| `kokoro-openvoice-cpu-docker` | Conversão de timbre em CPU, isolada em container | `dockerExecutable`, `manifestPath`, `assetRoot`, `kokoroManifestPath`, `kokoroRepository`, `cpuHourlyCostUsd` |

Todos exigem `workerManifestPath` absoluto e `workerImageDigest` no formato
`sha256:<64 hex>`. `timeoutSeconds` é opcional, entre 1 e 7200 segundos.
`command` é um array de argumentos cujo primeiro elemento é um executável
absoluto; é reservado à configuração local dos sidecars de clonagem existentes.
Não há interpretação por shell.

Os valores de custo são parâmetros contábeis da implantação. Não são uma cotação
do provedor de infraestrutura.

## Admissão e versões

Configurar um runtime não o homologa. Em cada nova execução, o backend verifica:

1. Registro aprovado para a capacidade, benchmark aprovado e anúncio no worker.
2. Versão exata do adaptador e digest exato do modelo aprovado para uso comercial.
3. Worker contendo o provider e o tipo de job, com a capacidade correspondente.
4. A revisão de fonte e o seguinte `runtimeBinding` no manifesto do registro:

```json
{
  "schemaVersion": "studio.speech-runtime-binding.v1",
  "kind": "kokoro-docker",
  "sourceRevision": "<commit completo>",
  "modelDigestSha256": "<digest do manifesto de assets>",
  "workerManifestDigestSha256": "<digest canônico do worker>",
  "workerImageDigest": "sha256:<imagem exata>"
}
```

Os outros kinds usam o mesmo contrato de binding. Alterar a imagem, o modelo ou o
worker exige um binding correspondente da versão homologada. O resolvedor não
insere candidatos nos mapas globais de providers, nem modifica os registros de
aprovação. Adaptadores registrados por outros plugins continuam utilizáveis sob
as regras existentes. A revogação é verificada novamente ao executar; um áudio
concluído continua sujeito às regras de autoria, roteiro e consentimento de sua
própria linhagem.

## Kokoro fora do processo da API

`KokoroDockerSpeechProvider` usa a imagem local pelo digest, sem puxar imagens no
momento da geração. O processo da API não importa Torch, Kokoro ou Misaki para
executar essa ponte. A imagem contém o modelo, a implementação e o eSpeak
verificados. O runner confere novamente os assets e o manifesto do worker.

Cada pedido cria primeiro um container identificado e depois o inicia. Isso
permite cancelar também durante a partida sem depender de matar apenas o cliente
Docker. O container roda sem rede, com filesystem principal somente leitura,
usuário não root, capabilities removidas e limites de 4 CPUs, 3 GiB e 128
processos. Somente o pedido/configuração de leitura e a pasta privada de saída
são montados. Não há montagem do socket Docker dentro do container.

O phonemizer carrega uma cópia temporária da biblioteca eSpeak. Por isso, há um
tmpfs executável de 64 MiB em `/run/clicko-phonemizer`, usado como `TMPDIR`; `/tmp`
continua com `noexec`. A cópia some ao remover o container.

Após sucesso, erro, timeout ou cancelamento, o adaptador remove o container e
confere sua ausência. Se a limpeza não puder ser verificada, a execução falha e o
áudio não é persistido. O resultado deve corresponder ao modelo, à revisão, ao
worker, à imagem, à versão, ao checksum e à duração do WAV medido.

As receitas de avaliação estão em `workers/speech-cpu/Dockerfile.candidate` e
`Dockerfile.sidecar`. O segundo recebe uma base local por referência imutável
`nome@sha256:...`. Os arquivos `.dockerignore` restringem o contexto aos inputs
necessários; chaves, bancos de dados e outras famílias de modelos ficam fora.

## Verificação de execução, sem promoção

Depois do build, rode `backend/scripts/check_kokoro_docker_runtime.py` com
`PYTHONPATH=backend` e os argumentos:

- `--image-digest`: digest da imagem sidecar obtido com `docker image inspect`;
- `--source-revision`: commit completo do código Kokoro incluído na base;
- `--model-manifest`: manifesto verificado do Kokoro;
- `--worker-manifest`: manifesto incluído na imagem;
- `--output-directory`: caminho absoluto privado novo, fora de `public` e `dist`;
- `--docker-executable`: executável Docker absoluto, quando necessário.

A verificação gera uma frase sintética fixa e conserva WAV e relatório privados.
Ela usa o mesmo adaptador da API, incluindo limpeza e validação do retorno. Não
acessa credenciais, não usa amostras pessoais e não escreve aprovação no banco.
Com `--mode cancel`, verifica uma partida real seguida de cancelamento e ausência
de áudio persistido, sem repetir a geração completa da frase.
Uma frase bem-sucedida não substitui o corpus de benchmark, a avaliação humana,
a revisão de licenças ou a qualificação dos modelos de clonagem e de avatar.

O benchmark histórico de Kokoro em CPU permanece reprovado em latência
(`kokoro-pf-dora-local-run-2026-08-26.v1.json`). Os manifests de avaliação mantêm
`providers: []`. Essas restrições não foram relaxadas pela configuração do runtime.

## Clonagem Kokoro + OpenVoice em CPU

O kind `kokoro-openvoice-cpu-docker` resolve o provider
`candidate.kokoro-openvoice-v2-cpu`. Somente esse provider encaminha `voice_clone`
para a capacidade `speech_cpu`, fila `studio.speech.cpu` e classe `cpu.speech`.
Os providers GPU mantêm seus perfis. O manifesto do sidecar é
`workers/speech-cpu/openvoice.worker.manifest.json`.

Todos os caminhos específicos desse kind são absolutos. `manifestPath` e
`assetRoot` identificam os assets OpenVoice/WavMark; `kokoroManifestPath` e
`kokoroRepository` identificam a base Kokoro materializada sem links simbólicos.
O manifesto de cada modelo é lido ao resolver a configuração. Os pesos são
conferidos somente na execução, sem importar Torch no processo da API.

A versão do provider inclui as revisões de fonte, modelo conversor e base.
O binding de admissão segue o contrato acima, usando esse kind. A imagem deve
conter os mesmos digests de ambos os modelos e do manifesto do worker. O
adaptador confere no daemon a imagem, os mounts e os limites realmente criados.
O retorno vincula voz selecionada, autorização, referência normalizada e roteiro.
Um recibo incompatível não produz áudio persistido.

O sidecar só aceita pt-BR, WAV mono PCM16 de 24 kHz e velocidade 1. A rotina de
verificação `backend/scripts/check_openvoice_cpu_runtime.py` chama esse mesmo
adaptador. `--mode cancel` espera observar o container em execução antes de
cancelar e conferir a limpeza. A receita completa e os argumentos estão em
`workers/speech-cpu/openvoice-candidate/README.md`.

Configurar essa entrada prepara o localhost, mas não aprova o candidato nem
altera o consentimento de uma voz. Os manifests de avaliação seguem com
`providers: []`; a disponibilidade da geração continua condicionada às
qualificações exigidas pelo sistema.
