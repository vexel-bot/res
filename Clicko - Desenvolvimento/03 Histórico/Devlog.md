# Devlog

Adicione a entrada mais recente no topo. Quando uma mudança afetar um fluxo, atualize também a nota correspondente e o [[Roadmap]].

## 28/11/2026 — Estratégia de copy para anúncios em vídeo

- **Mudança.** O [[Estúdio de Vídeo]] usa briefing, campanha vinculada e evidência registrada para preparar o argumento comercial conforme o tipo de oferta e o momento do público. O fluxo sob demanda gera duas aberturas com o mesmo corpo. A revisão salva segue no briefing do Claude com as condições, a prova e o CTA.
- **Verificação local.** No navegador em perfil DEV isolado, o teste conferiu contexto incompleto, validade das fontes, comparação das aberturas com resposta simulada, persistência por projeto e exportação da revisão escolhida. Passaram o TypeScript, os testes do contrato da copy e os cinco testes do serviço versionado. As duas falhas da suíte geral ligadas à navegação dos Crafts também ocorreram na versão anterior.
- **Validação editorial.** A qualidade do texto do provedor e a primeira exibição do vídeo ficam para uma produção autorizada. A validação técnica usou uma oferta fictícia e a saída para o Claude foi conferida no JSON.

## 28/11/2026 — Roteiro e decupagem prática no briefing

- **Mudança.** O [[Estúdio de Vídeo]] inclui orientação de roteiro em cada briefing. Há exemplos e hipóteses de A/B para anúncio de resposta direta, conteúdo explicativo e história de marca. Quatro grupos disponibilizam 20 técnicas de decupagem com exercícios e perguntas de revisão. O Claude escolhe quais aplicar.
- **Verificação local.** O teste de navegador abriu um projeto DEV isolado, baixou o briefing padrão, conferiu as três opções de roteiro, exportou um grupo e o conjunto das 20 técnicas, importou um plano de montagem e confirmou a limpeza das seleções ao reabrir o projeto.
- **Validação editorial.** A primeira exibição deve verificar se o público reconhece o tema, identifica a consequência e entende a prova. A validação da integração verificou o conteúdo que chega ao arquivo de briefing.

## 28/11/2026 — Conhecimento audiovisual no briefing para Claude

- **Mudança.** O [[Estúdio de Vídeo]] exporta os cartões selecionados de voz, narração, decupagem, efeitos, trilha e ambiência. O cofre criativo reúne as análises da Sol e de startups e seis comparações com material existente.
- **Verificação local.** A validação de navegador em um perfil DEV isolado confirmou o download básico, a seleção de dois cartões completos e o retorno a um projeto com seleção vazia. Os exemplos de montagem permanecem compatíveis. O TypeScript passou na verificação.
- **Validação do Claude.** O ensaio de transferência com briefing fictício chegou à tentativa de autenticação da assinatura, que retornou HTTP 401. A próxima validação depende de uma sessão válida. A resposta de uma pessoa à primeira exibição dos A/B também está em aberto.

## 26/11/2026 — Cofre de desenvolvimento

- **Mudança.** Criado o cofre versionado de produto e engenharia. A primeira nota técnica descreve o [[Estúdio de Vídeo]]. O acervo audiovisual segue no cofre local **Clicko - Segundo Cérebro**.
- **Verificação.** Entradas iniciais conferidas contra os caminhos de código, testes e documentação versionados.
- **Próximo passo.** Atualizar o mapa e o estado do roadmap na próxima alteração de produto.

## 25/11/2026 — MoneyPrinterTurbo assume a montagem de vídeo

- **Mudança.** O Claude pode produzir cenas à parte e entregar o plano de montagem à Clicko. O motor monta os clipes e a mixagem. Os projetos anteriores podem ser consultados e baixados.
- **Verificação.** Navegador e API passaram pela montagem e entrega do MP4. O teste verificou corte e áudio. O worker Linux renderizou um MP4. Um projeto antigo real forneceu um vídeo e um material com as rotas Craft desativadas. [Teste de montagem](https://github.com/vexel-bot/res/blob/main/backend/tests/test_moneyprinterturbo_assembly.py)
- **Limpeza local.** Foram removidas 12 imagens dedicadas dos Crafts e do HeyGem. A limpeza reduziu em 22,02 GB o espaço atribuído a imagens pelo Docker antes da instalação do novo worker. O contêiner remanescente dos Crafts foi removido em seguida, com o volume preservado.
- **Código.** [2908fb86b na main](https://github.com/vexel-bot/res/commit/2908fb86b0d51604a181eea3801ea31b74b912e7)
- **Próximo passo.** Instalar o novo worker e verificar a montagem e os downloads no ambiente publicado.
