# res — inteligência e repertório para edição de vídeo

Pesquisa e revisão técnica • 6 de setembro de 2026 • Preparação para o modo planejamento

## 1. A conclusão que orienta o próximo passo

**O res possui uma base útil de edição, mas ainda não há evidência de um editor profissional autônomo capaz de resolver qualquer cena. A principal lacuna está na ligação entre compreender o material, escolher uma solução editorial e construir uma composição executável.** Acrescentar fontes, arquivos ou nomes de efeitos aumenta as opções; não resolve sozinho essa ligação.

O avanço mais valioso é transformar repertório em procedimentos verificáveis: o sistema precisa reconhecer uma situação, escolher uma técnica adequada, identificar os materiais que ela exige, construir a cena e conferir se a intenção sobreviveu à exportação. Uma fonte nova deve participar de hierarquia e ritmo de leitura. Um recorte deve estabelecer uma relação espacial. Um som deve ter uma função na cena.

Recomendação desta pesquisa: aproveitar os contratos, a timeline, o catálogo, o MotionGraph, FFmpeg e HyperFrames já existentes. A prioridade intelectual é uma direção de cenas que conecte essas peças. A prioridade técnica é ampliar as composições que essa direção consegue expressar. A prioridade de validação é comparar um vídeo de entrada com uma edição real, incluindo o som e uma revisão localizada.

Este documento entrega diagnóstico, repertório e critérios para o planejamento. Não executa um novo teste de vídeo nem altera o código da aplicação. Gemini permanece a preferência do projeto, com provedores separados por capacidade; trocar a LLM não elimina as lacunas abaixo.

## 2. Método, evidência e limites

Foram retomados o código do res em `C:/Users/edugu/Downloads/res`, os documentos de pesquisa existentes e o acervo de observações de 05/09. Nesta continuação, seis publicações foram reabertas no navegador local do GPT, com inspeção de quadros durante a reprodução, leitura de duração e métricas públicas: motion outfit, pontos, estrelas, humor de chamada, Alex Cisse e café/localização.

A pesquisa anterior registra 48 posições de grade, 47 publicações distintas e 12 publicações examinadas visualmente. A nova sessão **revisita seis desses casos**, não soma seis vídeos inéditos. Tempos identificam quadros observados, não limites exatos de cortes. A base anterior permanece em `docs/studios/research/clicko-video-studio-2026-09-05/ANALISE-INSTAGRAM.md` e `instagram-metricas.csv`; o nome legado da pasta não altera o produto analisado: res.

Os players estavam sem som. Créditos de áudio e descrições foram lidos, mas não equivalem a audição. Não foram verificados BPM, transientes, qualidade da voz, mixagem ou sincronismo musical dessas publicações. Também não estavam disponíveis retenção, salvamentos, compartilhamentos privados, alcance único ou investimento em mídia. Nenhuma conclusão atribui causalmente desempenho a um efeito.

As fontes externas priorizadas são documentação oficial, descrição de processos pelos próprios profissionais, artigos assinados e pesquisa acadêmica. Páginas de cursos foram examinadas como programas de estudo; não como cursos assistidos. Livros são indicações bibliográficas baseadas nos editores, sem alegação de leitura integral. A revisão de código foi estática e delimitada ao caminho de edição contextual, recursos e motion. Não foram executados testes da aplicação nesta etapa; testes antigos não certificam qualidade editorial atual.

## 3. O que os dois Instagrams ensinam ao sistema

### 3.1 Motion outfit: preencher uma região com outra mídia

[Publicação em colaboração entre creators e moonsol.design](https://www.instagram.com/creators/reel/Dct4pAohiup/) • 35,18 s • leitura atual: aproximadamente 45,3 mil curtidas, idade exibida de seis dias.

Aos aproximadamente 20,44 s, a roupa de uma pessoa em uma fotografia aparece delimitada manualmente por pontos e contorno. Aos 26,27 s, uma mídia de paisagem está posicionada dentro da região da blusa, com trilhas e transformação de tamanho visíveis. A descrição atribui o procedimento a recorte e sobreposição no Edits.

**Técnica transferível:** máscara de região, preenchimento por mídia, enquadramento do preenchimento e ordem de camadas. Os parâmetros importantes são sujeito/região, forma da máscara, suavidade da borda, mídia interna, escala, posição e duração. A composição permite usar outro objeto, outra identidade e outra imagem sem depender de uma roupa específica.

**Fronteira:** o exemplo observado usa fotografia. Não demonstra rastreamento de tecido deformável, preservação de mãos em movimento ou substituição generativa de figurino em vídeo. O res tem máscara estática e sobreposição; ainda precisa obter a região correta e planejar a composição. Uma máscara aceita pelo compilador não prova que ela recorta a roupa certa.

### 3.2 Conectar pontos: revelar uma relação visual

[Tutorial de moonsol.design](https://www.instagram.com/moonsol.design/reel/DcdfCb9SW8F/) • 49,27 s • 25/08 • leitura atual: cerca de 1,1 mil curtidas, cinco comentários e 21 repostagens.

Aos 4,52 s, aparece um desenho verde parcialmente revelado sobre uma fotografia. Aos 19,14 s, o tutorial instrui adicionar um ponto como texto enquanto uma linha parcial serve de guia. O procedimento manual usa recursos disponíveis no aplicativo para simular uma construção gráfica.

**Técnica transferível:** trajetória vetorial, pontos distribuídos e revelação progressiva. O sistema não precisa reproduzir a sequência de cliques nem usar caracteres de ponto: pode representar pontos e traçados geometricamente. Precisa conhecer origem/destino, ordem, espessura, ritmo e o significado da conexão.

**Fronteira:** rasterizar uma imagem de linha permite exibi-la, mas perde sua estrutura editável. Um movimento de posição de uma imagem não equivale a desenhar um traçado. Essa distinção deve aparecer no registro de capacidades.

### 3.3 Estrelas: repetição organizada e animação de conjunto

[Tutorial de moonsol.design](https://www.instagram.com/moonsol.design/reel/DcxuG6fIxZ-/) • 39,15 s • quatro dias • leitura atual: aproximadamente 4,2 mil curtidas, 19 comentários e 123 repostagens.

Por volta de 11,33 s, três estrelas de tamanhos diferentes aparecem empilhadas; o tutorial propõe duplicação para formar uma composição circular. Aos 23,74 s, o conjunto está sobre uma fotografia e a instrução indica rotação no final da sobreposição. Há várias trilhas e uma composição de conjunto, não apenas um ícone isolado.

**Técnica transferível:** instanciar uma forma, distribuir cópias, variar escala, agrupar e animar o conjunto. A cor rosa e a estrela são escolhas de identidade. O princípio serve também para círculos, recortes, ícones ou elementos de produto.

**Fronteira:** não inferir física real, trajetória 3D ou som de brilho. Para uma composição com o elemento passando atrás do assunto, é necessário um recorte de primeiro plano adicional. Esse requisito não pode ser substituído por uma simples mudança de ordem de duas imagens inteiras.

### 3.4 Café e localização: informação integrada à profundidade

[Tutorial de moonsol.design](https://www.instagram.com/moonsol.design/reel/DRjjvOogSZg/) • 32,02 s • publicação de 27/11/2025 • leitura atual: cerca de 580,3 mil curtidas, 221 comentários e 12 mil repostagens.

Aos 4,52 s, a fotografia, o prato em primeiro plano e o cartão de localização formam a apresentação. Aos 9,96 s, o cartão está isolado para preparação. A pesquisa anterior também registrou os passos intermediários de fotografia, cartão e composição final. Trata-se de um tutorial em vídeo para composição de imagem/story; a peça final não comprova animação complexa.

**Técnica transferível:** inserir um cartão informativo, hierarquizar imagem e dados e utilizar oclusão para integrar o cartão ao espaço. Materiais: fotografia, recorte de primeiro plano e cartão com conteúdo correto. Parâmetros: sobreposição, margens, contraste, escala e profundidade relativa.

**Fronteira:** o local, a avaliação ou os dados do cartão não devem ser inventados a partir do aspecto visual. O sistema precisa separar a referência de composição da informação factual que será inserida. O post antigo fixado é repertório; não prova uma tendência em aceleração hoje.

### 3.5 Humor de chamada: saber preservar o momento

[Peça selecionada por creators](https://www.instagram.com/creators/reel/Dcl3b2LR6NC/) • 10,73 s • 28/08 • leitura atual: aproximadamente 162,2 mil curtidas, 4,3 mil comentários e 12,2 mil repostagens.

A pesquisa anterior registrou pergunta, resposta, chamada e reação em enquadramento estável. Nesta sessão, por volta de 6,07 s, a personagem olha o telefone sob a indicação de chamada recebida. Texto contrastado e reação permanecem legíveis. Não é necessário inferir uma grande quantidade de efeitos para explicar a construção visual.

**Técnica transferível:** preparação, mudança de situação e tempo para reação; texto como informação da cena. Uma regra que encurta toda pausa ou adiciona um movimento a cada frase pode prejudicar esse tipo de vídeo. O sistema precisa poder justificar manter um trecho.

**Fronteira:** a identificação do público com a situação é uma hipótese editorial. As métricas não permitem separar sua contribuição da edição, da distribuição ou da audiência do perfil.

### 3.6 Alex Cisse: ordenar imagens para construir uma memória

[Peça em creators](https://www.instagram.com/creators/reel/Dc3qMrJxJcp/) • 41,70 s • dois dias • leitura atual: cerca de 37,4 mil curtidas, 661 comentários e 517 repostagens.

Aos 0,87 s, o enquadramento alto mostra uma pessoa no sofá; aos 19,92 s, a composição combina uma pessoa reclinada, uma janela e paisagem. Pequenas unidades de texto aparecem sobre a imagem. A descrição do próprio post relaciona a edição à reorganização de memórias e à escolha de ordem, ritmo e música.

**Técnica transferível:** selecionar momentos com função narrativa, variar distância/enquadramento e controlar a quantidade de texto em cada momento. Para transferir a solução, o res precisa reconhecer relações entre planos, e não escolher imagens somente porque contêm palavras do roteiro.

**Fronteira:** a referência à música vem da descrição. Não houve audição para confirmar como ela muda a experiência. As duas capturas desta sessão não demonstram, por si, todas as transições do vídeo.

### 3.7 Complementos preservados da análise anterior

O aniversário `DcMFvawPPIl` acrescenta demonstração filmada e tipografia que vira textura; Kayra `DcRcZzhPGYV`, progressão entre pessoa, memória e trabalho; a colagem `Dcys2J3MfYK`, recortes e estados visuais sucessivos; xadrez `DQBrO73gf-S`, profundidade em fotografia; teia `Db2zPhdo5b_`, perspectiva gráfica; Papo de Criador `Dc6O2ryRBP9`, alternância entre apresentação e exemplos. Esses seis permanecem **evidência histórica de 05/09**, sem nova decupagem nesta sessão. Links, quadros e métricas estão na análise anterior.

### 3.8 O que as métricas permitem dizer

| Caso | Visualizações registradas em 05/09 | O que a comparação permite | Limite importante |
|---|---:|---|---|
| Aniversário | 62,3 milhões | Maior contagem nas 24 posições de creators observadas | Não mede retenção nem efeito causal da tipografia |
| Kayra | 50,5 milhões | Alto alcance também com construção narrativa diferente | Tema, audiência e distribuição diferem |
| Humor de chamada | 32,9 milhões | Exemplo simples também teve alto alcance e muitas repostagens | Não autoriza uma regra universal de duração |
| Motion outfit | 14,9 milhões | Forte distribuição da colaboração | Uma publicação em duas contas; não duplicar amostra |
| Café/localização | 8,4 milhões | Exemplo útil para estudar interesse por composição | Post antigo e fixado, com meses de exposição |
| Estrelas | 296 mil | Registro datado de uma aplicação recente | A nova sessão mediu curtidas, não novas visualizações |

Esses números vêm do CSV anterior, não de uma nova coleta de visualizações. As leituras atuais de curtidas não atualizam automaticamente as visualizações antigas. Não calcular uma taxa misturando datas. Uma classificação útil de tendência precisará de observações repetidas, idade do post, colaboração/fixação e contexto do perfil, mantendo separadas adoção, velocidade de crescimento e qualidade editorial.

## 4. Referências profissionais e o que aprender delas

**Processo de estúdio.** Ordinary Folk descreve mensagem, design, animação e áudio, com som considerado desde o início e desenvolvimento a partir de storyboard/animatic. A contribuição para o res é a sequência de decisões e artefatos intermediários, não uma estética para copiar. [Processo oficial](https://www.ordinaryfolk.co/process).

**Formação em motion.** O programa de Ben Marriott combina curvas de velocidade, máscaras/revelações, match cuts, estilos, parallax e composição de uma peça explicativa com storyboard e animatic. Serve como currículo para mapear habilidades independentes e exercícios. Não foi comprado ou assistido; a avaliação aqui é do programa público. [Motion Foundation](https://www.benmarriott.com/motion-foundation).

**Narrativa e ritmo.** Walter Murch é referência bibliográfica para critérios de corte e continuidade; Karen Pearlman, para desenvolver percepção e decisão rítmica; Bruce Block, para relacionar espaço, forma, tom, cor e movimento à estrutura visual. A tradução proposta para o sistema é registrar o motivo e o efeito esperado das escolhas. Não transformar princípios artísticos em percentuais ou regras fixas. [Murch, editora](https://www.silmanjamespress.com/shop/filmmaking-directing/in-the-blink-of-an-eye2nd-edition/), [Pearlman, editora](https://www.routledge.com/Cutting-Rhythms-Creative-Film-Editing/Pearlman/p/book/9781041024088), [Block, editora](https://www.routledge.com/The-Visual-Story-Creating-the-Visual-Structure-of-Film-TV-and-Digital-Media/Block/p/book/9781138014152). A página integral de Pearlman bloqueou a leitura; apenas a referência editorial indexada foi recuperada.

**Som como decisão de montagem.** Randy Thom defende construir o filme considerando o som e seu ponto de vista, inclusive deixando espaço para ouvir. Para o res, isso significa planejar entradas, ausências e relações sonoras junto das imagens, em vez de anexar efeitos ao vídeo terminado. [Artigo assinado, 1999](https://www.filmsound.org/articles/designing_for_sound.htm).

**Pesquisa de representação.** Scrolly2Reel usa unidades narrativas para relacionar gráficos, narração e ritmo na adaptação de conteúdo. É uma referência para a representação intermediária proposta; o escopo do trabalho é específico e não valida um editor universal. [Artigo dos autores](https://arxiv.org/abs/2403.18111).

### Editores e motores: referência por especialidade

Não existe um ranking único adequado a este projeto. A comparação abaixo separa o que estudar do que integrar.

| Referência | Especialidade útil ao res | Decisão recomendada nesta etapa |
|---|---|---|
| DaVinci Resolve / Fusion / Fairlight | Montagem, cor, composição por nós, tracking e pós-produção sonora | Usar exercícios oficiais como critérios de qualidade; não substituir a arquitetura atual |
| Adobe Premiere | Montagem temporal e separação entre momento do corte visual e sonoro | Estudar J/L cuts e aplicação em diálogo e continuidade |
| Adobe After Effects | Tipografia por palavra/caractere, seletores, máscaras e motion | Transformar conceitos em componentes do res com parâmetros e testes |
| Cavalry | Repetição procedural, distribuição e deslocamento temporal entre elementos | Referência forte para uma gramática de composições, em vez de duplicações manuais fixas |
| Blender | Composição, tracking de câmera/objeto e espaço 3D | Extensão especializada posterior, quando houver caso e validação próprios |
| HyperFrames + FFmpeg | Composição programável e processamento audiovisual na arquitetura atual | Consolidar como caminho principal antes de multiplicar renderizadores |
| Motion Canvas | Interpolação, fluxo temporal e cenas descritas por código | Aproveitar conceitos e a projeção já modelada; qualificar integração real antes de anunciar disponibilidade |

Fontes que sustentam as especialidades: [treinamento Blackmagic](https://www.blackmagicdesign.com/products/davinciresolve/training), [J/L cuts Adobe](https://helpx.adobe.com/uk/premiere/desktop/edit-projects/trim-clips/perform-j-cuts-and-l-cuts.html), [texto no After Effects](https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html), [Duplicator](https://cavalry.studio/docs/nodes/shapes/duplicator/) e [Stagger](https://cavalry.studio/docs/nodes/behaviours/stagger/), [Blender VFX](https://www.blender.org/features/vfx/), [HyperFrames](https://hyperframes.heygen.com/concepts/determinism), [Motion Canvas](https://motion-canvas.io/docs/tweening/). As páginas oficiais demonstram capacidades desses produtos; não demonstram que todas estão conectadas ao res.

## 5. Revisão do res: capacidades reais e lacunas

Os caminhos abaixo são relativos à raiz inspecionada `C:/Users/edugu/Downloads/res`. As classificações descrevem o caminho revisado, não certificam todos os fluxos do repositório.

| Área | Evidência no código | Resultado da revisão |
|---|---|---|
| Montagem determinística | `backend/app/providers/studios/contextual_render.py:30` | Há cortes, multitrilha, enquadramento, texto, máscara estática, keyframes, fades/dissolve, congelamento, velocidade constante, cor e mixagem |
| Técnicas indisponíveis | Mesmo arquivo, linha 45; `backend/app/services/studios/contextual_editing.py:1057` | Tracking, rotoscopia, máscara temporal, rampa, estabilização e 3D não estão certificados nesse caminho; técnica solicitada sem execução/material gera impedimento |
| Recursos | `backend/app/services/studios/editing_resources.py:22` | Catálogo por cliente, arquivo/metadata e busca textual; consulta exige todos os termos em título, descrição ou tags e retorna até 100 itens |
| Direção de materiais | `backend/app/services/studios/material_director.py:88` | Liga uma necessidade ao apoio, máscara ou áudio de um beat; várias necessidades podem colidir no mesmo campo |
| Planejamento | `backend/app/services/studios/gemini_editing.py:33` | Plano estruturado de beats, ordem, técnicas e materiais; não produz MotionGraph nesse contrato |
| Percepção | Mesmo arquivo, linha 299 | No caminho automático sem mídia explícita, amostra até 24 clips, com início/meio/fim; não é análise contínua do vídeo |
| Repertório | Mesmo arquivo, linha 393; `backend/app/services/studios/editing_repertoire.py:290` | Primeiras 100 fichas entram no contexto; busca recupera evidência, mas mudança executável depende de perfil tipado solicitado |
| Motion | `backend/app/domain/studios/motion.py:286`; `backend/app/services/studios/video_render.py:147` | Grafo com nós, trilhas, transições, eventos e restrições já existe e tem caminho de render associado a revisão; integração intelectual ainda fragmentada |
| Tipografia no motion | `backend/app/providers/studios/hyperframes_projection.py:45` | Projeção rejeita fonte customizada; texto usa Arial/Helvetica. A capacidade do outro renderizador não elimina essa diferença |
| Verificação da exportação | `backend/app/services/studios/contextual_editing.py:1290` | Confere cobertura de elementos compilados/encodados; explicitamente não avalia correção semântica ou perceptual |
| Provedores | `backend/app/providers/studios/editing_ai.py:24` | Seleção por operação e adaptador de planejamento compatível; qualificações de mídia real ainda aparecem como pendentes |

### Achados prioritários para o planejamento

**A1 — Direção contextual e grafo de motion não formam um fluxo completo. Prioridade de produto alta.** `GeminiDirection` aceita beats e técnicas, enquanto o render de motion recebe um grafo previamente construído e revisado. O compilador contextual exige timeline de vídeo (`contextual_editing.py:519`). Um pedido de criar uma cena gráfica a partir de uma ideia ainda não dispõe, nesse caminho, de uma transformação demonstrada da intenção para o grafo. Reaproveitar o MotionGraph é preferível a criar outro contrato paralelo.

**A2 — O plano por beat tem poucos espaços para materiais. Prioridade de produto alta.** `EditingBeatV1`, em `backend/app/domain/studios/contextual_editing.py:41`, contém um apoio, uma máscara e um áudio. Em `material_director.py:88`, música, ambiente e efeito apontam para o mesmo campo. Um beat que precise dos três pode ficar aguardando material mesmo com os arquivos presentes. Isso limita a expressão do planejador; não significa que a timeline inteira só aceite uma trilha. A evolução deve usar elementos e eventos com papéis e relações dentro da cena.

**A3 — Amostragem fixa pode perder a ação que motiva o corte. Prioridade de produto alta.** Início/meio/fim de até 24 clips é uma visão limitada. Uma interação curta, troca de expressão ou texto transitório pode ocorrer fora desses quadros. É preciso selecionar amostras por mudanças e eventos, registrar cobertura e pedir inspeção adicional quando a decisão depender do trecho não observado. A transcrição ajuda o conteúdo verbal, mas não substitui observar a ação.

**A4 — Crescer o acervo não garante que o planejador veja a técnica relevante. Achado de correção P2.** `available_repertoire` acumula fichas em ordem e o contexto corta a lista nas primeiras 100 (`gemini_editing.py:393`). Depois desse limite, uma nova técnica pode não chegar ao planejador mesmo quando é relevante. O comportamento é verificável pela leitura desses caminhos; não foi reproduzido com banco nesta etapa. Recuperação por objetivo/material/capacidade deve anteceder o limite de contexto.

**A5 — Perfil de composição ainda é estreito. Prioridade de produto alta.** `EditingCompositionProfileV1`, em `backend/app/domain/studios/contextual_editing.py:185`, configura proporção do apoio, entrada e duração. Isso pode variar uma inserção, mas não expressa a topologia de uma cena de estrelas, mapa recortado ou linha conectando objetos. A ficha de conhecimento já tem propósito, contraindicações e exemplos; falta uma receita executável com elementos, dependências e parâmetros mais amplos.

**A6 — Fontes não têm equivalência entre os caminhos. Achado de compatibilidade P2.** Em `hyperframes_projection.py:45`, uma camada com `fontAssetId` é rejeitada, e o estilo textual subsequente fixa famílias genéricas. Não há erro silencioso aqui: há limitação explícita. Para identidade visual em motion, será necessário resolver a fonte do projeto no mesmo runtime de prévia e exportação, mantendo os testes de caracteres do catálogo.

**A7 — Revisão localizada ainda corresponde a operações fixas. Prioridade de produto média.** Em `contextual_editing.py:1193`, “menos texto” remove os complementos textuais selecionados; “mais calmo” remove keyframes do apoio e ajusta fades; mostrar melhor o produto aumenta o apoio. São alterações localizadas úteis, mas não equivalem a reescrever texto com concisão, redistribuir pausas ou selecionar uma demonstração melhor. Preservar a localização da mudança e acrescentar diagnóstico editorial antes de decidir a operação.

**A8 — Cobertura de render não certifica qualidade. Prioridade de validação alta.** O recibo confirma IDs e omissões esperadas; não mede leitura, oclusão, continuidade de rosto, sincronia percebida ou preservação de ressalvas. O próprio código declara essa fronteira. A avaliação profissional deve acrescentar observações do MP4 e do áudio, com tempo, motivo e evidência de falha, mantendo o recibo técnico como uma camada distinta.

**A9 — SVG utilizável não é SVG editável. Prioridade de produto média.** `editing_resources.py:110` valida e rasteriza SVG, preservando referência ao checksum original. Isso é útil para exibir logos, mas não entrega caminhos vetoriais manipuláveis ao compositor. Revelar traçados, ajustar segmentos ou fazer morph exige representação de geometria própria ou outra ingestão qualificada.

Pontos que merecem ser preservados: vínculo de revisão e checksum dos materiais, validação de transcrição, impedimentos explícitos, separação entre evidência e alegação causal e recusa de técnicas sem parâmetros executados. A marcação de observação recente em `editing_repertoire.py:337` indica idade da leitura; não deve ser exibida como prova de tendência crescente. O adaptador compatível contém bloqueios explícitos para GPT em produção, mas esta revisão não é uma auditoria integral de todas as saídas de rede do produto.

## 6. Repertório operacional que faz falta

As fichas abaixo são **propostas de engenharia editorial derivadas desta análise**. Não são capacidades recém-implementadas nem receitas universais. “Base existente” indica operações aproveitáveis; a composição completa ainda precisa ser qualificada.

### Grupo A — montagem e narrativa

| Técnica | Finalidade e condição de uso | Materiais e parâmetros | Como executar e verificar no res |
|---|---|---|---|
| Corte por mudança de informação | Avançar quando surge ação, dado ou reação; evitar cortar uma ressalva | Intervalos de origem, unidades de sentido, dependências entre frases | Base de cortes existe; selecionar limites semanticamente, comparar transcrição e contexto antes/depois |
| Continuidade de ação e olhar | Conectar planos da mesma ação; evitar falsa continuidade entre momentos incompatíveis | Posição, direção, fase do gesto, planos disponíveis | Acrescentar seleção visual e relações entre planos; conferir gesto, eixo e objeto persistente |
| J/L cut | Antecipar ou prolongar áudio para conectar cenas; não atribuir fala à pessoa errada | Áudio separado, pontos de entrada/saída e caudas | Trilhas independentes são base; qualificar alinhamento e contexto, não apenas sobreposição |
| Demonstração com apoio | Mostrar o que a fala explica; evitar uma imagem apenas decorativa | Entidade correta, momento relevante, trecho da demonstração | Ampliar apoio para seleção temporal e enquadramento por entidade; conferir se a evidência realmente aparece |
| Preparação, pausa e reação | Permitir expectativa e compreensão; evitar compressão automática de toda pausa | Ação e reação completas, intenção de humor/tensão/clareza | Usar decisão de manter; avaliar o efeito da pausa em comparação com o original |
| Match cut visual ou conceitual | Conectar duas ideias por forma, posição ou movimento | Âncoras comparáveis, enquadramentos e significado compatível | Precisa correspondência entre planos; verificar alinhamento e se a conexão não inventa causalidade |
| Montagem de arquivo | Construir progressão com materiais de tempos/lugares diferentes | Proveniência, ordem, legendas contextuais, conteúdo comprovado | Selecionar por função narrativa; manter contexto factual e identificar imagens ilustrativas quando necessário |

### Grupo B — composição, tipografia e movimento

| Técnica | Finalidade e quando evitar | Materiais e parâmetros | Como executar e verificar no res |
|---|---|---|---|
| Hierarquia tipográfica | Separar título, explicação e dado; evitar vários focos simultâneos | Família/variante, largura, entrelinha, contraste, área disponível | Fonte real mais medição de texto; verificar quebra, acentos, colisões e tempo de leitura |
| Tipografia cinética por unidades | Dar ênfase a palavras ou construir uma frase; evitar fragmentar negações | Palavras/caracteres, grupos semânticos, atraso e curva | Implementar seletores/grupos; conferir ordem, frase completa e equivalência no render |
| Revelação por máscara | Apresentar um elemento gradualmente | Máscara, elemento, direção, suavidade e duração | Máscara estática é base parcial; qualificar máscara animada/clip de revelação e bordas |
| Repetição e distribuição | Formar conjuntos, padrões ou hierarquias | Forma mestre, contagem, distribuição, escala e grupo | Gerar instâncias determinísticas; verificar número, espaçamento, ordem e adaptação ao conteúdo |
| Stagger e sobreposição temporal | Criar progressão dentro de um conjunto | Ordem, atraso por instância, duração e curva | Compilar eventos relacionados; conferir se a sequência orienta o olhar sem prolongar demais |
| Desenho de traçado | Mostrar ligação, percurso ou construção | Caminho vetorial, progressão, espessura e pontos | Novo componente de caminho; verificar início/fim, direção e progressão no MP4 |
| Profundidade por oclusão | Integrar informação ao espaço da imagem | Fundo, recorte frontal, cartão/objeto e relações de frente/atrás | Multicamadas e máscaras são base; conferir bordas, visibilidade da informação e ordem espacial |
| Parallax 2,5D | Sugerir profundidade em fotografia; evitar revelar áreas inexistentes | Camadas separadas, regiões ocultas reconstruídas, deslocamentos | Base de transforms parcial; avaliar buracos, bordas e coerência do movimento relativo |
| Antecipação e acomodação | Dar preparação e peso ao movimento | Estados, curva, intensidade, tempo de pausa | MotionGraph tem curvas/restrições; escolher pelo papel do objeto, limitar overshoot quando legibilidade exigir |
| Transição por continuidade | Transportar um elemento de uma cena a outra | Identidade persistente, posição inicial/final e contexto | Construir ligação entre cenas; conferir que a transformação não apaga informação necessária |
| Colagem em estados | Revelar objetos ou etapas por recortes sucessivos | Recortes individuais, fundo, ordem e duração por estado | Planejar estados e material por elemento; evitar imitar duração fixa de um tutorial |
| Integração em superfície filmada | Colocar gráfico ou marca acompanhando uma superfície | Track, plano/perspectiva, oclusores, luz e referência | Extensão ainda não certificada no caminho contextual; medir deriva e revisar oclusão quadro a quadro em trechos críticos |

A documentação de seletores do After Effects, distribuição do Cavalry e interpolação do Motion Canvas oferece mecanismos para várias dessas fichas. A escolha de finalidade, contraindicações e critérios acima é a síntese proposta para o res, não uma alegação de que a documentação já resolve direção editorial.

### Grupo C — desenho e edição sonora

| Técnica | Finalidade e quando evitar | Materiais e parâmetros | Como executar e verificar no res |
|---|---|---|---|
| Hierarquia de fala | Manter a mensagem compreensível sem achatar toda dinâmica | Diálogo, ruído de fundo, ganho, compressão e pausas | Mixagem/ducking são base; medir pico/loudness e ouvir palavras críticas no conjunto |
| Ambiente e ponte sonora | Dar continuidade espacial entre planos | Room tone/ambiente, ponto de vista, entrada/cauda | Eventos de áudio por cena; verificar cortes abruptos, mudanças artificiais de espaço e mascaramento |
| Acento sincronizado | Destacar uma ação ou informação específica | Ataque/transiente, momento visual e intensidade | Alinhar pelo evento audível, não somente pelo começo do arquivo; verificar poucos quadros antes/depois |
| Ritmo por frase musical | Relacionar progressão da peça a frases, mudanças e pausas | Música, marcações estruturais, ação e restrições da fala | Seleção temporal orientada pela estrutura; evitar cortar todo plano em cada batida |
| Silêncio e contraste | Abrir espaço para reação, suspense ou compreensão | Intenção, ambiente residual e limites de fala | Permitir ausência de trilha; conferir se a pausa tem função e não é uma falha de render |
| Perspectiva e timbre | Fazer o som pertencer ao material e ao espaço | Categoria, textura, proximidade, reverberação e variantes | Evoluir taxonomia e busca; audição comparativa de candidatos, sem escolher apenas pela palavra “impacto” |

O acervo sonoro deveria combinar a classificação do [Universal Category System](https://universalcategorysystem.com/) com campos editoriais próprios: função, intensidade, textura, ataque, cauda, proximidade, ponto de sincronismo e faixa útil. O UCS organiza categorias e nomes; não determina qual som combina com uma cena.

Para aquisição, bibliotecas próprias e pacotes importados continuam sendo a primeira base. [Freesound](https://freesound.org/help/faq/) permite descobrir materiais com condições diferentes por arquivo. A [biblioteca do YouTube](https://support.google.com/youtube/answer/3376882?hl=en) oferece busca e downloads de música/efeitos dentro do Studio. Essas fontes não são promessa de catálogo universal, API já integrada ou autorização automática para redistribuir um pacote dentro de um SaaS. O res precisa registrar as condições do arquivo e do uso pretendido; não houve compra ou download de mídia nesta pesquisa.

## 7. Como transformar pesquisa em intelecto utilizável

### Uma base conectada, com seis tipos de conhecimento

| Tipo | Conteúdo | Pergunta que precisa responder |
|---|---|---|
| Princípio | Continuidade, hierarquia, contraste, ritmo, relação som/imagem | Por que essa intervenção ajudaria? |
| Observação | Vídeo, quadros/intervalos, data, autoria, descrição e limites | Onde isso foi visto e o que foi realmente verificado? |
| Técnica executável | Pré-condições, elementos, operações, parâmetros, falhas e testes | Como construir essa intervenção com os materiais atuais? |
| Estilo | Regras combináveis de tipografia, cor, espaço, movimento, textura e som | Como manter identidade entre cenas diferentes? |
| Material | Arquivo, entidade, aparência, partes, origem e condições de uso | O que existe, o que falta e o que precisa ser pedido? |
| Avaliação | Resultado, alterações, falhas, revisão e contexto | Funcionou para esse objetivo? Em quais condições falhou? |

Esses tipos podem reutilizar a base existente, com relações explícitas. Não exigem seis bancos novos. Uma observação pode exemplificar várias técnicas; uma técnica pode ter vários compiladores; um estilo pode trocar cores e fontes sem mudar o significado das cenas. Um resultado ruim deve virar contraexemplo recuperável, sem apagar o histórico anterior.

### A unidade central deve ser a cena com relações

O beat existente é um ponto de partida. O próximo contrato precisa representar o que o espectador deve entender, fatos que não podem mudar, elementos da cena, relações espaciais/temporais, materiais presentes ou ausentes e critérios de avaliação. “Produto à frente do cartão”, “palavra aparece após a demonstração” e “som começa quando a conexão é concluída” são relações; não são apenas listas independentes de efeitos.

Exemplo de raciocínio esperado para um tema de organização de informação: vários cartões expressam dispersão; uma conexão mostra a relação; agrupamento reduz a complexidade; uma conclusão permanece tempo suficiente para leitura. Se a intenção for calma, reduzir movimentos concorrentes e aumentar acomodação. Se for mostrar um mecanismo, priorizar a transformação visual e sua explicação. As escolhas devem apontar para elementos do mesmo grafo, permitindo alterar apenas a parte solicitada depois.

Para materiais ausentes, descrever o pedido com precisão: função na cena, entidade, perspectiva, transparência/recorte, duração, variante visual e critérios de aceitação. “Preciso de uma imagem” não é suficiente. “Preciso do símbolo oficial em vetor ou PNG transparente, com espaço para inserir sobre um cartão escuro” é um pedido operacional. Um nome famoso, uma roupa ou uma marca nova não deve exigir um ramo específico de código.

### Recuperação e seleção

Primeiro filtrar por materiais, capacidade executável e restrições do projeto. Depois recuperar por intenção, relação visual/sonora e exemplo de uso. Comparar candidatos por contribuição à mensagem, continuidade, leitura e custo de execução medido. Tendência pode desempatar uma decisão pertinente; não deve substituir os critérios principais.

O planejador deve apresentar uma justificativa curta e previsões verificáveis. Quando não houver evidência suficiente para escolher um recurso ou região, solicitar material/inspeção adicional. Para compor por código, gerar a representação tipada e selecionar componentes registrados; não executar código encontrado em uma referência.

### Atualização sem confundir repertório com treinamento

Cada publicação precisa de identidade estável, autor, URL, data de publicação e observações sucessivas. Contagens são eventos datados, com campo ausente diferente de zero. Colaboração entre contas é uma só publicação. Um tutorial revisitado hoje continua podendo demonstrar uma técnica antiga.

O anúncio da Meta sobre um ano do Edits descreve inspiração, organização de ideias e abertura de projetos de templates como recursos para creators. Isso reforça o valor de conectar referência e estrutura editável; não fornece, por si, um conector aberto para coletar tudo. [Meta, abril de 2026](https://about.fb.com/news/2026/04/one-year-of-edits-built-for-and-with-creators/amp/).

Atualizações incrementais devem registrar última coleta bem-sucedida, deduplicação, alterações e incertezas. Classificar tendência exige evidência datada de adoção/desempenho, não apenas nova data de ingestão. A atualização da base e da recuperação não será chamada de treinamento automático de modelo.

## 8. Insumos para o próximo planejamento

### Ordem recomendada para discutir as entregas

1. **Conectar direção de cena ao MotionGraph e à timeline.** Definir como intenção, materiais e relações se tornam uma composição, inclusive em cenas gráficas sem filmagem prévia.
2. **Tornar técnicas combináveis.** Começar com texto por unidades, grupos/repetição, caminhos/revelação, profundidade por recorte e eventos sonoros. Reutilizar as operações existentes onde bastarem.
3. **Melhorar percepção e recuperação.** Amostragem orientada por eventos, seleção por relevância, materiais com entidades/partes e contraexemplos de uso.
4. **Unificar identidade e avaliação.** Fontes reais no motion, inspeção de frames e áudio, revisão localizada com preservação das partes não afetadas.
5. **Qualificar extensões difíceis separadamente.** Tracking, rotoscopia, transformação de figurino, 3D e estabilização precisam de entradas, testes e limites próprios.

Essa ordem é uma hipótese de prioridade para o modo planejamento, não um cronograma aprovado. Não há estimativa séria de prazo ou volume de produção sem medir o fluxo integrado. O orçamento de testes permanece separado da política de produção já definida pelo usuário.

### O que não resolve a barreira principal

Uma coleção enorme de presets pode aumentar cobertura visual, mas continua limitada se o planejador não representa relações entre elementos. Uma LLM mais forte pode propor uma cena que o contrato não consegue expressar. Um gerador pode criar um clip agradável sem preservar identidade ou estrutura editável. Acesso a uma imagem de marca não demonstra adaptação correta ao contexto. Mais renderizadores aumentam as possibilidades e também a necessidade de equivalência e qualificação.

Em particular, um MP4 final não contém automaticamente as camadas, fontes e keyframes originais. Editar seus cortes e adicionar elementos é diferente de alterar com precisão cada objeto interno. Para isso, o sistema precisará do projeto em camadas ou de segmentação/reconstrução, com as limitações correspondentes. Esse limite deve orientar os pedidos de materiais.

## 9. Teste de edição motion a preparar depois do planejamento

**Pergunta do teste:** o res consegue transformar um vídeo existente em uma peça mais clara, com intenção explicável, preservando a informação e aceitando uma revisão localizada?

Proposta de tema para discussão: **“Da informação dispersa à decisão clara”**. É um tema visualmente demonstrável com cartões, conexões, hierarquia e conclusão. A escolha não está fechada. O formato de tela não é uma variável de pesquisa nesta rodada.

**Entrada necessária:** um motion de aproximadamente 20–40 segundos, próprio ou com uso autorizado, com mensagem conhecida e pelo menos uma melhoria editorial identificável. Preservar o MP4 original. Se houver projeto, fontes, vetores e trilhas separados, anexá-los; se houver somente MP4, registrar os limites. Não usar os Reels analisados como arquivos de produção presumidamente disponíveis.

**Preparação do caso:** inventariar materiais; transcrever/verificar texto e fala; listar afirmações e ressalvas; anotar problemas concretos do original; escolher referências de princípio e aplicação. Produzir storyboard/quadros de estilo e um animatic simples para comparar a proposta antes do acabamento. Isso será parte do desenvolvimento interno, sem inventar aprovações humanas.

**Versão A — edição contextual:** reorganizar somente quando houver motivo, reforçar demonstração com uma composição de múltiplos elementos, aplicar tipografia coerente, incluir uma relação de profundidade ou revelação e desenhar os eventos de som. Os elementos novos devem passar pelo fluxo do sistema. Um vídeo montado manualmente fora dele não certifica autonomia do res.

**Versão B — revisão localizada:** pedir “deixe o trecho da explicação mais calmo e reduza o texto, preservando a conclusão”. Comparar grafo, materiais e vídeo, documentando o que mudou. Quando a mesma operação não bastar, a revisão deve explicar a nova decisão e manter o restante.

**Teste separado de geração:** retirar intencionalmente um material necessário e avaliar se o sistema o solicita, encontra ou gera um candidato corretamente. Não misturar esse resultado com prova de tracking ou troca de roupa. O clip gerado precisa ser incorporado e avaliado no contexto, não apenas exibido como resposta do provedor.

### Critérios de avaliação propostos

| Critério | Evidência a produzir | Condição para considerar atendido |
|---|---|---|
| Mensagem | Lista de fatos/ressalvas, texto e transcrição comparados | Nenhuma alteração material de sentido; falhas críticas impedem aprovação |
| Decisão editorial | Objetivo → cena → técnica → operação → tempo no MP4 | Cada intervenção relevante tem finalidade verificável |
| Composição | Frames antes/durante/depois de eventos críticos | Texto legível, oclusão correta, ordem e posições coerentes |
| Movimento | Curvas, estados e reprodução do MP4 | Sem saltos indesejados; relações temporais continuam corretas |
| Som | Audição do vídeo completo, marcações e medições | Fala compreensível; acentos, ambiente e pausas coerentes; sem cortes/clipping indevidos |
| Recursos | IDs, checksums, fontes e resolução de necessidades | Arquivo realmente utilizado e identificação correta do que foi gerado/importado |
| Revisão | Diferença de grafo e comparação A/B | Alterações limitadas ao pedido, salvo dependências explicitadas |
| Repetibilidade | Mesma composição e ambiente fixado | Frames críticos equivalentes e nenhum recurso buscado no meio do render |
| Experiência | Avaliação humana de clareza, continuidade, ritmo e adequação | Avaliadores conseguem apontar ganhos/falhas por trecho, sem nota de qualidade inventada |

A documentação do HyperFrames recomenda relógio por frame, recursos carregados antes da captura e ambiente fixado para reduzir diferenças de render. Isso fundamenta o teste de repetibilidade, mas a equivalência deve ser demonstrada na integração do res. [Contrato de determinismo](https://hyperframes.heygen.com/concepts/determinism).

O pacote do teste deverá conter original, versões A/B, projeto/manifesto, materiais, planos, recibos, avaliação e custos observados. Critérios numéricos de legibilidade, sincronia e tolerância visual serão definidos no planejamento conforme a peça; não assumir uma nota universal. Métricas comerciais entram apenas quando houver publicação e acesso real a elas.

## 10. Estado final desta etapa

Pesquisa e revisão consolidadas, com seis casos reobservados no navegador do GPT, aproveitamento explícito do acervo anterior, fontes primárias, nove achados de integração/capacidade e 25 técnicas candidatas organizadas em três grupos. Foram produzidos este relatório e os registros de evidência. Não houve nova implementação ou certificação por render nesta etapa.

As incertezas que dependem do próximo trabalho estão delimitadas: audição técnica das referências, qualidade do fluxo integrado com mídia real, escolha do vídeo/tema de teste, transformação de elementos em movimento e comparação de resultados editoriais. Elas não impedem iniciar o modo planejamento; precisam aparecer como tarefas de validação, sem promessas de edição universal.
