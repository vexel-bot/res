# Rosto e personagens: geração de imagens em integração

Foi preparado um caminho específico para gerar uma imagem com a aparência
selecionada, usando Qwen Image Edit 2511. Ele recebe a referência da pessoa ou
personagem e pode receber também a imagem escolhida para a cena. LongCat
continua responsável pelo caminho de apresentação em vídeo.

Esta etapa implementa o contrato, o adaptador, o worker, a admissão comercial e
os controles do projeto. O modelo real ainda não foi qualificado para uso pelo
cliente. A composição de um retrato existente no PhotoCraft continua sendo uma
operação distinta; ela não comprova a geração de novas poses ou cenas.

## Referência e imagem escolhida

O pedido registra versão da aparência, autorização, referência e imagem alvo,
com os checksums correspondentes. Direção, dimensões, seed e quantidade de
passos também ficam explícitos. O modelo recebe a referência como primeira
imagem e a cena como segunda, com uma instrução que identifica esses papéis.

O retorno deve corresponder ao pedido, às imagens, ao modelo e ao PNG produzido.
O adaptador confere o recibo antes de copiar o resultado para o destino privado.
Cancelamento, timeout ou recibos incompatíveis não persistem uma nova imagem.
Arquivos de origem e saídas anteriores não são substituídos.

O planejamento do projeto confere a seleção ativa por meio do resolvedor de
elenco, recupera a referência da versão escolhida e verifica se a cena pertence
ao mesmo workspace. O plano registra a revisão do projeto, o elenco, as duas
imagens e seus checksums. Essa função ainda não inicia um job nem substitui as
verificações necessárias durante e depois da execução.

O endpoint autenticado de planejamento do projeto recebe a revisão e a direção,
recusa alterações concorrentes e retorna o plano. O teste de API e banco usa
metadados sintéticos e cobre acesso de outro usuário e revogação. Nenhuma
geração é iniciada por esse endpoint.

O serviço interno de execução foi preparado para materializar as imagens,
conferir seus checksums e salvar a saída privada para revisão. Ele exige um
provider e um modelo aprovados e revalida o plano, o elenco e a admissão depois
do processamento. Os testes de banco e armazenamento usam um provider de cores
simulado e verificam também que a revogação durante a execução impede a saída.
O tipo de job encaminha a execução para a fila de visão, e um resultado já salvo
pode ser recuperado pelo mesmo job sem repetir a inferência. O endpoint do
projeto valida o plano e a revisão; na sessão Clicko, a ponte reserva uma geração
de imagem e vincula o recibo ao projeto e à chave do pedido. A rota genérica não
pode criar esse trabalho. O Studio permite descrever a cena, acompanhar o pedido,
revisar a imagem privada e escolhê-la para a entrega. A seleção preserva o
material original e é conferida novamente antes da produção. Quando há uma
cena escolhida, a imagem gerada é usada como material visual da entrega e a
cena original continua registrada entre os assets do documento. Um pedido cuja
resposta não foi confirmada pode ser recuperado na mesma aba após recarregar.
Na primeira composição editorial, a cena quadrada ocupa uma área maior e o
texto fica em uma coluna separada. A geometria foi verificada no documento de
teste; a aparência de uma exportação real continua pendente de validação.
O painel também consulta a disponibilidade do provider antes de habilitar uma
nova geração; pedidos já iniciados continuam recuperáveis enquanto ele estiver
indisponível.
Testes da ponte exercitam repetição, escopo e resposta inconsistente; testes do
backend usam um provider simulado e verificam a admissão e a revogação.
Um teste produz o documento com uma cena de teste e confere tanto o uso do
resultado gerado quanto a preservação do asset original; a renderização e o
modelo são simulados nesse teste.

## Fontes, recursos e alcance dos testes

O código Qwen foi clonado integralmente para a área local de candidatos, sem
checkout raso. A revisão contém 15 arquivos rastreados e o clone preserva os
86 commits disponíveis nas referências obtidas. Os Crafts não foram alterados.

O inventário do modelo fixa revisão, tamanho e SHA-256 dos 35 arquivos upstream.
Somente os safetensors somam 57.699.249.798 bytes. Os pesos não foram baixados;
a preparação exige uma ação explícita e espaço livre suficiente.

Foram preparados testes com imagens geométricas e um pipeline substituto,
além de execução de subprocesso para conferir transporte, recibos e cancelamento.
Esses testes não demonstram semelhança facial ou qualidade generativa.

A verificação real deste computador identificou uma GPU de 4 GiB. O perfil
baseline não quantizado não cabe nela. A checagem rejeita a partida e não troca
automaticamente o modelo, o dispositivo ou a aparência escolhida.

## O que continua necessário

- Validar o fluxo visual completo com um modelo real aprovado e a entrega final.
- Validar o runtime isolado com pesos em hardware compatível.
- Avaliar preservação de aparência, obediência à direção, imagem alvo e qualidade.
- Concluir a qualificação do modelo e da cadeia de dependências.

O modelo não foi aprovado para uso do cliente e não entrou automaticamente no
catálogo. A integração de rosto, voz e personagens permanece em andamento.

## Evidências

- `backend/app/domain/studios/appearance_image.py`
- `backend/app/providers/studios/qwen_appearance.py`
- `backend/app/services/studios/project_appearance.py`
- `backend/app/routers/studio_department.py`
- `backend/tests/test_project_appearance_plan.py`
- `backend/tests/test_project_appearance_execution.py`
- `src/studios/department/ProjectAppearance.tsx`
- `server/studios/appearanceQuota.test.ts`
- `backend/scripts/download_appearance_model_assets.py`
- `workers/identity-image/model-assets.v1.json`
- `workers/identity-image/runner.py`
- `workers/identity-image/tests/test_runner.py`
- `workers/identity-image/README.md`

Fontes primárias:

- [Qwen Image](https://github.com/QwenLM/Qwen-Image)
- [Modelo de edição e exemplo com múltiplas imagens](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)
