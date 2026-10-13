# Clicko Studios — proposta de experiência e papel no produto

Data: 13 de outubro de 2026.
Status: proposta para discussão e próxima prototipagem; não altera a aplicação.

## Objetivo definido pelo usuário

Os Studios devem atender a duas necessidades: criar campanhas completas para
marcas e negócios e sustentar a produção recorrente para redes sociais. A
interface deve organizar essas entregas dentro do Clicko, com edição de imagem,
vídeo e composição disponível durante o refinamento.

O primeiro protótipo colocou canvas, propriedades, camadas e timeline no centro
da experiência. A nova proposta coloca objetivo, direção criativa, conjunto de
conteúdos e aprovação no centro. A unidade de trabalho passa a ser uma produção
vinculada a uma campanha ou ao planejamento recorrente da marca.

## Papel dos Studios

Os Studios transformam uma intenção de marketing em conteúdos coerentes com a
marca, editáveis e prontos para revisão. O sistema principal continua responsável
pela memória da marca, Radar, campanhas, calendário, aprovação, publicação e
analytics. Os Studios recebem esse contexto e entregam a produção de volta às
mesmas entidades, sem criar um segundo calendário, cadastro de marca ou fluxo
paralelo de aprovação.

Esta direção retoma a intenção já descrita em `docs/CLICKO_STUDIOS_STRATEGY.md`,
`STUDIOS_FUNCTIONAL_REQUIREMENTS.md` e no plano de CX: direção criativa,
produção, variações, revisão e aprendizado como jornada contínua. As referências
a motores antigos nesses documentos são históricas; a implementação Craft
atual continua sendo a base da edição.

## Duas jornadas, uma estrutura de produção

| Jornada | Entrada | Decisões principais | Entrega |
|---|---|---|---|
| Campanha | Campanha existente, oferta, público, objetivo, período e canais | Conceito central, narrativa, conjunto de peças e variações | Pacote coerente com roteiros, textos, peças, vídeos e adaptações por canal |
| Conteúdo recorrente | Marca, período, pilares, frequência, oportunidades e materiais disponíveis | Equilíbrio dos temas, prioridades da semana e formatos adequados | Lote de conteúdos ligado ao calendário existente, com revisão por peça ou conjunto |

Uma terceira ação contextual, reaproveitar material, alimenta ambas as jornadas.
Ela transforma um vídeo, uma entrevista, uma peça ou um conteúdo aprovado em
novas entregas, preservando sua origem.

O objeto de produção deve reunir: contexto utilizado, direção escolhida,
entregas solicitadas, versões e materiais, responsáveis, pendências e próxima
decisão. Cada peça mantém seu documento editável e sua revisão própria.

## Jornada proposta

1. **Definir a intenção.** O contexto vem da marca e da campanha ou do calendário.
   O usuário complementa o que falta: oferta, público, materiais ou restrições.
2. **Escolher a direção.** O Clicko propõe conceitos comparáveis, com promessa,
   gancho, narrativa, exemplos de abordagem e justificativa. Uma direção manual
   também pode ser fornecida.
3. **Definir as entregas.** O usuário confirma o conjunto de peças e canais.
   Escopo e estimativa de produção ficam claros antes da execução.
4. **Produzir os rascunhos.** Texto, roteiro, cenas, imagens e vídeos usam a mesma
   direção. Material ausente vira uma pendência acionável, como enviar um take.
5. **Refinar.** Pedidos como encurtar a abertura, trocar o CTA, adaptar para Stories
   ou destacar o produto atuam sobre uma peça ou seleção explícita. Ajustes rápidos
   e edição detalhada permanecem acessíveis.
6. **Comparar e revisar.** O usuário compara versões, comenta e envia a revisão
   exata para o fluxo de aprovação existente.
7. **Entregar ao calendário e à publicação.** As peças aprovadas seguem para as
   superfícies existentes. Mudanças relevantes exigem nova revisão.
8. **Aprender com resultados.** Dados observados dos canais orientam sugestões
   futuras quando disponíveis; o sistema indica quando faltam evidências.

## Papel da IA e do controle manual

A IA propõe direções, escreve, organiza cenas, sugere selects, cria adaptações
e aplica mudanças inspecionáveis. Deve mostrar a intenção e o alvo da alteração,
preservar histórico e permitir comparação e desfazer.

O usuário controla a direção, os materiais, as versões e a aprovação. Na produção
recorrente, pode aprovar uma pauta ou um lote; na campanha, pode validar primeiro
o conceito central e depois as entregas. O grau de autonomia deve ser configurado
por marca e tipo de tarefa, com publicação seguindo as permissões existentes.

A experiência de refinamento tem três níveis:

| Nível | Ações visíveis | Quando aparece |
|---|---|---|
| Dirigir | Alterar o tom, fortalecer o gancho, trocar a abordagem, criar variações | Durante a escolha e o refinamento da criação |
| Ajustar | Texto, CTA, cena, produto, duração, legenda, formato | Ao abrir uma peça ou selecionar um trecho |
| Editar em detalhe | Camadas, máscaras, cortes, tracks, efeitos e keyframes | Quando o usuário precisa de controle preciso |

PhotoCraft, FilmCraft e EffectCraft continuam clonados integralmente. Seus
recursos sustentam a edição e o acabamento. A interface principal dos Studios
apresenta o trabalho e suas entregas; os controles detalhados aparecem no
contexto da peça selecionada.

## Arquitetura de experiência a prototipar

### Entrada dos Studios

Ações principais: produzir uma campanha, preparar os próximos conteúdos e
reaproveitar material. A entrada mostra produções em andamento e decisões
pendentes, vinculadas à marca. O usuário retoma o trabalho na etapa em que parou.

### Área da produção

Objetivo e direção escolhida ficam visíveis junto ao conjunto de entregas.
Conceitos, roteiros, peças e variações são organizados pela produção. A próxima
ação acompanha seu estado: escolher direção, confirmar entregas, enviar material,
comparar versões ou revisar.

Um pedido em linguagem natural atua como uma das formas de interação. Cartões
de direção, previews, campos editáveis e comparações também precisam funcionar
sem depender de uma conversa longa.

### Refinamento de uma peça

O preview ocupa a área principal. O usuário altera o conteúdo e vê o resultado,
com pedidos dirigidos e ajustes contextuais. Vídeo começa por roteiro e cenas;
carrossel começa por argumento e sequência de páginas. Timeline e camadas abrem
quando o trabalho exige precisão.

### Revisão e entrega

A produção mostra o conjunto de entregas, suas versões, comentários e pendências.
O aprovador compreende a intenção e consegue decidir sem entrar na bancada
técnica. Calendário, publicação e resultados são acessados nas áreas existentes
do Clicko, com o contexto da produção preservado.

## Exemplos concretos

**Campanha:** lançar o café Aurora no Instagram e Meta Ads. O usuário fornece
oferta, público e materiais disponíveis. Escolhe uma direção criativa e confirma
duas sequências de carrossel, três vídeos curtos, seis Stories e duas variações de
anúncio. O Clicko mantém o argumento, a identidade e o CTA coerentes, permitindo
aprovação individual das versões. Quantidades são um exemplo, não uma regra.

**Recorrência:** preparar a próxima semana da marca. A pauta combina educação,
bastidores, prova e oferta, conforme a estratégia da marca. Uma gravação pode
alimentar um vídeo curto, um carrossel e Stories. O usuário revê a pauta, refina
as peças e envia o lote para aprovação e agendamento no calendário existente.

## Referências pesquisadas

Pesquisa de páginas públicas e documentação oficial em 13/10/2026. São referências
de organização de produto; não houve teste de qualidade, custo ou desempenho
em contas desses serviços. A aplicação ao Clicko é uma recomendação nossa.

| Referência | Capacidade descrita pela fonte | Padrão útil para o Clicko |
|---|---|---|
| [Jasper Canvas](https://help.jasper.ai/hc/en-us/articles/37817833127963-Jasper-Canvas) | Projeto reúne assets e contexto de marca, público e objetivo; canvas oferece assistência e colaboração | Um conjunto de entregas compartilha uma direção e contexto de campanha |
| [Adobe GenStudio](https://business.adobe.com/products/genstudio-for-performance-marketing/brand-compliance.html) | Diretrizes de marca, assets aprovados e fluxos de revisão e aprovação | Produção coerente e aprovação ligada às versões das peças |
| [Predis.ai](https://predis.ai/ai-social-media-manager/) | Criação de posts, carrosséis e vídeos ligada ao planejamento, agendamento e calendário | Produção recorrente organizada por marca e período |
| [StoryChief](https://www.storychief.io/agencies) | Workspaces por cliente, contexto da marca, produção, aprovação e distribuição | Continuidade do trabalho e colaboração com o aprovador |
| [Creatify](https://help.creatify.ai/en/articles/12435455-url-to-video) | URL de produto ou materiais enviados como entrada para anúncio em vídeo | Começar pelo produto e pela intenção comercial |

## Critérios para a próxima rodada

- O usuário inicia uma campanha ou lote recorrente sem precisar abrir um canvas
  vazio ou escolher um motor.
- A intenção e a direção escolhida permanecem claras durante toda a produção.
- Cada peça pode ser refinada sem perder a relação com a campanha e a marca.
- O usuário entende a próxima decisão e encontra resultados e pendências.
- O aprovador decide sobre a versão correta, com contexto e comentários.
- A edição detalhada é acessível quando necessária, com o mesmo projeto e histórico.
- A jornada usa os domínios existentes do Clicko para aprovação, calendário,
  publicação e resultados.
- O sucesso é avaliado pelo tempo até conteúdo aprovado, retrabalho e entregas
  úteis ao objetivo, com métricas dos canais quando disponíveis.

O próximo protótipo deve representar uma campanha e uma semana de produção
recorrente completas, desde a entrada contextual até a revisão. Essa rodada
validará a organização do trabalho antes de aprofundar o acabamento visual dos
controles de edição.
