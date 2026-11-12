# Laboratório Clicko · montagem aberta · 10/11/2026

Continuação implementada: [direção livre por referência e quatro correções](2026-11-10-clicko-quatro-correcoes.md). Os cortes anteriores continuam reprovados pelo usuário. O novo fluxo separa execução técnica, avaliação do modelo e decisão editorial; a prova desta entrega é local, sem consumo de API.

Este ciclo segue o plano do conselho registrado em [critérios de qualidade](2026-11-07-ad-quality-criteria.md). Mantém qualidade do anúncio como objetivo e separa o gasto de montagem de voz e geração de mídia. Oferta e prova vêm antes da edição. Nenhum resultado deste laboratório mede conversão.

## Briefs e evidência

| Brief | Público, promessa e ação | O que precisa aparecer |
|---|---|---|
| Motion · Da ideia à timeline | Criador de anúncios que precisa organizar cenas. A Clicko permite organizá-las na timeline. CTA autorizado “Abra o Studio de Vídeo”. | Até 3 s, a ideia de cenas soltas precisa estar clara. No meio, as peças precisam convergir visualmente para uma sequência. O CTA precisa fechar a mesma ação. Grafismos são ilustrações, não capturas da interface. |
| Filmagem · Depois do REC | Criador solo que já grava no celular. O editor permite montar o anúncio a partir da gravação. Mesmo CTA autorizado. | O telefone e a ring light identificam a situação real. O recorte precisa conservar a ação e o assunto. A montagem e a copy mostram a próxima etapa sem atribuir fala ou endosso à pessoa filmada. A fonte é [MART PRODUCTION, Pexels 7480852](https://www.pexels.com/video/7480852/). |

Os dois têm 12 s, formato vertical e trilha local. Para cada brief, médio e alto partem do mesmo projeto, material, instrução, trilha, duração e conjunto de operações. Cada versão pode alterar copy dentro dos fatos autorizados, criar grafismos e mudar a montagem. A Clicko valida a proposta, renderiza uma prévia e só aplica o plano aprovado tecnicamente a uma cópia. O controle local mostra a montagem de partida. O contraste entre controle e variantes mistura capacidade do modelo e liberdade editorial. O contraste entre médio e alto isola o nível de esforço nesta rodada.

## Indicadores, critérios e decisões

| Indicador | Como analisar | Critério de avanço |
|---|---|---|
| Gancho e oferta | Inspecionar 0–3 s. Registrar o que imagem e texto prometem e comparar com o restante. | Um problema e uma promessa específica sustentada pelo brief. |
| Prova e progressão | Conferir marcos no meio e no fim. Registrar ação, causa, consequência e intervalo. | No motion, os grafismos mostram a organização. Na filmagem, o telefone permanece reconhecível e o corte ajuda a entender a ação. |
| Copy, legibilidade e CTA | Conferir texto renderizado, contraste, margens e último trecho. | Sem alegação nova. O próximo passo deve ser legível, realizável e coerente com a demonstração. |
| Ritmo e continuidade | Comparar posições do assunto nos cortes. Observar pausas, saltos, redundância e relação da edição com o que se vê. | Ganho editorial localizado em relação ao controle. |
| Som e exportação | Comparar áudio decodificado entre braços, inspecionar duração e revisar o arquivo. | Áudio, formato e duração preservados. A sincronia perceptiva exige escuta. |
| Tempo e custo | Somar preparação, modelo e prévia. Medir exportação separadamente e registrar reservas, cobrança confirmada e tentativas. | Reservar US$ 1,50 por geração, com o mesmo teto. Um retorno incompleto mantém a reserva até conciliação. A fatura depende dos tokens efetivos. |
| Retrabalho | Registrar bloqueios, correção local, versão e achado que motivou a intervenção. | Duas tentativas sem ganho no mesmo problema pedem revisão da estrutura de edição antes de novo gasto. |

Primeiro passam os requisitos de fato, origem, identidade do assunto e integridade da saída. O conselho atribui 0 a 2 aos quatro primeiros indicadores de qualidade e apresenta os tempos que sustentam a avaliação. Um resultado exploratório por nível e brief não estima preferência do público.

## Lentes da revisão

- Legibilidade visual, a partir da lente Spielberg. A pergunta é se o espectador entende o que mudou antes de ler a próxima cartela. A regra operacional é uma inferência a verificar no corte.
- Precisão do gesto, a partir da lente Fincher. Cortar apenas quando o recorte preserva ou esclarece a posição do telefone e o gesto. Um salto que esconde o gesto é contraexemplo. Regra operacional inferida.
- Causalidade, a partir da lente Gilligan. A organização precisa ser consequência da ação mostrada e preparar o CTA. Se as cartelas puderem ser trocadas de ordem sem efeito, o motion não mostrou a relação. Regra operacional inferida.
- Ritmo e som são avaliados como função do corte. A trilha está congelada para isolar a montagem. Assincronias permanecem registradas como lacuna, inclusive quando o áudio decodificado é idêntico.

## Hipótese sobre a estrutura

A proposta é experimentar uma decisão editorial estruturada antes de compilar para o motor da Clicko. Nesta rodada a decisão ainda vira operações do editor atual, agora com liberdade para recortar, reenquadrar, reposicionar, criar grafismos e reescrever. Se continuar faltando continuidade, o próximo teste isola um motor ou formato de montagem diferente com os mesmos briefs, em vez de aumentar esforço do modelo ou trocar a mídia ao mesmo tempo. O primeiro candidato é um grafo de cenas com âncoras de movimento e transições explícitas, convertido para a linha do tempo atual e comparado com os cortes deste laboratório.

## Resultado da rodada · 10/11/2026

| Brief e braço | Gancho / prova / copy e CTA / ritmo | API cobrada | Planejamento e prévia | Exportação |
|---|---|---:|---:|---:|
| Motion local | 1 / 0 / 1 / 0 | US$ 0 | — | 9,6 s |
| Motion médio | 1 / 2 / 2 / 2 | US$ 0,112616 | 55,6 s | 30,0 s |
| Motion alto | 1 / 2 / 0 / 2 | US$ 0,127252 | 71,8 s | 12,9 s |
| Filmagem local | 1 / 1 / 2 / 0 | US$ 0 | — | 20,0 s |
| Filmagem médio | 2 / 1 / 2 / 2 | US$ 0,078092 | 61,0 s | 15,8 s |
| Filmagem alto | 2 / 1 / 2 / 2 | US$ 0,097688 | 65,7 s | 11,6 s |

Os quatro braços pagos reservaram US$ 1,50 cada. Gasto medido por tokens retornados de US$ 0,415648 no total. As duas rejeições de orçamento ocorreram antes da Anthropic. Foram mantidos os limites por geração e ampliada a capacidade mensal local para acomodar reservas de outros testes já existentes. O motion médio inclui 48,3 s da proposta paga bloqueada por encaixe de texto e 7,3 s da reconstrução gratuita. A exportação inclui a espera do job e a leitura do arquivo. Rejeições antes da chamada e reinicialização do ambiente ficam fora da medida. Os projetos de partida de cada brief tiveram o mesmo hash nos três braços. Todos os MP4s medidos têm 12 s e áudio decodificado idêntico. A sincronia perceptiva com música permanece em aberto.

### Parecer cinematográfico

**Legibilidade visual.** No motion local, os elementos ficam parados até o CTA. No médio, os primeiros encaixes já são visíveis em 5–6 s e as três peças estão ordenadas em 8 s. O alto também completa a ação e acentua os pousos, mas o CTA branco sobre amarelo em 8–12 s ficou difícil de ler. O teste de contraste inicialmente leu o fundo do canvas como se fosse o fundo do texto. A comparação conserva o defeito original. A Clicko agora reconhece a tarja compatível com o título e estabiliza a superfície antes de validar o contraste. Reexecutar essa correção é local.

**Precisão do gesto.** Na filmagem, os dois níveis preservam a mão no primeiro plano e cortam para o telefone mais próximo em 3,5 s. Voltam a um plano médio em 7,5 s. O alto escolhe trechos posteriores da fonte, mas a diferença de enquadramento e ritmo é pequena. O médio comunica o ponto em uma linha e mantém o telefone legível. A fonte foi reutilizada do acervo local, com atribuição registrada. A imagem da pessoa no telefone não implica fala ou endosso.

**Causalidade.** Os movimentos das três peças do motion explicam a ordem. Na filmagem, o enquadramento prova que houve gravação. A passagem da gravação para a timeline é comunicada em texto e continua sem demonstração visual. Uma captura curta da Clicko já seria material diferente e deve ser testada em uma rodada própria.

**Decisão.** Esforço médio como padrão para estes dois briefs. Reservar o alto para uma lacuna editorial concreta que o médio não resolve. O caso mais claro de retrabalho foi de compilação e revisão, com um título que estourou a caixa e um fundo mal identificado. A evidência sustenta comparar uma montagem por cenas e âncoras com a saída atual de coordenadas e camadas. Os quatro cortes não comparam renderizadores. A avaliação foi feita em quadros dos renders e em informações dos cortes, sem painel cego de espectadores.

## Rodada seguinte · direção por cenas

Comparamos **Direção por cenas** com o corte médio já exportado de cada brief. Usamos a mesma composição de partida, mídia, duração, áudio e CTA autorizado. O Opus trabalha em esforço alto nas duas passagens desta rodada. A comparação mede o fluxo completo com direção e revisão, junto com a diferença de esforço. A experiência não isola o efeito de cada uma dessas mudanças.

O Opus decide o papel de cada cena, seu peso no tempo total, a copy, o enquadramento e a passagem para a cena seguinte. Para o motion, a Clicko monta a ação das três peças, resolve a composição e estabiliza o CTA. Para a filmagem, o modelo pode escolher trechos reais, aproximar o assunto, preservar o foco entre planos ou pedir uma ilustração vetorial da timeline. A ilustração usa grafismos abstratos. A Clicko traduz essas escolhas para a linha do tempo editável, resolve margens e texto e gera a primeira prévia. O Opus recebe quadros dessa prévia para revisar uma vez. A Clicko valida e exporta o corte escolhido.

Reservamos uma vez US$ 1,50 por vídeo, cobrindo direção e revisão. Cada passagem verifica a estimativa máxima antes de enviar a chamada. O recibo registra o consumo das duas e o teto compartilhado. A exportação é local. O tempo mede a direção, a prévia, a revisão e a exportação. O parecer usa os mesmos quatro indicadores da rodada anterior e associa cada conclusão aos quadros ou aos cortes observados. A preferência do público continua pendente de avaliação cega.

### Resultado · direção por cenas

| Corte | API medida | Direção e prévia | Exportação |
|---|---:|---:|---:|
| Motion · Médio anterior | US$ 0,112616 | 55,6 s | 30,0 s |
| Motion · Direção por cenas | US$ 0,158660 | 108,7 s | 5,3 s |
| Filmagem · Médio anterior | US$ 0,078092 | 61,0 s | 15,8 s |
| Filmagem · Direção por cenas | US$ 0,074664 | 68,2 s | 15,7 s |

Total desta rodada de **US$ 0,233324**. Cada vídeo reservou US$ 1,50 para todas as suas chamadas. A filmagem recebeu duas respostas, direção e revisão. O motion recebeu a direção, uma revisão descartada por formato e uma revisão recuperada em esforço xhigh. As chamadas do motion compartilham o teto original. A duração de planejamento do motion inclui a falha sem cobrança na preparação da recuperação. O ajuste final de abertura acrescentou uma exportação local de 11,1 s e nenhuma chamada. O hash da composição de partida coincidiu por brief. Os MP4s têm 12 s e a mesma faixa de áudio decodificada dos controles.

**Legibilidade visual.** O motion médio já mostrava as três peças chegando às posições em 5–8 s. A nova montagem acrescenta marcas dentro de cada peça, reduz o gancho para 2,4 s e sustenta o CTA em contraste alto a partir de 8,4 s. O Opus apontou que o primeiro render deixava as peças paradas e na ordem final. O compilador agora aceita uma escolha estruturada para a abertura. A cópia local corrigida começa com uma ordem diferente e tem movimento antes dos encaixes. Na filmagem, a revisão retirou um grafismo que cobria o telefone. O CTA final amarelo se destaca a partir de 8,4 s, e o texto intermediário ocupa duas linhas. O controle médio usa uma linha.

**Precisão do gesto.** A filmagem mantém o gesto da mão perto de 1–2 s. O novo corte passa ao detalhe em 3,6 s e abre para o plano geral em 8,4 s. O médio fez a mudança em 3,5 s e 7,5 s. A aproximação preserva a posição do telefone nos quadros observados. O novo corte dá mais respiro ao encerramento, com ganho pequeno no ritmo sobre o controle.

**Causalidade.** No motion revisado, a ordem visível no início difere da final. A promessa é demonstrada pela ação, e o cursor percorre a sequência enquanto o CTA aparece. Na filmagem, o acervo comprova o uso do telefone. A timeline é mencionada pela copy, sem imagem da edição. Um novo plano mostrando a interface em ação seria a hipótese a testar para completar essa prova.

**Decisão do conselho.** Preferir a abertura corrigida por cenas para o motion. Para filmagem, manter o médio como referência de custo e tempo e aproveitar a solução de CTA do novo fluxo. A avaliação se apoia em quadros dos MP4s e no plano editável. As notas abaixo são julgamento editorial exploratório. Compreensão do público e sincronia perceptiva permanecem sem medição.

| Corte | Gancho / prova / copy e CTA / ritmo |
|---|---|
| Motion médio anterior | 1 / 2 / 2 / 2 |
| Motion por cenas, saída inicial | 1 / 2 / 2 / 2 |
| Motion por cenas, abertura corrigida | 2 / 2 / 2 / 2 |
| Filmagem média anterior | 2 / 1 / 2 / 2 |
| Filmagem por cenas | 2 / 1 / 2 / 2 |

O compilador atual cobre o motion de três peças com uma barra e filmagem em uma faixa de vídeo silenciada com três títulos. A rodada mediu execução e revisão nesse escopo. Foram observadas duas falhas na recuperação do motion, uma resposta que não passou pelo formato de revisão e uma tentativa local sem chamada por estado de recibo ainda vazio. A revisão posterior usou resposta estruturada e a exportação foi concluída. As duas falhas permanecem nos recibos.

## Filmagem real com demonstração da Clicko

A comparação mantém a duração de 12 s, a filmagem do celular, a trilha e o CTA do corte médio. A nova montagem adiciona uma captura da Clicko entre a gravação e o fechamento. Essa diferença de material é a intervenção avaliada.

A ação gravada é **Dividir no cursor**. O projeto aberto tinha um clipe de 9 s. A interface mostrou dois clipes depois do comando e o servidor confirmou a revisão salva com os cortes de 3,75 s e 5,25 s. A versão vertical usa um close da faixa real, identifica a gravação da interface e destaca a contagem. A tela está presa à cena de prova, sem recorte automático que possa ocultar a divisão.

Uma única geração compartilha o teto de US$ 1,50 entre direção, revisão da prévia e conferência da prova no render final. A exportação é local. O critério principal do conselho é ver o clipe único virar dois. A avaliação também observa a continuidade do assunto entre celular e timeline, a leitura do CTA e o tempo que o corte dá para entender a demonstração.

### Resultado · demonstração da timeline

| Indicador | Corte médio anterior | Filmagem com timeline real |
|---|---|---|
| API medida | US$ 0,078092 | US$ 0,246384 |
| Planejamento e renders | 76,8 s | 240,0 s |
| Promessa e prova | Filmagem do celular, edição descrita em texto | Gravação do celular, divisão na interface, retorno ao celular |
| Gancho / prova / copy e CTA / ritmo | 2 / 1 / 2 / 2 | 2 / 2 / 2 / 2 |
| Duração | 12 s | 12 s |

Os indicadores seguem os critérios do conselho já registrados acima. As notas são julgamento editorial exploratório com base em quadros e no projeto. A comparação muda a mídia da cena central. O trabalho de capturar a tela e preparar o close fica fora da medida de planejamento e renders. O render inicial levou 16,8 s e a correção local levou 34,7 s, além dos 188,5 s de direção e revisões.

Foram três chamadas de Opus em esforço xhigh na mesma geração. A direção custou US$ 0,077484, a revisão do primeiro render US$ 0,129020 e a conferência de prova US$ 0,039880. O teto compartilhado foi US$ 1,50. A ampliação da interface e a correção do renderizador custaram US$ 0 em API. O limite mensal local foi ajustado para acomodar a nova reserva junto às reservas históricas, com o limite por vídeo em US$ 1,50. O Console da Anthropic conservou sua configuração.

**Legibilidade visual.** A primeira prévia deixava a faixa da timeline fina. O Opus confirmou a operação, mas marcou a leitura em celular como insuficiente. A versão final mantém a visão geral da faixa e acrescenta um close ao redor do cursor. Em 3,6 s a cena entra com um clipe. Perto de 5,1 s a separação aparece na faixa e no detalhe. A contagem de dois clipes fica visível até 9,6 s. O título “Dividir no cursor” identifica a ação, e a composição apresenta a captura como gravação da interface.

**Precisão do gesto.** O comando foi executado na interface sobre um clipe de 9 s. A revisão salva passou de 1 para 2 e contém os intervalos de 90 e 126 frames a 24 fps. O close usa os mesmos quadros da captura, com visão geral em paralelo. Um quadro vazio apareceu na fronteira de volta ao celular na primeira saída. O compilador agora conserva o último frame decodificado durante o intervalo do clipe. A validação final decodificou os 288 frames e não encontrou quadro uniforme. A revisão técnica também passou a amostrar o início e o fim dos clipes.

**Causalidade.** O corte médio dizia para editar na timeline. A nova cena demonstra uma ferramenta dessa montagem e volta ao celular para o CTA. O assunto progride de gravação a edição e à ação seguinte. A troca da filmagem por captura é motivada pela promessa do anúncio. A demonstração cobre divisão de clipe. A leitura dos restantes recursos do editor fica fora dessa prova.

**Decisão do conselho.** Preferir o anúncio com a timeline real para este brief. O ganho está na prova visível da operação. A passagem é um corte seco e a trilha mantém o áudio decodificado do controle. Compreensão do público e sincronia perceptiva continuam pendentes de avaliação. A revisão visual paga do Opus precede a ampliação local da interface. O arquivo final foi conferido em quadros e no estado salvo do projeto, com a gravação original e as versões intermediárias preservadas.

A aplicação automática agora exige confirmação da operação e de sua leitura em celular. Uma prévia reprovada nessa conferência fica bloqueada para correção.

## Reavaliação após o feedback do usuário

O usuário reprovou o anúncio final com a timeline. A recomendação anterior do conselho fica suspensa. As notas registraram presença de prova, legibilidade e estrutura observadas em quadros. A avaliação do usuário sobre a qualidade do anúncio é negativa. Eficácia comercial permanece sem medição. O [diagnóstico de referência](2026-11-10-diagnostico-e-referencia.md) registra as limitações da direção, da montagem e dos critérios de revisão e a prova local de tipografia em profundidade.
