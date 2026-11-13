# Interpretação editorial e hipóteses concorrentes

Tier 1, 13/11/2026. Responsabilidade: Klein, análise de padrões e explicações alternativas. Handoff recebido de [Sackett](01-question.md), [Booth](02-method.md) e [Creswell](03-design.md). Esta análise usa artefatos existentes; não executou nova geração, inferência paga, render ou alteração de produção. Não reabriu os Reels e não ouviu seu áudio. Não representa manifestação dos autores dos vídeos ou de cineastas.

## Interpretação de trabalho

O quadro que melhor acomoda os dados é um **fluxo criativo incompleto, com capacidades de execução parcialmente verificadas**, e não uma causa única já localizada no editor. O híbrido pode ampliar os meios de executar uma cena, mas não fornece automaticamente materiais, decisões editoriais, escuta, revisão competente ou conclusão da tarefa. A conclusão sobre atingir a meta é condicional a essas funções serem demonstradas em conjunto.

Confiança **moderada nessa interpretação**, por concordância entre artefatos, recibo e resultado visual; **baixa quanto à contribuição causal de cada fator**, porque o ensaio independente mudou ambiente, ferramentas, materiais e instruções ao mesmo tempo. Não é possível estimar probabilidade de sucesso ou PPV com estes dados.

### Pistas fortes e anomalias

1. **Mudança de linguagem não equivale a isolamento de causa.** O usuário considerou a ÓRBITA Canvas um primeiro resultado positivo. Ela recebeu apenas copy e ferramentas, escreveu seu próprio renderizador e criou suas imagens procedurais. O ensaio nativo anterior usou planos filmados preparados. O ganho percebido é real como feedback do proprietário; a comparação não determina qual motor tem maior teto de qualidade.
2. **Capacidade, sentido e entrega se separaram.** O renderizador independente produziu imagens com hierarquia e uma metáfora reconhecível de filme contendo mundos; o MP4 recuperado mantém clarão e não tem faixa de áudio. A sessão terminou antes de pedir a exportação. Portanto, uma direção visual promissora coexistiu com falha de conclusão.
3. **Mais mudanças não resolveram automaticamente o ritmo.** `src/timeline.js` contém dez marcos `snaps` entre 4,5 e 7,5 s, além de outras entradas. A peça não sofre simplesmente de ausência numérica de acontecimentos. A questão é o que se reconhece, entende e sente em cada passagem, incluindo a relação ainda não demonstrada com som.
4. **O evento luminoso tem autoria localizável.** `src/orbita.js:671–674` desenha uma cobertura de tela inteira com alpha inicial 0,9 a partir de 8 s. Isso explica a origem desse evento no código Canvas. Não permite concluir que todo clarão anterior veio da mesma causa ou que qualquer brilho intenso é inadequado por definição.
5. **O repertório registrado ainda é candidato.** As três novas fichas declaram `state=knowledge_only` e `localReproduction=not_tested`. A recuperação de uma ficha em consulta demonstra disponibilidade do conteúdo; não demonstra sua aplicação correta pelo diretor em um novo anúncio.

Fontes: [relatório do ensaio independente](../../../plans/2026-11-12-clicko-gargalos-e-orbita-independente.md), [baseline com feedback vinculado ao arquivo](../../knowledge/orbita-quality-baseline.v1.json), [fichas e storyboards](../../knowledge/playbooks/tres-referencias-storyboards-2026-11-12.md), `backend/app/services/studios/craft_research_observations.v1.json`, e fontes locais do ensaio em `C:/Users/edugu/Downloads/clicko-orbita-independent-20261112/src/`.

## A meta tem três componentes visuais diferentes

Reexaminei as folhas válidas `paulo-contact-play.jpg`, `creators-contact.jpg` e `moonsol-contact.jpg`, e `orbita-independente-quadros.jpg`. São quadros esparsos; esta leitura não valida movimento fino, todos os cortes ou sincronismo.

| Exemplar | Relação observável que serve de meta | O que seria uma comparação inadequada |
|---|---|---|
| **@paulo.ia, bola dourada/Olise** | Sujeito e motivo recorrentes, cenários fotográficos, proximidade/distância e relações de primeiro plano/fundo. A identidade e a paleta unem as imagens. | Exigir que uma composição de texto abstrata pareça filmagem real sem fornecer ou produzir cenas equivalentes. A fotografia não prova qual operação/software gerou cada plano. |
| **@creators / @martsromero, matcha** | O copo participa de gestos e contextos reais; a montagem alterna pessoas, corpo, rosto e produto. | Tratar o resultado como catálogo de transições ou usar movimento de cartões no lugar da ação de produto que o briefing precisa demonstrar. |
| **@moonsol.design, colagem** | Retrato, texto e arranjo reconhecíveis; silhuetas dão lugar a objetos no mesmo espaço. O tutorial mostra preparação por componentes. | Medir o ritmo do anúncio pela duração total do tutorial, impor seus 0,5 s a todos os projetos ou considerar qualquer substituição geométrica uma transformação legível. |
| **ÓRBITA positiva** | Planeta e tira de filme vinculam ficção científica a curta; tipografia possui hierarquia e o convite aparece no fechamento. | Descartar o progresso porque ele ainda é ilustração, ou promovê-lo a anúncio pronto sem áudio, revisão completa e exportação autônoma. |

**Reenquadramento útil da meta:** cinema fornece uma referência de materialidade e continuidade; filmagem de produto fornece uma referência de ação e contexto; colagem fornece uma referência de correspondência entre estados e hierarquia. A Clicko deve selecionar e combinar funções pertinentes ao briefing. “Vídeo mais sensorial” precisa virar relações de atenção, movimento e som que possam ser examinadas; não vira uma obrigação de multiplicar cortes.

## Cinco hipóteses concorrentes

Elas podem coexistir. Uma prova deve variar o fator em questão, e não substituir simultaneamente todos os componentes.

| Hipótese | Evidência a favor | Evidência contrária ou insuficiente | Prova discriminante e decisão |
|---|---|---|---|
| **H1 — o motor ou sua integração bloqueia o acabamento essencial.** | O build Craft documenta diferenças de compatibilidade e comportamento; o caminho Clicko já consumiu contexto antes de montar. | As lacunas do catálogo não localizam o defeito desta peça. O caminho nativo já renderizou montagem com planos, efeitos e áudio; o Canvas também introduziu um evento luminoso problemático e terminou incompleto. | Executar a mesma cena determinística e materiais pela Clicko e diretamente no mesmo build; só depois comparar Canvas pela mesma especificação visual. Falha exclusiva da Clicko dirige correção da integração; falha nativa reproduzida justifica fallback por operação. |
| **H2 — materiais e preparação não sustentam a linguagem desejada.** | As referências fotográficas contêm pessoas, objetos, ambientes, textura e luz. O ensaio independente recebeu copy e criou mundos por desenho procedural. | Um anúncio gráfico pode ser excelente com formas, texto e som; material fotográfico não é requisito universal. Não houve ensaio isolando o pacote de materiais. | Manter plano e executor; trocar apenas materiais atuais por um pacote preparado para os estados previstos. Se só a aparência melhora, registrar isso sem atribuir ganho de sentido. Se a ação necessária passa a existir, priorizar preparação/aquisição. |
| **H3 — a direção não converte suficientemente copy em progressão e hierarquia.** | A categoria completa entra depois de cerca de 10 s em uma peça de 16 s. Muitas trocas mostram variedades de mundo dentro de um dispositivo visual semelhante. | A metáfora “mundos cabem em filme” aproxima a imagem da promessa e recebeu feedback positivo. Revelação tardia pode ser deliberada e adequada; não há prova de incompreensão de espectadores. | Com a mesma mídia e execução, comparar apenas duas organizações editoriais justificadas. Pedir descrição espontânea da oferta antes da preferência e localizar o que cada passagem acrescenta. Corrigir ordem, legibilidade ou exposição da categoria quando o resultado pedir; não presumir uma cadência correta universal. |
| **H4 — a revisão disponível não fecha o ciclo audiovisual.** | O MP4 recuperado não contém áudio; o clarão amplo permanece; a cobertura das referências é visual e amostrada. | Existe revisão local por quadros e medidas de áudio no sistema. Não foram examinadas aqui todas as decisões internas do modelo; sobrevivência de um efeito não prova que ele não foi visto. | Usar pares locais corretos/defeituosos com colisão, pico luminoso, consequência omitida e áudio ausente/desalinhado. Medir detecção e falso positivo por tipo. Separar medição de sinal de escuta e julgamento editorial; calibrar com revisão humana quando o recurso perceptivo não estiver disponível. |
| **H5 — recursos, conclusão e aprendizado não estão organizados para reutilização.** | O Opus gastou a sessão construindo infraestrutura, encontrou erros de comandos longos/aspas, não produziu áudio nem chamou exportação. Fichas recuperáveis ainda não têm reprodução local validada. | A Clicko já tem rascunho, retomada e exportação testados; autonomia não precisa de uma nova equipe para cada tarefa. O ensaio independente não usou essa infraestrutura, por desenho. | Primeiro provar retomada e exportação com resposta simulada/motor real; depois uma sessão do diretor sobre runtime e mídia prontos, com custo/tempo restantes visíveis. Registrar lição com exemplo, contraexemplo e caso novo; só chamar transferência quando a escolha e a execução ocorrerem sem fornecer a resposta do caso. |

**Causas confirmadas de resultados específicos:** a codificação explícita do pico de luz; ausência de áudio no arquivo; encerramento por orçamento antes da exportação; diferença de insumos entre os ensaios. **Mecanismos plausíveis ainda por isolar:** contribuição da falta de materiais, efeito da política editorial/revisão, e limites de fidelidade do Craft na operação que o anúncio realmente exige.

### Evidência adicional recebida do coordenador

Depois da análise acima, o coordenador forneceu uma prova local de repetibilidade e alfa, registrada em `.codex-runtime/clicko-dev/motion-quality-probe/result.json`. Li o recibo; não executei essa prova. O teste preservou o fonte, amostrou oito solicitações de quadro em 4,26 s, reproduziu hashes idênticos ao pedir 3,4 s e 8 s fora de ordem e obteve o mesmo quadro de 3,4 s em uma página nova. As amostras tiveram alfa mínimo e máximo 255. Isso sustenta **reutilizar o renderizador existente para cenas completas nessas condições amostradas**; não o qualifica ainda como camada transparente, não valida movimento integral e não estabelece paridade com o Craft.

O coordenador também informou que os hashes das três novas folhas de referência não constam no `LibraryAsset` consultado, enquanto `consult_repertoire` devolve fichas JSON com descrições e filenames. Esse achado localiza uma lacuna na ponte entre a referência escolhida e os pixels efetivamente disponíveis por esse caminho. Não prova ausência de qualquer imagem equivalente em todas as sessões. A próxima prova deve registrar o material visual fornecido, a consulta feita pelo diretor e a revisão que o usou, em vez de tomar o título da ficha como confirmação de que o modelo viu o exemplo.

Por fim, a inspeção de backend do coordenador identificou `composition.link` já ligando EffectCraft a FilmCraft com VP9/alfa e dependências. Canvas ainda não entra nesse elo. O plano deve estender uma ligação existente quando adequado; não pressupor que toda a montagem/som precisa ser reconstruída. Os contratos de alfa e tempo-base continuam essenciais: a saída opaca demonstrada pode ser correta para um plano completo e inadequada para um overlay.

## O que manter

- O baseline positivo por hash e o feedback do proprietário; ele é uma referência interna útil, ainda em revisão.
- A relação entre filme, mundos e a promessa, como direção candidata a refinar; sua preferência detalhada deve ser calibrada, sem atribuir ao usuário aprovação de cada elemento isolado.
- A copy aprovada, fontes e projeto editável; comparar alterações locais sem recomeçar todo o filme.
- Liberdade do Opus para duração, cenas, camadas e efeitos, com evidências que permitam discutir o resultado.
- Componentes já comprovados de persistência, inspeção e exportação; uma arquitetura híbrida deve conservá-los.
- Separação entre procedimento conhecido, execução reproduzida, julgamento editorial e validação com espectadores.

## Seis fases propostas e condições para avançar

| Fase | Entrega prática | Condição de avanço |
|---|---|---|
| **1. Calibrar a meta e preservar o ponto de partida.** | Uma ficha por dimensão das referências, mais comentário do proprietário sobre o que conservar na ÓRBITA. | Meta de cada trecho compreensível, distinção entre função visual e gosto, arquivo original preservado. Não exigir um software ou estilo universal. |
| **2. Preparar cenas e materiais.** | Copy ligada a objeto, evento, consequência, foco e material; quadros de estilo e plano de som. | A ação ou transformação necessária pode ser construída com os materiais disponíveis; lacunas ficam explícitas antes da montagem. |
| **3. Discriminar execução e revisão.** | Provas locais P0-A/P0-B/P0-C de Creswell, com pares corretos/defeituosos e contratos equivalentes. | Localização da falha em integração, motor ou avaliação, sem declarar superioridade estética por semelhança de pixels. O caso correto deve continuar aceito. |
| **4. Integrar somente o caminho necessário.** | Runtime preparado de cenas com fontes preservados; eventual adaptador Canvas/Craft, montagem e som com tempo-base, cor e alfa conferidos. | Uma cena passa de fonte a saída editável e entra na montagem sem perda de identidade, duração, posição de áudio ou retomada. Se o Craft já resolver a prova, evitar complexidade adicional. |
| **5. Concluir uma ÓRBITA comparável.** | Refinar a direção positiva, produzir a faixa sonora e revisar o MP4; depois, quando autorizado, testar o Opus sobre o pacote pronto. | Resultado sem defeito essencial definido, oferta e convite legíveis/compreensíveis, escuta registrada e pedido de exportação rastreável. Recuperação humana permanece identificada. |
| **6. Transferir e conservar o aprendizado.** | Reaplicar o princípio a um briefing compatível e testar um caso em que ele não cabe; manter controles de regressão. | O sistema seleciona/adapta e também recusa a técnica adequadamente, preservando os dados do novo produto. Somente então ampliar repertório ou delegação. |

Os controles de duração, mídia e tentativas pertencem às comparações, não a uma restrição editorial definitiva. Não é preciso alongar uma peça apenas para alcançar 30–45 s, nem encurtá-la para caber no baseline: a nova duração precisa de conteúdo e leitura que a justifiquem.

## Simulação prospectiva e premortem

**Cenário:** o híbrido foi integrado e, mesmo assim, os próximos anúncios continuam fracos. Probabilidades não são estimáveis aqui; impactos e sinais são qualitativos.

| Falha imaginada | Sinal precoce | Impacto e proteção do plano |
|---|---|---|
| A equipe otimizou um renderizador, mas continuou sem cenas adequadas. | Novos mundos genéricos e operações sem relação com a promessa, apesar de exportar sem erro. | Impacto editorial alto. Preparar e avaliar os materiais e as relações do storyboard antes de consumir uma sessão longa. |
| “Aprender” continuou significando armazenar documentos. | A ficha aparece no contexto, mas a decisão não muda ou a mesma regra é aplicada a um caso incompatível. | Transferência falha. Ligar cada lição a exemplo, contraexemplo e prova posterior inédita. |
| O roteador acrescentou perdas e tempo. | Saltos de cor, fontes trocadas, alfa errado, som deslocado ou reparos manuais em toda emenda. | Acabamento e autonomia caem. Um contrato de saída por cena e uma prova simples de intercâmbio antecedem a generalização. |
| Os avaliadores recompensaram acabamento superficial. | Nota alta com oferta ausente, erro de texto, transformação falsa ou faixa sem escuta. | Falsa promoção de qualidade. Separar execução, sentido e percepção; não compensar falha essencial por uma média. |
| A sessão novamente esgotou recursos antes de concluir. | Reescrita de infraestrutura, repetição de inspeções e material sonoro deixado para o final. | Entrega incompleta. Reutilizar o runtime, expor estado e recursos, preservar o rascunho e testar a cadeia até a exportação. |

## Alternativas e gatilhos de decisão

- **Craft permanece suficiente nas provas essenciais:** conservar o caminho nativo e investir em preparação, direção e revisão. O híbrido não é obrigatório por princípio.
- **Uma operação específica falha no Craft e passa em Canvas:** usar fallback delimitado, preservando os fontes e as condições de reprodução. Não substituir o editor inteiro a partir de um caso.
- **O intercâmbio híbrido prejudica mais do que ajuda:** considerar um executor dominante para a peça e usar o outro apenas onde exista ganho comprovado; comparar custo, tempo e acabamento antes de ampliar a arquitetura.
- **A operação essencial não passa em nenhum dos caminhos:** documentar a necessidade exata e avaliar uma ferramenta especializada ou revisão da proposta visual. Essa decisão depende de prova, condições técnicas e custo próprios; não pressupõe retorno a HyperFrames/MCP ou aquisição imediata de outro editor.

## Handoff e limites

Para Forsgren: localizar no fluxo real as capacidades e lacunas que correspondem a H1/H4/H5. Para Higgins: completar procedência/cobertura e distinguir ação de produção observada de reconstrução proposta. Para Gilad: confrontar os gatilhos de decisão com custo de integração e alternativas. Para Ioannidis/Kahneman: auditar a inferência multicausal, o viés de atribuir qualidade ao editor e o risco de promover o primeiro avanço como domínio geral.

Esta é uma interpretação apoiada por artefatos e hipóteses discriminantes. Não certifica equivalência aos criadores, eficácia comercial, qualidade sonora ou capacidade de editar qualquer gênero. Não contém pesquisa web nova, pontuação estética populacional ou probabilidade inventada.
