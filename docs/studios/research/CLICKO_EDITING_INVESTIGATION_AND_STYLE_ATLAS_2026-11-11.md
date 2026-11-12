# Clicko · investigação da edição e catálogo de linguagens

Atualização de implementação em 12/11/2026: os achados abaixo descrevem o estado investigado em 11/11. Consulte as [correções e provas locais](../../plans/2026-11-12-clicko-correcoes-do-aprendizado-editorial.md) para o estado posterior. O diagnóstico histórico foi preservado.

Pesquisa de 11 de novembro de 2026. A entrega registra fontes, decisões editoriais e diagnóstico do fluxo existente. O trabalho desta rodada usou leitura do sistema, pesquisa pública e análise dos recibos. Gasto com a API cadastrada de Claude/OpenRouter nesta rodada foi US$ 0. As propostas de experimentos abaixo estão por executar.

O problema mais sustentado pela investigação é a transferência incompleta entre conhecimento, contexto do editor, execução e avaliação. Há estudos antigos detalhados que o caminho nativo atual deixa de consultar. Os especialistas recebem menos recursos de descoberta e correção que o diretor. A revisão do modelo usa principalmente quadros estáticos. Esses fatos explicam limitações concretas do processo. A contribuição de cada um para o acabamento da ÓRBITA ainda precisa ser isolada.

**As três referências recuperadas do sistema**

O cadastro da área de copy contém @creators, @paulo.ia e @moonsol.design. Esses perfis têm linguagens variadas. @creators também publica trabalhos de outros autores, cujos créditos precisam acompanhar cada exemplar. A escolha editorial deve considerar o vídeo específico e seu propósito. [Cadastro no sistema](../../../backend/app/services/studios/ad_copy_workflow.py:16)

As análises anteriores estão distribuídas pelo [estudo dos perfis](clicko-video-studio-2026-09-05/ANALISE-INSTAGRAM.md), pelos [procedimentos dos tutoriais](INSTAGRAM_TUTORIAL_WORKFLOWS_2026-09-30.md), pelo [modelo de conhecimento](INSTAGRAM_EDITING_KNOWLEDGE_MODEL_2026-09-30.md), pelo [corpus de Reels](../knowledge/motion-research/corpus-reels.v1.json) e pelas [análises por vídeo](../knowledge/corpus/). O modelo de conhecimento de setembro identifica expressamente fichas de pesquisa ainda sem ingestão. Portanto já havia uma descrição desse elo a construir.

A reabertura de uma publicação por perfil nesta rodada confirmou os créditos e as declarações dos autores. @creators e @ruama explicam uma composição com recorte automático, sobreposição e keyframes no Edits. @moonsol.design identifica InVideo no tutorial de transformação de desenho em comida. A publicação de @paulo.ia sobre uma chamada da TV Globo credita criação, roteiro, direção de IA, edição/composição e trilha a profissionais diferentes. Essas declarações documentam preparação e responsabilidades. A qualidade final ainda exige examinar o resultado. [Texto em profundidade](https://www.instagram.com/creators/reel/DdwS-6oRvL8/) · [Desenho e produto](https://www.instagram.com/moonsol.design/reel/Dd3k4cBtFrK/) · [Processo e créditos da chamada](https://www.instagram.com/paulo.ia/reel/DdZ6dY-M12g/)

**O processo publicado pelo Matheus**

A página pública do Matheus apresenta quatro etapas. Organiza gravações, referências e exportações. Prepara e testa HyperFrames, FFmpeg, Whisper e yt-dlp. Usa de três a cinco vídeos para construir um guia editorial persistente. Depois pede um storyboard com fala, imagem e duração, recebe alterações e só então finaliza. As correções também atualizam o guia. Essa sequência foi lida diretamente na página nesta rodada. [Procedimento do Matheus](https://matheusgobbi.com/edit)

O Reel indicado tem 60,115 s. Foram acessados os tempos 1, 18, 39 e 57 s, com pixels diferentes confirmados no player. A cobertura disponível nesta investigação não estabelece uma transcrição integral da fala, audição técnica ou todas as operações mostradas. O procedimento acima se apoia na página escrita do autor. A legenda do Reel anuncia o tutorial. [Reel indicado](https://www.instagram.com/p/DflIbFny1zw/)

O ponto a transferir para a Clicko é a ligação persistente entre exemplos concretos, decisões de montagem e correções do usuário. A escolha de ferramenta deve ser avaliada pelo comportamento que ela consegue executar. O estudo do Matheus parte de gravação disponível e de um gosto explicitado. A ÓRBITA exigiu também criar as cenas a partir da copy, com apenas uma faixa WAV no índice inicial de materiais. Essa diferença de tarefa impede comparar diretamente os resultados como se a única variável fosse o modelo.

Na documentação da Anthropic, Claude Code combina modelo, ferramentas, acesso a arquivos e gestão de contexto. Suas sessões podem recuperar instruções e memória persistente. A interface de IDE é uma das formas de acessar esse ambiente. Isso permite que a qualidade dependa do conjunto efetivamente disponível ao agente. [Funcionamento do Claude Code](https://code.claude.com/docs/en/how-claude-code-works)

**Catálogo inicial com um exemplar por família**

Cada linha abaixo registra uma linguagem principal e seu mecanismo. Um anúncio pode combinar famílias, preservando a função de cada trecho. O catálogo é expansível para novos gêneros, públicos e materiais. A demonstração de competência exige transferir a técnica para um briefing diferente do exemplar.

Os estados de evidência têm alcance definido. **V** corresponde a quadros observados no acervo anterior, com cobertura audiovisual parcial. **M** corresponde a análise assistida por máquina com revisão humana pendente. **D** corresponde a procedimento ou declaração primária, com decupagem audiovisual pendente. As condições de escolha e contraindicações são inferências editoriais propostas para a Clicko.

| Família e exemplar principal | Como a montagem funciona | Quando escolher e material necessário | Sinal de escolha inadequada | Cobertura |
|---|---|---|---|---|
| Fala direta com prova · [@paulo.ia, ChatGPT Work](https://www.instagram.com/paulo.ia/reel/Dd2EAaIBeRg/) | A pessoa sustenta a explicação e a interface entra quando a afirmação pede demonstração. O retorno à pessoa conserva o contexto. | Software, serviço ou funcionalidade com fala utilizável e captura da operação real. | A fala promete uma ação e a tela mostra cartões decorativos ou resultado diferente. | V, amostras dentro de aproximadamente 0–31 s de 91 s. |
| Conversa com exemplos · [@creators / @jdiasss_, Papo de Criador](https://www.instagram.com/creators/reel/Dc6O2ryRBP9/) | Pergunta, exemplo e retorno à reação fazem a informação avançar. | Didática, bastidores e autoridade compartilhada, com conversa, exemplos e áudio sincronizado. | Cortar a pausa ou a reação remove a intenção da resposta. | V, 0,9; 5,5; 7,6; 25,1; 26,3; 48,3 s. |
| Tutorial de interface · [@creators, composição de aniversário](https://www.instagram.com/creators/reel/DcMFvawPPIl/) | Seleciona gestos que alteram o resultado e mantém reconhecível o espaço de trabalho. | Ensinar uma operação, com captura ou mãos/aparelho, estado inicial e resultado. | O controle fica ilegível ou o resultado aparece sem a ação correspondente. | V, amostras dentro de 5–11 e 30–35 s, além de 39,7 e 46,7 s. |
| Processo físico e bastidores · [Junk journaling](https://www.instagram.com/reel/DdtuxMNBtxr/), crédito a @natashahmedx no corpus | Materiais, gesto, artefato e uso mostram como o trabalho acontece. | Artesanato, fabricação ou serviço, com processo captado e detalhes correspondentes. | O insert de arquivo mostra outra tarefa, objeto ou etapa. | V, 0,35; 11,11; 25,39; 43,64; 62,68; 74,59 s. Autoria da edição não determinada. |
| Produto sensorial filmado · [Daniel Schiffer, comercial de café](https://www.youtube.com/watch?v=3ojDeNPP8SM) | Exemplar candidato para organizar planos pelo que revelam de textura, manipulação e desejo. | Produto físico ou alimento com captação próxima, luz e interação utilizável. | A montagem pede macro, líquido ou contato e os brutos disponíveis só mostram fotografias gerais. | D, título e autoria localizados. Procedimento e tempos por decupar. |
| Motion argumentativo · [@mep.io_, Distribution](https://www.instagram.com/reels/DciIBRYBHBK/) | Tese, problema, exemplos, sistema e convite recebem composições com funções diferentes. | Explicação de uma ideia, com copy argumentada, voz, provas e design coerente. | As palavras e cards se movem sem acompanhar uma mudança no argumento. | M, janelas registradas 0–9; 9–28; 28–49; 49–69; 69–87 s. |
| Tipografia cinética · [NeverStillFX](https://www.youtube.com/shorts/bYWZ-kn839M) | A escala e a ocupação do quadro alteram prioridade e dão consequência à palavra. | Slogan, frase curta, lançamento ou ênfase verbal, com fonte e medidas reais dos glifos. | A palavra perde leitura ou tudo se movimenta com a mesma intensidade. | V, somente 2,1 e 7 s. Curvas e sincronismo por verificar. |
| Motion de marca e manifesto · [Ordinary Folk, School of Motion](https://www.ordinaryfolk.co/project/school-of-motion-manifesto) | O processo documentado faz formas simples ganharem complexidade e dimensão para expressar a missão. | Identidade, apresentação ou manifesto, com conceito e sistema visual que tenham relação com a marca. | A abstração poderia receber qualquer marca sem mudar o sentido. | D, processo e créditos primários. O estudo anterior amostrou 4,85 e 28,82 s. |
| Colagem editorial · [@moonsol.design, animated dot stickers](https://www.instagram.com/moonsol.design/reel/DdwecRoI4Bf/) | Fotografias, recortes e conectores pertencem a uma mesma superfície e hierarquia. | Portfólio, coleção ou história com arquivos e textura coerente. | As fotos só se acumulam e nenhuma relação ou informação fica mais clara. | V, observação de composição. O estudo descreve fotos, madeira, título e InShot. Comportamento temporal por verificar. |
| Transformação VFX localizada · [@moonsol.design, doodle to food](https://www.instagram.com/moonsol.design/reel/Dd3k4cBtFrK/) | O estado preparado do cenário muda para revelar o produto com posição e perspectiva correspondentes. | Produto ou benefício que ganha sentido por uma transformação, com placa limpa e fonte alinhada. | O objeto desliza, a sombra muda sem motivo ou a revelação acontece antes do gesto. | V/D, preparação observada por volta de 20 s no estudo anterior. Página primária identifica InVideo. Traço intermediário por verificar. |
| Documentário curto de marca · [@creators / Kayra Theodore](https://www.instagram.com/creators/reel/DcRcZzhPGYV/) | Presente, arquivo, processo e obra estabelecem origem e significado. | História real, trajetória ou bastidor, com arquivo ligado à pessoa e ao projeto. | Imagens genéricas substituem a evidência que sustenta a história. | V, 5,7; 11,5; 22,1; 44 s. Voz e som sem auditoria. |
| Montagem pessoal e vlog · [@creators / Alex Cisse](https://www.instagram.com/creators/reel/Dc3qMrJxJcp/) | Ambientes, distâncias e retorno ao presente organizam uma experiência. | Relato pessoal ou lembrança, com brutos relacionados e percurso reconhecível. | A seleção de planos bonitos rompe a geografia ou a cronologia necessária. | V, 0,8; 6,6; 22,7; 32,2 s. Sincronismo musical por verificar. |
| Micro-história de humor · [@creators, ocupado/chamada](https://www.instagram.com/creators/reel/Dcl3b2LR6NC/) | Preparação, informação que muda a situação e reação sustentam o payoff. | Identificação cotidiana e oferta relacionada ao conflito, com performance e reação disponíveis. | A piada exige explicação adicional ou o corte elimina a pausa que a torna compreensível. | V, 0; 3,5; 5,1; 9 s, de 10,73 s. |
| Entrevista longa em capítulos · [Colin & Samir com Emma Chamberlain](https://www.colinandsamir.com/resources/an-honest-conversation-with-emma-chamberlain) | Exemplar candidato para preservar pergunta, resposta e progressão temática; o corte curto conserva contexto. | Conversa longa, transcrição e áudio sincronizado, com câmeras e reações quando disponíveis. | A seleção de frases muda o argumento ou a intenção do entrevistado. | D, capítulos oficiais. Cortes, planos e som por observar. |
| Narrativa com mídia generativa · [@paulo.ia, processo de chamada para TV](https://www.instagram.com/paulo.ia/reel/DdZ6dY-M12g/) | A fonte documenta etapas e responsabilidades de criação, roteiro, geração, composição e áudio. A continuidade deve ser planejada antes de unir planos gerados. | Briefing que pede situações de difícil captação, com direção de arte, referências de identidade e material suficiente para cada plano. | Cada cena reinventa pessoa, produto, luz e mundo, prejudicando a mensagem. | D, legenda e créditos relidos nesta rodada; a fidelidade entre planos requer análise temporal. |

A tipografia atrás de uma pessoa é uma técnica transversal de profundidade. A ordem é fundo, texto e recorte do sujeito, seguida de animação com o corpo preservado. Cabe quando o texto precisa pertencer à cena e continua legível. Quando a palavra indispensável fica escondida, a composição perde sua função. Esse procedimento pode servir às famílias de fala, tutorial, produto ou identidade. [Exemplar de @creators e @ruama](https://www.instagram.com/creators/reel/DdwS-6oRvL8/)

Os registros locais permitem conferir a origem da cobertura de cada exemplar.

| Exemplar ou família | Registro da observação |
|---|---|
| Fala direta com prova · ChatGPT Work | [Expansão do diário visual](INSTAGRAM_EDITING_VIEWING_LOG_EXPANSION_2026-09-30.md) |
| Conversa · Papo de Criador | [Análise dos perfis, seção 3](clicko-video-studio-2026-09-05/ANALISE-INSTAGRAM.md) |
| Tutorial · aniversário | [Análise dos perfis, seção 3.1](clicko-video-studio-2026-09-05/ANALISE-INSTAGRAM.md) |
| Processo físico · journaling | [Corpus com tempos e atribuição](../knowledge/motion-research/corpus-reels.v1.json) |
| Produto · comercial de café | A fonte primária está vinculada na linha do catálogo. Decupagem pendente. |
| Motion argumentativo · Distribution | [Análise assistida por máquina](../knowledge/corpus/instagram-DciIBRYBHBK/analysis.md) |
| Tipografia cinética · NeverStillFX | [Cobertura S1 do repertório](../../../docs/plans/2026-11-11-orbita-repertorio-paralelo.md) |
| Manifesto · Ordinary Folk | [Cobertura Y2 do repertório](../../../docs/plans/2026-11-11-orbita-repertorio-paralelo.md) e página primária vinculada no catálogo. |
| Colagem · stickers | [Procedimento 6](INSTAGRAM_TUTORIAL_WORKFLOWS_2026-09-30.md) |
| VFX · desenho e comida | [Procedimento 3](INSTAGRAM_TUTORIAL_WORKFLOWS_2026-09-30.md) |
| Documentário · Kayra | [Análise dos perfis, seção 3](clicko-video-studio-2026-09-05/ANALISE-INSTAGRAM.md) |
| Vlog · Alex Cisse | [Análise dos perfis, seção 3](clicko-video-studio-2026-09-05/ANALISE-INSTAGRAM.md) |
| Humor · ocupado/chamada | [Análise dos perfis, seção 3](clicko-video-studio-2026-09-05/ANALISE-INSTAGRAM.md) |
| Entrevista · Colin & Samir | A página primária com capítulos está vinculada no catálogo. Decupagem pendente. |
| Narrativa generativa · chamada de TV | Declaração e créditos relidos na publicação primária vinculada no catálogo. |

**Como decidir a linguagem por projeto**

O editor começa pela tarefa do espectador. Aprender a clicar pede uma operação legível. Acreditar numa afirmação pede prova. Entender uma ideia pede relações que a imagem consiga representar. Sentir textura pede material capaz de mostrá-la. Acompanhar uma história pede progressão, ponto de vista e contexto. Reconhecer uma identidade pede um sistema visual relacionado à marca.

Em seguida, confere o que o cliente forneceu. Rosto e logo identificam pessoa e marca. Benefício, oferta e evidência vêm do dossiê do produto. Brutos, captura de tela, transcrição, imagens, fontes, cores, áudio e exemplos aprovados determinam quais realizações estão disponíveis. O editor deve explicitar uma falta relevante antes de substituir prova por ilustração.

Cada escolha deixa um registro curto com objetivo, exemplar, elemento a adaptar, material usado, efeito perceptivo esperado, alternativa e motivo para abandoná-la. No resultado, a revisão compara a expectativa com o que apareceu no quadro e no som. A decisão continua aberta à direção criativa. O catálogo serve de repertório consultável.

**O que o backend e os recibos demonstram**

| Evidência no caminho atual | Consequência possível | Estado da conclusão |
|---|---|---|
| Dois arquivos locais carregam 17 fichas. O índice anuncia 12 e omite show-action, protect-interface, readable-type, honest-audio e cutout-depth. O repertório amplo com busca híbrida fica em outro fluxo. | Uma análise guardada pode deixar de participar da decisão atual. | Separação de caminhos confirmada. Impacto editorial a medir. [Carregamento e índice](../../../backend/app/services/studios/craft_direction.py:20) · [Repertório amplo](../../../backend/app/services/studios/editing_repertoire.py:803) |
| A consulta exclui o campo operations de duas fichas legadas. Os sete operationRecipe novos continuam disponíveis. | A descrição de uma finalidade pode chegar sem seu procedimento antigo. | Alcance confirmado e limitado a esse campo. [Consulta](../../../backend/app/services/studios/craft_direction.py:41) |
| Os três perfis têm orientações breves na área de copy. O editor recebe o dossiê preenchido, sem carregamento automático de um guia produzido das análises dos perfis. | O nome da referência pode chegar sem as decisões que produzem seu efeito. | Caminho lido confirmado. [Perfis](../../../backend/app/services/studios/ad_copy_workflow.py:16) · [Contexto do editor](../../../backend/app/services/studios/craft_agent.py:598) |
| As prévias do Opus são folhas de até seis momentos. A inspeção de fonte também usa stills e metadados. A leitura de fala depende de transcrição pronta. | Cadência, curvas, articulação da fala e sincronismo podem escapar da revisão. | Forma de observação confirmada. Capacidade de detectar cada defeito a medir. [Prévias](../../../backend/app/services/studios/craft_agent.py:80) · [Fontes](../../../backend/app/services/studios/craft_agent.py:243) |
| Cada tarefa delegada recebe resumo, primer e uma ferramenta de contribuição, com um turno e 6.000 tokens de saída. | O especialista pode adivinhar uma operação incompatível e terminar antes de corrigi-la. | Restrição confirmada. O erro de opacidade com keyframes ocorreu no recibo. [Execução delegada](../../../backend/app/services/studios/craft_swarm.py:193) |
| A memória recupera evidências técnicas e comentários por documento. Um comentário preservado ainda exige interpretação para virar uma regra útil a outro briefing. | A mesma falha pode reaparecer em outro projeto sem uma preferência editorial aplicável. | Mecanismo confirmado. Transferência de gosto ainda sem prova. [Memória e feedback](../../../backend/app/services/studios/craft_learning.py:35) |
| A pesquisa de material do editor retorna fontes já cadastradas. A ÓRBITA começou com uma faixa WAV no catálogo. | O modelo precisa criar a arte ou prosseguir com um conjunto pobre de materiais. | Catálogo e âmbito da busca confirmados. [Fontes](../../../backend/app/services/studios/craft_direction.py:50) |
| EffectCraft e FilmCraft são reimplementações independentes dos aplicativos da Adobe. O projeto documenta lacunas de compatibilidade de scripting. | Um script conhecido de After Effects pode precisar de adaptação e verificação no EffectCraft. | Origem e lacunas documentadas. A hipótese de insuficiência visual do motor precisa de teste. [EffectCraft](../../../third_party/craft/effectcraft/README.md:14) · [FilmCraft](../../../third_party/craft/filmcraft/README.md:14) · [Paridade de scripting](../../../third_party/craft/effectcraft/docs/scripting-parity.md:11) |

Os Crafts têm código próprio da organização Storytold, conforme o arquivo de origem. A compatibilidade com o aplicativo da Adobe deve ser conferida por operação. O registro da origem e a documentação de recursos delimitam o ambiente. A qualidade comparada dos motores permanece por medir. [Origens dos motores](../../../workers/craft/sources.lock.json)

O recibo da ÓRBITA registra 81 turnos do Opus, 21 inspeções, 16 prévias por sequência e nove compactações. Sete prévias ocorreram no lote 18 e cinco no lote 19. A gravação de 539.599 tokens no cache corresponde a US$ 2,697995 dos US$ 4,9449489 medidos. Cinco entregas iniciais do Sonnet terminaram sem contribuição executável. O registro localiza atrito e desperdício. A causa específica de cada escolha estética permanece aberta. [Recibo do ensaio](<C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-swarm-2026-11-11/recibo.json>)

**Como desenvolver e comprovar domínio editorial**

O processo de aprendizado proposto reúne uma biblioteca de exemplares, procedimentos executáveis, preferências revisadas e resultados em tarefas novas. Na integração atual, a persistência ocorre no armazenamento da aplicação e na informação recuperada para a sessão. A documentação da Anthropic descreve memória como dados que a aplicação guarda e devolve ao agente. Guardar essas informações requer uma etapa explícita de recuperação para que elas participem de outra decisão. [Memória na API](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)

Uma ficha de aprendizado precisa registrar situação, objetivo, fonte e cobertura, material necessário, estado inicial, ação, estado final, operações verificadas no motor, falha provável, correção observada e condição de reutilização. A preferência pessoal também precisa de escopo. Uma correção de uma assinatura da ÓRBITA pode valer para essa marca. Sua aplicação a uma entrevista exige outra justificativa.

O aprendizado pode seguir estas etapas futuras, preservando a liberdade editorial do diretor.

1. Recuperar o conhecimento já existente e acompanhar exatamente o que chega à sessão. Uma ficha útil precisa aparecer entre as referências que o editor consegue consultar.
2. Descrever a gramática de um exemplar, com ações e consequências, timing, camadas e som observado. Identificar separadamente o que foi inferido e o que falta verificar.
3. Demonstrar a operação no motor com materiais equivalentes e saída editável. Conferir se um efeito, curva ou máscara realmente se comporta como previsto.
4. Rever o storyboard e uma prévia de ritmo para calibrar o gosto. No processo do Matheus, o usuário participa dessa etapa. Esse componente humano precisa aparecer na comparação de autonomia e tempo.
5. Traduzir uma correção em instrução reutilizável com exemplo e contraexemplo. Recuperá-la em outro projeto e observar se muda a decisão.
6. Avaliar briefing, ação, continuidade, design, texto, som e compreensão, com evidência do resultado. Tempo, chamadas e gasto acompanham o veredito de qualidade.

Essas etapas são uma proposta de desenvolvimento. A literatura de agentes recomenda contexto relevante e exemplos recuperáveis, enquanto a avaliação precisa comparar o resultado produzido com o objetivo. Isso apoia o desenho da investigação e ainda exige validação específica em edição. [Contexto para agentes](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) · [Avaliação de agentes](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)

**Experimentos que distinguiriam as causas**

| Pergunta | Comparação futura | Evidência que mudaria o diagnóstico |
|---|---|---|
| O repertório está chegando? | Mesmo briefing, materiais e modelo, registrando a recuperação atual e a consulta do exemplar completo. | A técnica relevante chega e é aplicada, ou chega e continua sendo ignorada. |
| O especialista falha por falta de contrato? | Mesma tarefa pequena, com contexto atual e com esquema/exemplo nativo verificado. | A operação deixa de falhar com o contrato disponível, ou permanece inadequada. |
| A revisão percebe o movimento? | Defeitos conhecidos dentro e entre os quadros amostrados, com registro da observação fornecida. | A revisão identifica defeitos temporais e sonoros quando há evidência suficiente. |
| O motor produz a técnica? | Composição pequena, materiais e propriedades fixos, comparando comportamento previsto e render. | Divergência localiza defeito/ausência concreta; correspondência desloca a investigação para decisão e direção. |
| O aprendizado transfere? | Um exemplar estudado e dois briefs inéditos por mecanismo, incluindo caso em que a técnica atrapalha. | O editor adapta a escolha e evita o contraexemplo sem repetir o objeto ou produto do exemplar. |
| O fluxo se aproxima de uma edição pela IDE? | Mesmo modelo, briefing, fontes, guia e critério de qualidade, documentando ferramentas e intervenções disponíveis. | As diferenças de resultado podem ser atribuídas ao que de fato mudou no ambiente. |

Uma análise documental localiza limitações e testa a coerência das explicações. Atribuição causal exclusiva e domínio de qualquer gênero permanecem perguntas experimentais. O próximo avanço verificável é uma decisão editorial bem executada e transferida a outro caso, acompanhada do contexto que a tornou possível.

Nas comparações futuras, os critérios de revisão devem ser definidos antes da coleta. Um avaliador independente recebe os cortes em ordem aleatória, sem conhecer a variante, o custo ou a justificativa do editor. A compreensão espontânea vem antes da preferência estética. O relatório conserva os erros e as perdas de cada tentativa. Esse desenho permite confrontar a expectativa dos responsáveis com a leitura do espectador.

O diagnóstico metodológico foi conduzido por Sackett, Booth e Creswell em sequência. A auditoria técnica ficou com Forsgren e o catálogo editorial com Klein, por meio de agentes da pesquisa. A auditoria final de Ioannidis e Kahneman ocorreu sequencialmente. Seus ajustes foram vincular os intervalos ao acervo específico, restringir alegações sobre o motor à evidência disponível e prever avaliação independente e cega. Essa coordenação ocorreu nesta investigação do Codex. A implementação das propostas permanece em uma etapa futura.
