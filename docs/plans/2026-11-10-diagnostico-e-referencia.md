# Diagnóstico editorial e reconstrução de referência

Atualização de implementação: [quatro correções no fluxo integrado](2026-11-10-clicko-quatro-correcoes.md). O modo de direção livre substitui a restrição de três cenas quando escolhido, recebe quadros reais da referência, exige produto/copy aprovados para anúncios e separa os pareceres técnico, do modelo e humano. A prova de integração é local, com transporte simulado do modelo e gasto externo zero; não muda a reprovação do anúncio anterior.

## Pedido e evidência

O usuário reprovou o anúncio com filmagem e demonstração da timeline. Esse feedback substitui a recomendação anterior de uso da peça. A avaliação anterior deu peso excessivo a execução, presença da prova e leitura de texto. As notas registradas não mediram qualidade percebida pelo usuário.

O estudo reabriu o Reel [DdwS-6oRvL8](https://www.instagram.com/reel/DdwS-6oRvL8/), publicado por @creators com crédito a @ruama. O player público estava acessível. Foram inspecionados os tempos 0, 0,5, 1, 1,5, 2, 2,5, 3, 4, 5 e 8 s. No primeiro intervalo, uma chamada grande aparece atrás da pessoa. Depois há mudança de enquadramento e legendas curtas. Em 8 s, o vídeo apresenta uma demonstração dentro de um telefone. O áudio original ficou sem avaliação.

Para isolar uma operação, a Clicko usou como matéria-prima o trecho de 2 a 8 s da própria filmagem, onde o título da abertura já havia saído. Foram preservadas as legendas pequenas que pertencem à fonte. A Clicko preparou um recorte temporal da pessoa e recompôs a chamada “TUTORIAL” entre a filmagem e o primeiro plano da pessoa. O título apareceu de 0,5 a 1,83 s do novo arquivo. Foram exportadas duas versões com a mesma matéria-prima e o mesmo título, uma com a palavra sobre a pessoa e outra com o primeiro plano da pessoa sobre a palavra.

A reconstrução trata da operação de profundidade da abertura. A filmagem, as legendas existentes e a passagem para a interface no fim vêm da fonte. O escopo do ensaio é a oclusão da chamada sobre a filmagem da referência. A direção dessas operações foi guiada pelas medições deste estudo.

## Causas rastreadas

| Problema | Evidência no sistema | Efeito observado ou hipótese |
|---|---|---|
| Direção reduzida a uma estrutura fixa | Scene e Direction em scene_direction.py exigem três papéis, limitam pesos e oferecem três paletas. _motion posiciona três peças e uma barra em proporções fixas. | Confirmado que a montagem de motion converge para uma mesma composição. É uma explicação direta para a repetição entre briefs. |
| Parte da intenção vira apenas texto | Scene.intent entra no registro e no contexto da revisão. compile_direction executa os campos enumerados, sem interpretar livremente a descrição. O CTA e a legenda da prova da timeline recebem texto imposto pelo compilador. | Confirmado que uma intenção detalhada não garante uma operação correspondente. A revisão chegou a pedir desordem no gancho sem que a primeira versão do compilador a executasse. |
| Referência distante do planejamento | A base registra amostras e hipóteses. O contexto do modo por cenas fornece o projeto e seus quadros, sem importar os quadros da referência. | Confirmada a ausência do vídeo de referência no contexto visual desse modo. A semelhança estética não foi medida antes de recomendar os cortes. |
| Operações existentes fora do alcance do modo por cenas | A timeline canônica suporta faixas intercaladas de vídeo, título e máscara. O modo por cenas oferece cortes, três enquadramentos, paletas e ilustração de uma barra. | A reconstrução desta rodada executou a tipografia em profundidade com o motor já disponível. A capacidade do compilador específico limita o repertório entregue ao Opus. |
| Materiais e enquadramento pouco adequados ao anúncio | O anúncio anterior parte de uma tomada de ring light e telefone. A referência tem uma pessoa em quadro, gesto legível, escala variada e título integrado ao corpo. O close da interface foi acrescentado manualmente. | A tomada do telefone permite demonstrar gravação, mas oferece pouca ação editorial adicional. Esse limite foi encoberto por aproximações e tarjas. A força publicitária relativa segue sem teste com espectadores. |
| Copy centrada em uma tarefa | O roteiro do experimento usa “Gravou no celular”, “Divida clipes” e “Abra o Studio”. O dossiê de produto, prova e proposta comercial dos processos de copy não foi exigido na admissão desse ensaio. | A peça explica uma ferramenta. A promessa de valor do anúncio ficou pouco desenvolvida. A ligação com a rejeição estética é hipótese editorial, sustentada pelo feedback do usuário. |
| Aprovação técnica confundida com avanço criativo | motion_editorial_review verifica quadro uniforme, arquivo, áudio existente e texto local. A prova de timeline ainda precisou de uma checagem própria. As notas de conselho foram atribuídas a quadros e estrutura. | Confirmado que passed_technical pode coexistir com um anúncio rejeitado. A comparação anterior não teve avaliação cega de espectadores e não sustenta uma recomendação estética geral. |
| Ritmo sonoro não avaliado | O áudio foi congelado entre braços e comparado por hash. As referências anteriores não tiveram áudio auditado. | O hash comprova preservação. Ritmo, desenho de som e sincronia perceptiva continuam sem evidência. |

## Resultado do ensaio

A preparação local segmentou 144 frames com RVM e registrou um reset no corte de cena. O mesmo FFmpeg da Clicko compôs as faixas editáveis. A máscara ocultou a região central da palavra sobre o tronco e preservou as partes laterais visíveis no quadro de 0,95 s. A versão sem máscara cobre a pessoa com as letras. A inspeção em 4 fps acompanha os estados durante o gesto.

O recorte local levou 13,2 s segundo o recibo do worker. A exportação sem profundidade levou 29,4 s e a versão em profundidade levou 17,0 s, incluindo espera do job e obtenção do arquivo. As duas usam música local. O gasto externo desta rodada foi US$ 0. Os hashes dos arquivos coincidem com os recibos, e a versão em profundidade decodificou 144 frames de seis segundos.

Essa evidência confirma a composição em camadas para a operação testada. Ainda faltam medir aderência temporal ao original, voz, desenho de som, qualidade de bordas em outros materiais e compreensão por espectadores.

## Parecer cinematográfico

**Legibilidade visual, lente Spielberg.** Na referência, a pessoa ocupa uma parcela grande do quadro e continua sendo o foco enquanto a palavra aparece. A operação de oclusão reforça profundidade e preserva a figura. A reprodução mantém essa relação. Reprovar uma variante em que o texto cobre o rosto ou em que a máscara apaga letras fora do corpo. Regra de avaliação inferida a partir da leitura de encenação do perfil do conselho.

**Precisão de quadro, lente Fincher.** Compare referência, fonte limpa e saída no mesmo tamanho de consumo. O controle sobre a região do título precisa aparecer no arquivo final, com registros de posição, duração, máscara e origem. O par sem máscara/com máscara confirma essa decisão na Clicko. As bordas amostradas exigem acompanhamento temporal em mais gestos antes de ampliar o uso. Regra operacional inferida.

**Causalidade, lente Gilligan.** O anúncio anterior saltava da gravação para uma demonstração com muitas explicações. A referência sustenta a ação humana e apresenta a ferramenta dentro de uma progressão. A próxima montagem precisa justificar o momento de mostrar a prova e o efeito dessa prova sobre a promessa. A reprodução da oclusão fornece um recurso de linguagem, com a promessa comercial ainda a formular. Regra operacional inferida.

## Critérios para retomar os anúncios

1. Um brief comercial com produto, público, promessa e prova revisados pelos processos de copy. Campos ausentes ficam registrados.
2. Referência observada com intervalos, quadros e cobertura sonora. Uma tabela liga cada recurso essencial ao material necessário e à operação disponível na Clicko.
3. Uma prova curta de reprodução usando faixas da timeline canônica antes de mudar o roteiro comercial. Registrar os recursos que dependem da filmagem de origem.
4. Direção do modelo por ações, camadas e relações com capacidade real de alterar a sequência. Um relatório compara decisões pedidas e decisões executadas.
5. Aprovação de execução, aderência à referência e avaliação do usuário em registros próprios. Retomar orçamento somente com um problema visual identificado e uma operação capaz de corrigi-lo.

O próximo teste de integração deve colocar a referência visual no contexto do modelo e permitir faixas intercaladas de título, vídeo e máscara. A comparação deve usar a mesma matéria-prima e duração e conservar um controle sem esse contexto. A estrutura fixa de três cenas fica restrita aos experimentos que efetivamente pedem essa forma.

## Artefatos

O script scripts/validation/clicko-reference-reconstruction.cjs cria e acompanha os jobs pelos endpoints da Clicko. O recibo registra a fonte, a preparação e os dois documentos. A entrada limpa foi capturada a 24 fps no player público. Os quadros e vídeos de estudo ficam na pasta local de saída. Os projetos editáveis ficam disponíveis na Clicko.
