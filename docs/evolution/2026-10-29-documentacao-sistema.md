# Clicko: documentação do sistema e estado da evolução

**Referência:** checkout local `codex/evolution-and-identity`, inspecionado em 29/10/2026. Este documento é um mapa de navegação e de arquitetura; os registros individuais de Evolução conservam os detalhes e as evidências de cada mudança. O estado da branch local não comprova publicação na `main` ou implantação em produção.

## Objetivo do produto

A Clicko reúne contexto de marca, planejamento, criação e acompanhamento de conteúdo. Os Studios organizam o pedido, a escolha de direção e a revisão das entregas. A KLIC utiliza o contexto autorizado do workspace para apoiar o trabalho. Os recursos disponíveis dependem das permissões, configurações e integrações de cada ambiente.

## Áreas do sistema

| Área | Responsabilidade |
| --- | --- |
| Dashboard | Apresentar a operação e itens que exigem atenção. |
| Studios | Preparar conteúdo e anúncios em formatos de imagem, carrossel e vídeo; manter projetos, materiais e entregas. |
| Klic AI | Conversa e apoio à criação com contexto da marca. |
| Biblioteca | Organizar materiais; a área de rostos e vozes mantém perfis, versões e amostras. |
| Calendário | Organizar conteúdo e sua programação. |
| Conexões | Gerenciar contas e integrações disponíveis. |
| Clientes, aprovações e equipe | Organizar marcas, revisão e acesso conforme as permissões do workspace. |
| Automações e Analytics | Acompanhar fluxos e informações disponíveis para a operação. |
| Configurações | Administrar opções da conta e do ambiente. |
| Evolução | Consultar histórico, decisões, análises e pendências documentadas. |

Os itens apresentados na navegação variam conforme o modo da conta e o acesso do usuário. A presença de uma área não significa que todos os serviços externos ou modelos opcionais estejam configurados.

## Como os componentes se comunicam

O frontend React/TypeScript apresenta a aplicação. O servidor Express mantém a sessão e a governança Clicko e encaminha operações dos Studios ao serviço FastAPI por uma ponte autenticada. O backend de Studios mantém documentos, projetos, referências, trabalhos e registros de mídia. Os workers executam operações especializadas; o armazenamento mantém os arquivos e sua proveniência.

O navegador não precisa receber chaves de provedores. Uma operação pode depender de configuração local, direitos, cotas, worker e modelo específicos. A documentação de configuração e os testes de cada recurso são a fonte para seus requisitos concretos.

## Fluxo de criação nos Studios

1. O cliente informa objetivo, público, formato e materiais disponíveis para a marca.
2. O projeto apresenta direções editoriais e registra a escolha.
3. A produção usa materiais e referências vinculados ao projeto; quando aplicável, a aparência e a voz são escolhidas separadamente.
4. O sistema prepara documentos e trabalhos, conserva versões e disponibiliza a entrega para revisão.
5. A exportação e a publicação seguem as verificações e autorizações aplicáveis ao conteúdo e aos materiais.

Os fontes de PhotoCraft, FilmCraft e EffectCraft estão incorporados ao projeto para imagem, montagem de vídeo e composição. Sua presença no repositório, por si só, não comprova que toda capacidade upstream está disponível ou validada em cada ambiente.

## Rostos, vozes e personagens

A biblioteca permite cadastrar perfis e versões de aparência e voz, incluindo personagens e vozes licenciadas. O cadastro e a seleção preservam referências e autorizações; eles não equivalem à aprovação de um modelo generativo. Os pedidos de imagem, carrossel e vídeo podem guardar a aparência e a voz escolhidas.

Na composição de imagem existente, um retrato de referência pode ser usado como asset pelo PhotoCraft. A geração de uma nova cena com identidade preservada ainda está em integração. Para vídeo, há fluxo de narração e plano de apresentação ligados às escolhas do projeto; a validação generativa de avatar e a montagem completa com modelos reais continuam pendentes.

O adaptador Kokoro + OpenVoice em CPU foi exercitado com uma referência sintética, e o fluxo do projeto foi testado com fixtures. Isso não comprova a qualidade da clonagem de uma pessoa real. O candidato Qwen para imagens possui contrato e worker em desenvolvimento; os pesos e a inferência ainda não foram validados neste computador. O runner LongCat também depende de ambiente e pesos compatíveis e de avaliação audiovisual.

Consulte os registros **Rostos, vozes e personagens na biblioteca**, **Clonagem em CPU conectada ao projeto**, **Rosto e personagens: geração de imagens em integração** e **Runner de avatar preparado para qualificação** na área Evolução para acompanhar os limites de cada etapa.

## Evolução e documentação

O catálogo versionado `docs/evolution/catalog.json` aponta para documentos Markdown em `docs/evolution`. A API autenticada disponibiliza a lista, o conteúdo e o download; a interface `/evolution` permite pesquisar e filtrar os registros. Cada registro informa sua situação e evidências.

As situações distinguem o que foi integrado à main, o que está implementado na branch, o que está em andamento e o que foi planejado. Uma alteração futura deve acrescentar ou atualizar sua evidência e manter as pendências explícitas. Documentos históricos descrevem o que era conhecido na data registrada e podem ter atualizações posteriores.

## Ambiente local

O perfil de desenvolvimento usa `scripts/dev-local.mjs`. No PowerShell, a partir do checkout e com as dependências instaladas:

```powershell
$env:PORT = '3000'
$env:CLICKO_LOCAL_STUDIO_PORT = '8000'
node scripts/dev-local.mjs
```

Acesse `http://127.0.0.1:3000/evolution` e use `node scripts/dev-local.mjs status` ou `node scripts/dev-local.mjs stop` para consultar ou encerrar o perfil. Os dados privados de desenvolvimento ficam em `.codex-runtime/clicko-dev`; não devem ser publicados junto com o código. O perfil local não constitui implantação de produção nem autorização de gasto com provedores.

## Verificação e operação

`npm run lint`, `npm run build` e `npm test` são comandos gerais do projeto. Os testes específicos de cada integração são indicados nos respectivos registros e documentos de operação. Resultados de testes anteriores são evidência apenas da revisão e dos cenários em que foram executados; não representam automaticamente o estado atual da CI ou a qualidade de modelos reais.

Antes de distribuir ou operar um motor opcional, conferir sua versão, dependências, licença, configuração, capacidade do equipamento e evidências de validação. Para o trabalho em andamento, as principais pendências são a qualificação de voz e avatar com amostras autorizadas, a geração de novas imagens com a aparência escolhida e sua ligação completa aos projetos.

## Referências do projeto

- `README.md`: visão geral, comandos e histórico operacional.
- `src/components/Sidebar.tsx`: navegação e visibilidade por acesso.
- `server/studios/proxy.ts` e `backend/app/studio_routes.py`: ponte e rotas dos Studios.
- `backend/app/routers/product_evolution.py`: catálogo autenticado de evolução.
- `backend/app/routers/studio_department.py` e `backend/app/services/studios/casting.py`: projetos e referências de elenco.
- `docs/studios/LOCAL_IDENTITY_SETUP.md` e `docs/studios/LOCAL_SPEECH_RUNTIMES.md`: configuração e limites locais de identidade e voz.
