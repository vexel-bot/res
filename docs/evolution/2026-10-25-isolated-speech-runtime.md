# Execução isolada de voz no localhost

O backend ganhou uma configuração privada para os runtimes de narração e
clonagem. Ela conecta os adaptadores existentes de Kokoro, Chatterbox e OpenVoice
aos pedidos dos projetos e à produção editorial. A configuração não aprova um
modelo, nem troca a voz escolhida pelo cliente.

## O que foi implementado

- Execução Kokoro em container local, sem instalar Torch na API.
- Configuração versionada de runtime, modelo, revisão, worker e imagem exatos.
- Verificação da homologação antes de resolver e executar o adaptador.
- Rejeição de outra versão/modelo/imagem e rechecagem após revogação.
- Cancelamento com remoção do container, também durante a partida.
- Diagnóstico privado de falhas, separado do código de erro apresentado na API.
- Descoberta da configuração privada pelo launcher do localhost.

Os três adaptadores de clonagem configuráveis continuam usando suas referências
de voz autorizadas e as verificações de assets já existentes. Esta entrega não
qualificou esses modelos nem produziu uma clonagem real.

## Evidência real

Uma frase sintética fixa foi gerada pelo Kokoro `pf_dora`, com os assets fixados e
a imagem local identificada por digest. O WAV tem 2,75 segundos, mono, 24 kHz. O
processo de controle não importou Torch. A execução completa levou cerca de 20,6
segundos; o tempo de síntese após a inicialização foi de cerca de 1,8 segundo.
Essas medidas não representam o p95 de produção.

A inspeção durante a execução confirmou rede desabilitada, filesystem principal
somente leitura, usuário não root, limites de CPU/memória e os dois mounts
privados do pedido e da saída. Uma segunda execução real foi cancelada após a
partida: o container foi removido e nenhum áudio foi persistido.

O teste encontrou uma dependência real do phonemizer: o carregamento de sua cópia
temporária do eSpeak exige memória mapeável para execução. Foi acrescentado um
tmpfs específico de 64 MiB; `/tmp` continua com `noexec`.

O inventário local Syft gerou um SBOM CycloneDX com 846 componentes. O hash desse
inventário e as observações do teste estão no resumo de verificação versionado.
O SBOM completo, os logs e o áudio permanecem no armazenamento privado local.

A regressão final passou em 78 testes do backend e cinco testes do launcher. Os
testes de orquestração usam fixtures explícitas para modelos; somente a execução
Kokoro e o cancelamento descritos acima usaram o runtime real nesta etapa.

## Limites mantidos

O benchmark histórico de 64 casos continua reprovado em latência, com avaliação
humana e revisão de licenças pendentes. Um caso real bem-sucedido não o substitui.
Os workers de avaliação continuam sem anunciar providers; nenhum registro foi
promovido por essa configuração.

A homologação real de clonagem de voz, geração de personagens e avatar ainda
faz parte da integração em andamento. A GPU local de 4 GB não qualifica os perfis
atuais de avatar LongCat e de clonagem Chatterbox.

## Referências de implementação

- `docs/studios/LOCAL_SPEECH_RUNTIMES.md`
- `backend/app/services/studios/speech_runtime.py`
- `backend/app/providers/studios/kokoro_docker.py`
- `backend/scripts/check_kokoro_docker_runtime.py`
- `benchmarks/studios/identity/kokoro-local-sidecar-smoke-2026-10-25.v1.json`
- `backend/tests/test_speech_runtime.py`
- `backend/tests/test_kokoro_docker.py`
