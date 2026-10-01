# Tutoriais decodificados em operações ensináveis ao res

**Escopo:** tradução de tutoriais efetivamente acompanhados no [caderno inicial](./INSTAGRAM_EDITING_VIEWING_LOG_2026-09-30.md) e na [expansão de 30 Reels](./INSTAGRAM_EDITING_VIEWING_LOG_EXPANSION_2026-09-30.md). Este documento é uma especificação de aprendizagem e avaliação, **não uma implementação nem uma afirmação de que o res já executa os efeitos**. Cada técnica distingue o resultado perceptivo do conjunto de operações mostrado. O texto exato de prompts privados/oferecidos por comentário não está disponível; nenhum prompt foi inventado. A [proposta de modelo de conhecimento](./INSTAGRAM_EDITING_KNOWLEDGE_MODEL_2026-09-30.md) organiza a transferência entre briefs.

## O que significa “ensinar o sistema” aqui

O sistema não deveria memorizar que “texto atrás da pessoa = usar Edits” ou que “efeito bonito = chamar InVideo”. A unidade aprendível é um **procedimento causal**:

1. que relação visual o espectador deve perceber;
2. que material de origem é necessário e que propriedades ele deve ter;
3. quais transformações alteram pixels ou áudio e em qual ordem;
4. que âncoras precisam permanecer estáveis entre estados;
5. quais falhas tornam o resultado falso ou artificial;
6. como comprovar o efeito no render, inclusive nos frames intermediários.

Essa representação permite escolher entre código, editor, geração de imagem/vídeo ou composição manual conforme o caso. Um tutorial não é autorização para copiar o trabalho do criador nem garantia de licença de uso de seus assets. A referência ensina a **gramática**, não fornece material comercial reutilizável.

## Ficha 1 — texto atrás de uma pessoa em movimento

**Fonte:** [@creators / @ruama](https://www.instagram.com/creators/reel/DdwS-6oRvL8/). **Confiabilidade das etapas:** alta para ordem das camadas e recorte, média para parâmetros exatos.

**Efeito observado.** A palavra “TUTORIAL” parece situada no espaço físico em frente à escultura, mas atrás do corpo da apresentadora. Ela permanece legível nas laterais enquanto o corpo tapa as letras centrais.

**Passos mostrados no tutorial.** Importar o clipe base; criar uma camada de texto largo; ajustar sua posição/duração; duplicar o clipe como sobreposição; aplicar recorte automático da pessoa à cópia superior; manter o texto entre a cópia recortada e o clipe original; ajustar o texto por keyframes. A timeline mostra claramente o empilhamento; há um momento de processamento do recorte automático por volta de 28 s. Depois, o vídeo retorna à pessoa falando em outros enquadramentos.

**Pré-condições.** Sujeito distinguível do fundo; região de contraste suficiente para letras; texto não deve ocultar rosto/mãos essenciais; movimento do sujeito precisa caber na máscara; fonte/resolução suportam borda limpa. Se o fundo tiver muita textura, é preciso deslocar o texto, reiluminar ou simplificar a composição.

**Representação operacional:**

```text
camada 3: sujeito recortado do mesmo clipe, sincronizado ao frame da camada 1
camada 2: texto com posição, escala, cor, início/fim e keyframes
camada 1: clipe original
```

**Critérios de verificação.** Amostrar início, meio, fim e frames em que braços/cabelo cruzam letras; verificar se a borda não treme, se não há halo, se as palavras não atravessam o corpo e se o sujeito não “salta” entre base e cópia. Reproduzir na velocidade normal e em tamanho de celular; conferir a palavra sem depender da legenda/caption.

**Aplicação analógica ao Café Aurora:** não apenas “colocar o título na frente do café”. Um texto curto poderia existir atrás de vapor, mão ou xícara se houver separação confiável de profundidade. Sem essa máscara, preferir enquadrar a palavra no espaço negativo real. **Não copiar a palavra, tipografia ou composição do tutorial.**

## Ficha 2 — escaneamento de raio X por máscara móvel

**Fonte:** [@moonsol.design / X-ray](https://www.instagram.com/moonsol.design/reel/Ddv4nmHIsWI/). **Confiabilidade:** alta para sequência foto → variante de IA → máscara → keyframes → efeito sonoro; média para o alinhamento interno do gerador.

**Efeito observado.** Uma região circular percorre a pessoa e revela uma versão de esqueleto luminoso ciano sob a roupa, sem transformar permanentemente o ambiente. O efeito depende de a pose da variante coincidir com a original.

**Passos mostrados.** Adicionar uma foto e colar um prompt no módulo de IA do CapCut (~9 s); salvar a variante gerada (~15 s); voltar à edição com original e variante em trilhas separadas; dimensionar/posicionar a variante; criar máscara circular; inserir keyframes à medida que se move a máscara (~25–27 s); na timeline, adicionar uma faixa de efeito sonoro nomeada como operação de máquina de raio X (~41 s). A escuta e a sincronia exata do som não foram verificadas.

**Pré-condições.** Original e variante precisam retratar a mesma pessoa, pose, câmera e fundo ou ser registrados geometricamente. A borda circular deve ter feather deliberado e a revelação deve ser localizada. O efeito perde credibilidade se esqueleto, roupa e articulações divergirem.

**Representação operacional:**

```text
base = imagem/filmagem original
variante = imagem/filmagem transformada, registrada à base
m(t) = máscara circular ou orgânica com centro/raio/feather animados
frame(t) = base*(1-m(t)) + variante*m(t)
evento sonoro = intervalo ligado à entrada, deslocamento ou saída de m(t)
```

**Critérios de verificação.** Comparar landmarks de cabeça, ombros, mãos e pés nas duas versões; verificar se o fundo não muda fora da máscara, se o círculo não mostra bordas do arquivo gerado, se não há pulsação dos ossos e se o som existe no master e coincide com um evento visível. Se o alinhamento falhar, selecionar outra variante ou abandonar o truque; aumentar blur da máscara não corrige pose errada.

**Aplicação analógica ao produto:** revelar estrutura, ingrediente ou interior de um objeto real por janela móvel. Para embalagem, preservar rótulo/logotipo reais e não alucinar texto dentro da variante.

## Ficha 3 — desenho que vira objeto físico

**Fonte:** [@moonsol.design / doodle to food](https://www.instagram.com/moonsol.design/reel/Dd3k4cBtFrK/). **Confiabilidade:** alta para limpeza da cena e correspondência espacial; média para a construção exata do traço intermediário.

**Efeito observado.** Um contorno incompleto aparece na mesa; esse contorno passa a descrever um copo na posição de um porta-copo; o copo real surge no mesmo lugar. A cena muda de local entre o plano de superfície metálica e o plano de café, mas a forma circular e o centro mantêm a ponte perceptiva.

**Passos mostrados.** O tutorial abre a foto com a bebida no InVideo. Uma instrução legível pede ao agente **remover a bebida deixando uma mesa vazia** (~20 s). O resultado com a bebida é mostrado novamente ao final. O procedimento intermediário que desenha cada linha não foi legível o bastante para especificar ferramenta, curva ou prompt; registrar a lacuna em vez de preenchê-la por suposição.

**Pré-condições.** “Clean plate” fiel ao fundo, sombra e reflexo; referência real do objeto; ponto de apoio (porta-copo/mesa) estável; silhueta final reconhecível; relação de perspectiva compatível. Para filmagem com câmera em movimento, a área limpa e o traço precisam de tracking, ou o movimento deve ser planejado já na captação.

**Representação operacional:** `objeto real → remoção controlada/placa limpa → contorno progressivo → troca em posição coincidente → objeto real`. Esta ordem é a de preparação dos assets; a ordem percebida pelo público pode começar pela placa limpa/desenho e terminar no objeto.

**Critérios de verificação.** O objeto não pode deixar “fantasma” ou sombra contraditória na placa limpa; o contorno não deve flutuar; a troca deve acontecer num mesmo centro e eixo de perspectiva; o objeto real precisa mostrar materialidade e contato. Validar os 3–5 frames da metamorfose, não só os estados antes/depois.

**Aplicação analógica ao Café Aurora:** grãos ou vapor desenham a silhueta de uma xícara/embalagem antes da revelação do produto real. Isso só funciona se uma referência real e uma placa limpa puderem ser preparadas com precisão.

## Ficha 4 — duplicação de objeto numa cena estável

**Fonte:** [@moonsol.design / duplicate masking](https://www.instagram.com/moonsol.design/reel/DdoFxp7oz5C/). **Confiabilidade:** alta para prompt visto, média para operação de máscara, baixa para contagem exata de objetos.

**Efeito observado.** A abertura mostra aviões num aeroporto e um carro vermelho repetido/empilhado em outro ambiente. A câmera e a arquitetura servem como referência fixa para a multiplicação.

**Passos mostrados.** Abrir InVideo e anexar o material; a instrução legível (~17,5 s) toma um avião branco-azul como objeto principal e pede duplicatas sobrepostas empilhadas à direita; o agente analisa o anexo. A timeline posterior mostra faixas de vídeo superpostas e uma camada vinculada ao agente. O tutorial é chamado de *masking*, mas o trecho visível não especifica toda a máscara, tracking, limpeza do fundo ou tratamento de sombras.

**Pré-condições.** Câmera estável ou tracking confiável; duplicatas devem respeitar perspectiva, escala, ordem de profundidade, foco, granulação, iluminação e oclusões. O plano de fundo deve permitir retirar/duplicar o objeto sem repetir acidentalmente placas, pessoas ou marcas.

**Critérios de verificação.** Inspecionar interseções com chão e outros objetos, sombras de contato, linhas do horizonte e consistência temporal. Um único frame convincente não basta se os duplicados deslizam entre frames. Evitar marcas conflitantes e considerar direitos de imagem/asset.

**Aplicação analógica ao produto:** multiplicação de grãos, embalagens ou xícaras somente se o gesto reforçar a proposta criativa. Não criar várias cópias como decoração sem função narrativa.

## Ficha 5 — cutout acionado por gesto dentro de uma interface

**Fonte:** [@creators / @dudanascimento](https://www.instagram.com/creators/reel/Dd4dfPnRkgb/). **Confiabilidade:** alta para gestos e resultado, média para os comandos internos de recorte.

**Efeito observado.** Mãos reais seguram um celular; dentro da tela, uma foto de sobremesa torna-se cenário para uma segunda imagem. A mão arrasta/posiciona um recorte de pessoa com bolo. No resultado, parte do bolo avança para fora da janela interna, criando profundidade recursiva.

**Passos mostrados.** Preparar Story com foto de base; acessar a galeria de imagens; adicionar o recorte de pessoa/bolo; escalonar e posicionar por gesto; preservar a área que deve saltar à frente da moldura. O Reel mostra as mãos e a interface, mas não uma timeline técnica completa nem o algoritmo do cutout.

**Pré-condições.** Frame de interface com geometria conhecida; assets com transparência ou máscara; o gesto deve terminar no local de aparição; dedos não podem ocultar o payoff; composição legível no tamanho de telefone.

**Critérios de verificação.** Contorno do bolo/mão; oclusão correta pela borda da moldura; continuidade temporal entre toque, arrasto e mudança visual; ausência de elementos que apareçam antes da ação causadora. O gesto não deve ser um mero ornamento.

**Aplicação analógica ao produto:** mão real pega ou revela a embalagem, e uma camada gráfica responde ao contato. Se não houver captação de gesto verdadeiro, não simular “mão de stock” sem relação espacial com o produto.

## Ficha 6 — colagem de superfície com elementos pontilhados

**Fonte:** [@moonsol.design / animated dot stickers](https://www.instagram.com/moonsol.design/reel/DdwecRoI4Bf/). **Confiabilidade:** alta para direção visual e ferramenta declarada; média para animação exata de cada sticker.

**Efeito observado.** Fundo de madeira, foto monocromática, título condensado, fotos de café/arte e traços pontilhados que pertencem à mesma superfície editorial. O tutorial mostra a cópia de um motivo pontilhado e inserção na edição pelo InShot; a legenda cita Kaomoji.

**Passos ensináveis.** Definir uma superfície editorial; selecionar fotos com enquadramento compatível; controlar borda/espaçamento; inserir stickers animados como conectores, não ruído; estabelecer hierarquia tipográfica; manter movimento pequeno o bastante para não roubar o foco do objeto principal.

**Critérios de verificação.** A textura e os pontos devem manter contraste e não competir com marca/produto; as fotos não podem parecer simplesmente empilhadas; a animação precisa guiar o olhar entre elementos. Para uma peça sem ação filmada, este tipo de colagem ainda pode parecer slide dinâmico: é recurso secundário, não solução integral.

## Ficha 7 — prompt ao agente + timeline executável

**Fontes:** [transição trem/café](https://www.instagram.com/moonsol.design/reel/DdyZuAKo-iq/), [building transition](https://www.instagram.com/moonsol.design/reel/Dd1EBmsIfof/) e [duplicate masking](https://www.instagram.com/moonsol.design/reel/DdoFxp7oz5C/). **Confiabilidade:** alta para existência do fluxo, baixa para o algoritmo interno do agente.

**Passos mostrados em conjunto.** Importar material na timeline; ajustar clipes; abrir o agente; descrever em linguagem natural a aparência desejada; o agente produz uma timeline com novas faixas; revisar o resultado. Um prompt de duplicação do avião é parcialmente legível; os demais prompts completos não foram exibidos/legíveis. O vídeo não demonstra quantas tentativas houve nem custo/licença de cada resultado.

**Lição para o res.** Aceitar uma decisão de alto nível do planejador é útil **somente** quando ela se transforma em operações rastreáveis: qual clipe, qual camada, qual intervalo, qual máscara, qual fonte gerada, qual revisão. “Aplique uma transição cinematográfica” não é um plano testável. O agente precisa devolver uma timeline auditável e aceitar reprovação por inconsistência visual. O tutorial não fornece prova de que geração automática seja confiável sem direção e inspeção.

## Proposta de registro para aprendizagem, ainda sem implementação

Uma futura ficha de técnica poderia ter os seguintes campos sem vincular o res a um fornecedor:

```yaml
technique_id: subject-occluded-typography
source_reel: https://www.instagram.com/creators/reel/DdwS-6oRvL8/
evidence: observed_timeline_and_caption
perceptual_intent: text_occupies_scene_depth_behind_subject
inputs: [base_video, subject_mask_or_segmentation, text_asset]
anchors: [subject_identity, frame_sync, text_baseline, depth_order]
operations: [duplicate_base, segment_subject, place_text, animate_position]
temporal_checks: [entry, foreground_crossing, exit]
failure_modes: [halo, mask_jitter, text_crosses_face, unreadable_on_phone]
audio_evidence: unverified
license_status: reference_only
```

O campo `evidence` impediria o sistema de confundir hipótese com passo demonstrado. A biblioteca de técnicas deve conter também **contraexemplos** do próprio res: packshot parado por sete segundos, fade entre layouts e zoom de fotografia não devem receber nota alta de ação/continuidade só porque movimentam pixels.

## Sequência de ensino sugerida para uma etapa posterior

1. **Anotação humana de poucos tutoriais de alta qualidade:** resultado, entradas, etapas, intermediários, falhas e grau de certeza. Este documento é um primeiro lote, não um dataset suficiente.
2. **Representação executável independente de fornecedor:** decompor técnica em materiais, camadas, transformações, intervalos e validações.
3. **Reprodução controlada em material próprio:** o res executa a técnica com outros assets e textos; não replica frames protegidos dos criadores.
4. **Avaliação cega:** comparar o efeito com a intenção declarada em reprodução normal, sem deixar o nome da técnica inflar a nota.
5. **Generalização:** repetir em três produtos distintos e num caso em que a técnica deve ser rejeitada por falta de pré-condições.

Até haver essa reprodução, as fichas são conhecimento editorial documentado, não capacidade autônoma comprovada.

## Fichas adicionais da expansão: passos vistos e lacunas

### Ficha 8 — troca de estado escondida por gesto

**Fonte:** [@creators / Ishift](https://www.instagram.com/creators/reel/Ddb0HfwRd93/). **Confiança:** alta para a necessidade de antes/depois, mão e alinhamento; média para parâmetros da transição.

**Procedimento observado:** mostrar o resultado de maquiagem; na parte de tutorial, preparar um plano pré-transição em que a mão cruza e cobre o rosto (~33 s); alinhar o rosto depois do gesto (~46 s); abrir o seletor e aplicar “Ishift” em vez de “Dissolve”, com duração visualmente curta (~57 s). O vídeo não mostrou números legíveis de alinhamento facial nem uma comparação A/B controlada dos presets.

**Contrato transferível:** duas fontes do mesmo sujeito, continuidade de escala/ângulo/luz, um gesto que tape a região transformada, corte no pico de cobertura. **Teste:** olhos, nariz, mandíbula e mão devem permanecer coerentes nos frames anterior e posterior; o espectador percebe transformação, não salto de pessoa ou câmera. Se não há gesto/oclusão, procurar outra técnica em vez de aplicar a marca de transição.

### Ficha 9 — janela recortada que percorre conteúdo com keyframes

**Fonte:** [@moonsol.design / travel dump](https://www.instagram.com/moonsol.design/reel/DSUcRaKAXYb/). **Confiança:** alta para recorte do centro, ordem visual das camadas e inserção de keyframes; baixa para curva e valores exatos.

**Procedimento observado:** preparar em Canva um cartão semelhante a uma ficha de local com uma região central vazia (~10 s); levar o elemento ao editor de vídeo; no fim da trilha, ajustar posição e criar outro keyframe (~24 s); a timeline mostra cartão e mídia subjacente em camadas e keyframes adicionais (~47 s). A ilusão vem de uma borda fixa e fotos/conteúdo que passam **atrás** dela. A legenda do autor resume o trabalho como muitos keyframes.

**Contrato transferível:** `camada superior = moldura com alfa`; `camada inferior = mídia deslocada por posição(t)`; o enquadramento da abertura pode ficar parado enquanto o conteúdo percorre um caminho. **Teste:** não pode vazar conteúdo fora da janela, deixar lacuna vazia no fim, cortar texto essencial ou mover a moldura involuntariamente. Uma automação deve armazenar cada keyframe e curva, não apenas “efeito de scroll”.

### Ficha 10 — inventário de camadas antes da animação

**Fontes:** [@moonsol.design / bolso](https://www.instagram.com/moonsol.design/reel/DdgvqW_oiBN/) e [@paulo.ia / objetos flutuantes](https://www.instagram.com/paulo.ia/reel/Dcy8nVrM7Wx/). **Confiança:** alta para a necessidade de referências separadas declarada no segundo Reel e para a colagem inicial vista no primeiro; média para como cada gerador executou o movimento.

**Procedimento mostrado/declarado:** a colagem do bolso apresenta fotos e objetos com profundidades distintas; o tutorial mostra a composição num editor e, depois, uma interface que pede movimento dos objetos salvos. Paulo declara ter separado imagens de cenário, objetos específicos, duas fichas de personagens e imagem inicial antes de gerar o vídeo. Isso é evidência de preparação, não prova de que o prompt sozinho manteve todos os objetos estáveis.

**Contrato transferível:** catálogo de objetos com IDs, referência visual, posição inicial, plano de profundidade, trajetória e comportamento quando o sujeito passa na frente. **Teste:** contar objetos por frame, verificar rótulos/logotipos reais, continuidade do personagem e ausência de colisões/oclusões erradas. Registrar qual asset foi usado em cada camada ou geração.

### Ficha 11 — fenômeno inserido em placa real

**Fontes:** [@paulo.ia / urso, flores e livros](https://www.instagram.com/paulo.ia/reel/DAD81xdOC8j/) e [@paulo.ia / campanha no quarto](https://www.instagram.com/paulo.ia/reel/DdHHUNrRCch/). **Confiança:** alta para o princípio de imagem de referência + ação concreta e para prompt visível; baixa para composição interna e número de tentativas.

**Procedimento observado:** anexar frame/imagem de referência numa interface; no primeiro tutorial, digitar uma ação como “A Giant cat jumps in the window” e gerar uma variante; no segundo, o prompt visível pede que objetos flutuem em gravidade zero enquanto o mesmo quarto ancora o resultado. As legendas citam ferramentas, mas o player não atribui todos os frames a uma só delas.

**Contrato transferível:** placa, referência de câmera e ambiente, objeto/evento, trajetória, ponto de entrada, escala, interação com superfícies, reação humana e área que não deve mudar. **Teste:** sombra/contato, oclusão, escala, fundo estável, objeto não metamorfoseia; comparar início e fim com a placa. O planejador precisa pedir um evento observável, não “efeito especial” genérico.

### Ficha 12 — layout contínuo dividido em painéis

**Fonte:** [@moonsol.design / carrossel musical](https://www.instagram.com/moonsol.design/reel/Ddlg5vgIeTv/). **Confiança:** alta para o cálculo da altura e largura total declarados no tutorial; média para todas as etapas de desenho.

**Procedimento observado:** criar canvas de **1350 px de altura** e **1080 px × número de slides** de largura (~11 s); colocar fotos e motivos gráficos em uma composição única; desenhar/ajustar elementos sobre a faixa contínua em outra interface (~30 s); mostrar os painéis finais. Notas musicais, linha curva e cartões atravessam limites entre painéis.

**Contrato transferível:** definir painéis e zonas seguras, alinhar elementos que cruzam emendas e exportar recortes coerentes. Para vídeo, o mesmo princípio pode virar um travelling ou sequência de painéis, mas essa transposição é **hipótese nossa**, não resultado que o Reel demonstrou. **Teste:** nenhum rosto/texto principal cortado nas emendas; linha atravessa sem salto.

### Ficha 13 — composição de Story em três faixas

**Fonte:** [@moonsol.design / café](https://www.instagram.com/moonsol.design/reel/Ddbbg3MIl6u/). **Confiança:** alta para as zonas visuais; média para a técnica exata de recorte.

**Procedimento observado:** uma foto de café em preto e branco é colocada e salva no editor de Story (~8 s); o resultado mostra fachada do estabelecimento acima, copos no centro e close/texture de café abaixo, com instrução para ajustar posição (~19 s). O Reel não esclarece completamente como cada recorte foi criado. Perguntas nos comentários demonstram essa lacuna de explicação, não uma resposta técnica.

**Contrato transferível:** zona 1 = lugar; zona 2 = objeto/uso; zona 3 = textura; pesos e contraste guiam leitura de cima para baixo. **Teste:** cada zona informa algo novo, assunto principal não fica coberto, e a montagem é legível no tamanho real de Story. A operação pertence a layout estático; para virar vídeo, cada faixa precisaria de temporalidade justificada.

### Ficha 14 — recorte e empilhamento de objetos reais

**Fonte:** [@moonsol.design / sanduíche](https://www.instagram.com/moonsol.design/reel/DdWc6kgIXPH/). **Confiança:** alta para abertura e ferramenta “Remove Background”; baixa para ordem completa dos ingredientes, não capturada na amostragem.

**Procedimento observado:** resultado inicial com rosto, câmera, calçado e telefone encaixados no sanduíche sobre prato e papel listrado; começo do tutorial em Picsart exibe fatia de pão recortada e controle de remoção de fundo (~11 s). A composição requer assets separados; a sequência completa de montagem ficou fora dos momentos amostrados.

**Contrato transferível:** recortes com contorno limpo, perspectiva e sombras compatíveis, ordem de profundidade que permita objetos saírem/entrarem entre ingredientes. **Teste:** halos, escala absurda involuntária, contatos sem sombra e objetos sem função. A excentricidade visual não basta para validar clareza da peça.

### Ficha 15 — fluxo exibido de Higgsfield, ainda sem qualificação

**Fonte:** [@moonsol.design / freeze motion](https://www.instagram.com/moonsol.design/reel/DdjIM_qo-jL/). **Confiança:** alta para a imagem de referência anexada e o texto “@ Higgsfield” na interface do ChatGPT (~11 s); baixa para o prompt integral, resultado em movimento e integração técnica.

**Procedimento observado:** partir de uma foto da pessoa numa rua; abrir o ChatGPT com a imagem anexada; digitar `@ Higgsfield` segundo o tutorial. O vídeo e a legenda chamam isso de plugin; não demonstram um MCP conectado ao res. **Teste futuro, se houver integração:** API/MCP real, licença, custo por tentativa, controle de identidade/câmera, duração, callback e reprodução com materiais próprios. Não promover o fornecedor com base nesta referência isolada.
