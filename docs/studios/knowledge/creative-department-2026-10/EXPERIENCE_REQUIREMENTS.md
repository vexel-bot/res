# Requisitos de experiência: pedido, direção e entrega

O cliente está dirigindo um departamento criativo. Conteúdo é a entrada prioritária; anúncio é a segunda frente. Pesquisa e produção aparecem por sua contribuição ao resultado, enquanto timeline, camadas, renderização, filas e verificações técnicas permanecem internos. Este documento orienta o próximo design; não define uma tela nem altera o frontend atual.

## Pedido

| ID | Requisito | Evidência que orienta | Critério de aceite proposto |
| --- | --- | --- | --- |
| P01 | Receber um objetivo em linguagem natural e o contexto encaminhado pela KLIC | F01, F12 | O cliente consegue pedir uma explicação, uma posição de autoridade ou uma oferta sem escolher ferramenta de edição. |
| P02 | Confirmar o público, a tarefa e o produto/serviço quando afetam a direção | F10, F12, F13 | O departamento não supõe que uma peça para investidor serve ao comprador do produto. |
| P03 | Reutilizar identidade, materiais e decisões anteriores com origem explícita | F03, F08, F16 | O cliente reconhece a marca e só fornece o que estiver ausente ou desatualizado. |
| P04 | Distinguir informação confirmada de lacuna | F05, F15 | Não aparecem testemunhos, resultados, preços ou estoques inventados. Uma pergunta explica por que a informação é necessária. |
| P05 | Oferecer exemplos de objetivos, sem obrigar formulário extenso | F11 | Uma pessoa sem repertório técnico entende o que pode pedir e chega a um pedido suficiente. |

Texto exemplificativo de pedido: “Quero ajudar quem cuida do estoque a descobrir por que os números não batem, usando nosso processo.” É um exemplo fictício EX01. O departamento pode sugerir público e formato, mas confirma fatos determinantes.

## Escolha da direção

| ID | Requisito | Evidência que orienta | Critério de aceite proposto |
| --- | --- | --- | --- |
| D01 | Apresentar inicialmente duas ou três direções com diferenças de argumento | F01, F11 | As opções não são o mesmo roteiro com cores diferentes. Quantidade é hipótese a testar. |
| D02 | Explicar para quem serve, o que comunica, valor entregue e razão da recomendação | F04, F10, F12 | O cliente consegue explicar sua escolha com palavras próprias. |
| D03 | Indicar formato e tratamento como consequência da mensagem | AS-IG-01/02, HZ-IG-01 | A peça pode ser simples quando a mensagem permite, ou demonstrativa quando a compreensão exige. |
| D04 | Mostrar uma abertura ou trecho ilustrativo sem simular produção concluída | F07 | O cliente distingue proposta editorial de entrega pronta. |
| D05 | Permitir ajuste de direção em linguagem de intenção | F08, F14 | “Mais direto”, “menos promocional” ou “mostre o processo” produz revisão editorial, sem abrir controles técnicos. |
| D06 | Explicar lacunas que afetam a viabilidade | F05, F15 | Uma direção que depende de demonstração indisponível não é oferecida como igualmente executável. |

Exemplo fictício de comparação EX04: “Qual filtro cabe no seu coador?” resolve compatibilidade por guia visual; “A montagem sem peças faltando” demonstra a sequência. A diferença está na pergunta e na forma de entregar valor. O cliente não escolhe PhotoCraft ou FilmCraft.

Referências podem aparecer como uma justificativa curta e pertinente. O acervo de autores e frameworks não deve ser um catálogo obrigatório de “escolha sua personalidade”. O cliente não está contratando uma imitação de Hormozi ou Alfredo.

## Revisão da entrega

| ID | Requisito | Evidência que orienta | Critério de aceite proposto |
| --- | --- | --- | --- |
| E01 | Apresentar a peça pronta para julgamento, junto da mensagem e do objetivo | F02, F07 | O cliente avalia a entrega sem operar montagem ou controle de qualidade técnico. |
| E02 | Resumir o que mudou entre versões | F03, F06 | A comparação informa mudança de tese, abertura, prova ou embalagem sem apagar a versão anterior. |
| E03 | Solicitar revisão de adequação, precisão de contexto e representação da marca | F08, F14 | O cliente não recebe checklist de fontes, mixagem, codecs ou correção de renderização como tarefa. |
| E04 | Aceitar comentários sobre um trecho e pedidos em linguagem natural | F07 | Um pedido de ajuste preserva fatos e contexto; alterações materiais recebem nova revisão. |
| E05 | Mostrar pendências relevantes de modo honesto | F05, F15 | Não mostrar “pronto” quando preço, autorização ou afirmação necessária não foi confirmado. |
| E06 | Registrar aprovação vinculada à versão | Continuidade e governança do projeto | Exportação e uso referenciam a entrega aprovada; revisão posterior não a substitui silenciosamente. |
| E07 | Conectar continuidade à intenção editorial | F03, F16 | “Adaptar para outro canal”, “aprofundar a ideia” e “continuar a série” têm significado e origem diferentes. |

Exemplo fictício de revisão EX08: “O exemplo está claro, mas explique quando a diretoria ainda precisa de contexto.” O departamento ajusta a narrativa e confere a produção antes de reapresentar. O cliente não reposiciona slides ou corrige áudio para resolver o pedido.

## Sinais e estados compreensíveis

Usar estados que informam o que o cliente pode fazer: pedido em preparação, direções disponíveis, direção escolhida, produção em andamento, ajuste necessário, entrega para revisão, aprovada. Progresso só será mostrado quando medido; não inventar percentuais ou prazo. A operação interna mantém estados mais detalhados sem torná-los a navegação principal.

Explicações sobre decisões podem ser consultadas sob demanda: “Por que esta direção?”, “Quais informações precisam de confirmação?” e “O que mudou?”. Elas apresentam justificativas verificáveis, não raciocínio privado dos modelos nem comandos técnicos.

## Validação anterior ao protótipo

Os nove exercícios documentais demonstram diferenças de direção por contexto. Ainda será necessário observar clientes executando as três decisões. O roteiro de teste deve conferir se a pessoa consegue formular um objetivo, distinguir alternativas e avaliar o resultado sem orientação sobre ferramentas. Não foram realizados testes de compreensão ou estudos de usabilidade nesta rodada.

Critérios de rejeição: a pessoa escolhe pela ferramenta porque não entende o argumento; precisa editar para conseguir revisar; confunde proposta com entrega; aprova uma versão diferente da exibida; atribui ao departamento um resultado comprovado que é apenas hipótese. Um caso desses exige revisão da experiência antes de avançar.
