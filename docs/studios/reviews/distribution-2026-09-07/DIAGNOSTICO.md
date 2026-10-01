# Distribution — por que a produção do res ainda não atende

Revisão de 7 de setembro de 2026. Veredito do usuário: **produção reprovada**. Esta avaliação mantém a aprovação técnica dos testes como evidência de execução, sem convertê-la em aprovação criativa. Nenhum código de produção foi alterado nesta revisão.

## 1. De quem foi o vídeo

O MP4 foi composto e codificado pelos serviços reais do res: compilador de cenas, MotionGraph, HyperFrames e FFmpeg. Não foi uma montagem final feita externamente num editor para fingir capacidade.

**Mas o Codex escreveu o roteiro de cenas, as posições, durações, animações e os materiais procedurais do diagnóstico.** O script `backend/scripts/qualify_editorial_v2.py` invocou diretamente esses serviços. O planejador Gemini, a recuperação contextual de técnicas e a resolução autônoma de materiais não dirigiram essa peça. O teste separado de API/worker prova a integração do render; não muda a autoria do plano do diagnóstico.

Nos dois planos exportados há seis cenas, nenhuma narração, nenhum `techniqueId` e nenhum pedido em `materialNeeds`. O runner remove explicitamente a narração para permitir um diagnóstico visual separado. A versão curta de cada título também foi escrita previamente no runner.

Portanto, a conclusão correta é: **o executor funciona para algumas composições; a competência de produção autônoma continua sem demonstração.** A apresentação anterior ficou centrada na execução e não respondeu suficientemente ao objetivo de qualidade do produto. Este resultado não permite atribuir o fracasso ao Gemini, que não participou dele.

## 2. Comparação observada

Referência: [Distribution, @mep.io_](https://www.instagram.com/mep.io_/reel/DciIBRYBHBK/), 87 segundos. Produção res: 51 segundos, inicial e revisada. Os tempos abaixo são aproximações lidas do player. Comparei funções e escolhas, não o mesmo segundo em vídeos de durações e roteiros diferentes. Formato de tela não é o eixo desta análise.

| Função | Referência observada | Diagnóstico res | Consequência |
|---|---|---|---|
| Entrada | ~0,7 s: retrato ocupa o quadro e o título cruza o rosto | 0–7,4 s: título no alto, figura circular abstrata e cartão | O nosso não estabelece uma situação ou uma pergunta visual forte |
| Material específico | ~9,4 s: ciclismo, interface e cartões de produto; ~30,6 s: demonstração em palco | Uma imagem procedural reutilizada; figuras geométricas e palavras | Há poucos objetos com significado que sustentem a explicação |
| Mostrar a contradição | ~20,5 s: cabeça/cérebro junto a interface e contagem; ~24,2 s: contraposição tipográfica e figura; ~27,3 s: palavra-chave domina a tela | Títulos enunciam conclusões; cartões apresentam rótulos | Falta encenar a diferença entre ter uma ideia e fazê-la chegar a alguém |
| Hierarquia | Alterna personagem, palavra dominante, interface, composição dividida e mosaico | Título quase sempre na mesma posição; três cenas repetem cartões muito semelhantes | A estrutura de informação pouco evolui |
| Progressão | ~44,8 s: filmagem; ~48,1 s: blocos de logos; ~67,8 s: comparação em painéis; ~69,5 s: mosaico | Seis cenas com entradas rápidas e longas permanências | Há sucessão de telas, mas pouca ação explicativa dentro delas |
| Identidade | Branco/preto e azul recorrente, molduras, bordas coloridas e tratamento visual de materiais diferentes | Fundo escuro, verde, fonte e cartão uniformes | Consistência existe, mas faltam direção de arte e variedade de funções |
| Desfecho | ~78,2 s: perfil da produtora; a referência também promove seu trabalho | ~41–51 s: conclusão textual e reaproveitamento da composição inicial | Os objetivos não são idênticos; não devemos copiar sua parte promocional automaticamente |

A referência é uma montagem mista com filmagens, pessoas, interfaces e motion; não é apenas um conjunto de formas animadas. Também não é necessário usar celebridades ou esses mesmos arquivos para atingir riqueza visual. O que precisamos transferir é a função das escolhas: contraste, demonstração, hierarquia, transformação e continuidade.

Não identifiquei o software usado pelo autor. Aparência tridimensional, desfoque e bordas coloridas são observações do resultado; não comprovam um método específico de produção.

**Limite sonoro:** o player da referência estava mudo e não houve audição integral nesta análise. A exportação pelo recurso do navegador falhou. Não atribuo BPM, instrumentos, qualidade da voz, efeitos específicos nem sincronismo à referência. A comparação sonora abaixo se apoia exclusivamente no código e nos arquivos do res.

## 3. Por que nosso diagnóstico parece uma apresentação animada

### Ritmo sem evolução suficiente

A análise local dos MP4 encontrou pouca mudança visual em aproximadamente **82,5%** das amostras consecutivas da versão inicial e **81,3%** da revisada. Método: dez amostras por segundo, imagem em cinza de 160×90 e diferença média absoluta inferior a 0,5 numa escala de 0–255. Isso não mede qualidade nem atenção e pode ignorar pequenos movimentos.

Na versão inicial, os períodos quase estáticos incluem aproximadamente 1,4–7,4 s; 9,1–15,3 s; 17,3–24,2 s; 25,7–32,6 s; 34,1–41 s; e 42,4–50,9 s. A permanência pode ser adequada para leitura ou performance. Aqui, sem narração e sem uma demonstração se desenvolvendo, boa parte desses intervalos não acrescenta explicação.

As durações de 8, 9 e 10 segundos foram predefinidas no runner, não derivadas de uma voz medida. A maioria dos efeitos atua na entrada. O motor recebe uma chegada e um estado final; falta uma sequência de ações e consequências.

### Som de teste tratado como componente de produção

`tone()` produz uma base constante com três frequências, ruído de baixa amplitude para ambiente e um único sinal descendente de meio segundo para efeito. São materiais legítimos para verificar processamento, mas não constituem seleção musical ou desenho sonoro profissional. O mesmo efeito reaparece nas seis cenas com deslocamento fixo de 38 frames em relação ao elemento escolhido.

A existência de dezoito clips de áudio no recibo comprova mistura de trilhas, não adequação musical. Precisamos de seleção de trechos, função emocional/expositiva, curva de energia, momentos de entrada/saída, contraste, silêncio e sincronismo com eventos semânticos. Ter ducking também não resolve isso: ele controla a relação de nível com a fala, conforme a [documentação oficial do Premiere](https://helpx.adobe.com/premiere/desktop/add-audio-effects/adjust-volume-and-levels/automatically-duck-audio.html).

### Revisão localizada excessivamente mecânica

Em `revise_direction`, “mais calmo” multiplica tempos de keyframes/revelações por até 1,5; “menos texto” troca o texto por um trecho previamente fornecido; “mostrar melhor o produto” muda o encaixe para `contain`. Essas são operações úteis, mas estreitas.

A revisão deixa títulos como “Uma ideia” e “uma conexão.” Sem a narração, a explicação fica ainda mais dependente de inferência. Preservar literalmente duas conclusões não demonstra preservação de toda a mensagem. Uma revisão editorial precisa considerar voz, ação, carga de leitura e entendimento conjunto, além de preservar as cenas não afetadas.

## 4. Causas na arquitetura e no processo

| Camada | O que existe | O que falta ou não foi demonstrado |
|---|---|---|
| Direção | Adaptador, contexto, esquema V2 e chamada de planejamento | Ensaio real a partir de briefing; alternativas de conceito, storyboard e revisão do conceito antes do layout final |
| Repertório | Fichas, busca existente, ranking lexical com apoio da recuperação e versões | Exemplos executados com antes/depois, papel narrativo, materiais, custos e falhas; recuperação por problema editorial comprovada em produção |
| Percepção | Amostras por mudanças de cena e intervalos; lacunas declaradas | Leitura temporal e sonora suficiente para relacionar movimento, palavra, evento e resultado; inspeção complementar efetivamente fechando lacunas |
| Materiais | Catálogo, importação, fontes cadastradas, candidatos e jobs | Busca visual e semântica, seleção comparativa e aquisição/produção completando a necessidade até arquivo verificado; a peça não exercitou essa cadeia |
| Construção de cenas | Elementos, grupos, máscaras estáticas, caminhos e relações temporais | Representação explícita de estado inicial, ação, consequência, foco, informação adquirida e motivo da próxima cena |
| Motion | Keyframes, revelações, grupos e transições limitadas | Vocabulário coreografado e qualificado: antecipação, transferência, transformação, passagem de foco e movimento secundário com finalidade |
| Avaliação | Arquivo, fontes, overflow, intervalos, algumas relações e cobertura | Avaliação perceptiva da mensagem, composição, ritmo e som, com falha localizada e correção; campos audiovisuais ainda ficam pendentes |

Dois detalhes merecem prioridade na próxima implementação:

1. **Não confundir “posso executar agora” com “posso produzir o material necessário”.** O ranking filtra técnicas pelos tipos de material já presentes. Isso pode excluir uma solução pertinente antes de o planejador pedir a imagem ou filmagem que a viabilizaria. Precisamos separar técnicas prontas, técnicas viáveis após aquisição e técnicas sem execução disponível.
2. **Justificativa declarada não é comprovação.** O compilador copia verificações da cena para as operações e atribui `confidence=1`; o provedor declara IDs de camadas a partir do documento. Isso serve à rastreabilidade, mas não é confiança editorial calibrada nem prova perceptiva de que cada elemento comunicou o esperado.

O catálogo usa termos presentes no título, descrição e tags e retorna até cem resultados. Isso não equivale a reconhecer visualmente “a melhor imagem para demonstrar isolamento” ou resolver sinônimos, enquadramento, espaço para texto e direção do olhar. As bibliotecas são necessárias, mas precisam estar ligadas a decisões e à verificação de arquivos reais.

## 5. Duas lentes de diagnóstico

**Tradução visual — lente Villeneuve, aplicada por inferência.** A observação é que cartões nomeiam ideias que poderiam ser demonstradas. O princípio documentado é a ida do roteiro ao storyboard e a reescrita após descobrir as implicações visuais; isso está descrito na [conversa da DGA](https://www.dga.org/events/2024/may2024/duneparttwo_qna_0324). Decisão: fazer storyboard com estados e ações antes de gerar coordenadas. Efeito esperado: compreensão apoiada na imagem. Risco: acrescentar metáforas rebuscadas a um assunto simples.

**Estado do espectador e som — lente Peele, aplicada por inferência da skill, sem atribuir esta recomendação diretamente ao cineasta.** A observação é que não registramos o que cada cena faz o espectador descobrir e os sons são repetidos como marcação. Decisão: para cada momento, explicitar o que a pessoa sabe antes, o que muda e qual evento merece som. Efeito esperado: progressão e atenção motivada. Risco: exagerar suspense ou pontuação sonora num vídeo explicativo. Não é preciso importar linguagem de terror para usar esse raciocínio.

As duas análises convergem em uma direção: **desenhar ações explicativas e seu som antes de escolher efeitos decorativos**. A técnica de animação continua necessária: os [gráficos de valor e velocidade do After Effects](https://helpx.adobe.com/sg/after-effects/desktop/animate-in-after-effects/animation-basics/animation-basics.html) ilustram o controle temporal que deve existir na qualificação dos nossos componentes. Não há razão demonstrada para substituir HyperFrames/FFmpeg por outro renderizador neste momento.

## 6. Direcionamento recomendado

Manter o executor e investir primeiro na cadeia de produção verificável:

**Briefing → conceito visual → progressão narrativa → storyboard → necessidades de material → voz medida e mapa sonoro → animatic → composição → render → crítica audiovisual → revisão.**

Isso deve ocorrer em serviços do res, com artefatos persistidos e adapters por capacidade. Não exige dez agentes, vários modelos pagos ou outra plataforma de edição. Gemini pode ser o planejador principal, mas a escolha do provedor não deve substituir o processo de direção.

**Manter:** contratos V1/V2, filas, isolamento de clientes, checksums, render real, acervo e limites explícitos de capacidade.

**Mudar:** aceitação baseada principalmente em testes técnicos; recuperação que confunde falta atual de material com inviabilidade; revisão que apenas altera parâmetros; confusão entre fixture manual e produção autônoma.

**Construir:** conceito e storyboard verificáveis; aquisição até o arquivo; repertório com exemplos reais; mapa de eventos e som; avaliação audiovisual ligada a intervalos e correções. As fichas precisam de problema resolvido, pré-condições, estados, parâmetros, exemplo positivo, contraexemplo e resultado avaliado. O número de fichas isoladamente não mede conhecimento útil.

Para música e efeitos, iniciar um acervo pequeno e curado: trilhas com e sem voz, pontos de edição, energia por trecho, duração útil, timbre, função, restrições e prévia; efeitos categorizados por ação e intenção, não somente por nome. Seleção deve comparar candidatos e registrar por que o trecho foi escolhido. Compras ou geração não devem acontecer implicitamente.

Materiais visuais precisam de descrição de conteúdo e atributos úteis à composição: orientação, região livre, recorte/alpha, objeto focal, movimento, qualidade e coerência com a identidade. Um arquivo de logo serve como recurso; não informa sozinho o que fazer na cena. Cenários de motion podem ser espaços gráficos coerentes, sem exigir filmagem ou geração 3D.

## 7. Próximo ensaio: menor, mas verdadeiramente dirigido pelo produto

Antes de outra peça de 51 segundos, qualificar **12–15 segundos completos**, com voz e som reais. Objetivo de ensaio: mostrar que uma ideia precisa de um caminho até as pessoas. Abaixo há um exemplo de critério visual, não um JSON final que o Codex deva entregar pronto ao executor:

- Estado inicial: uma mensagem e três destinos visíveis, sem ligação; nada chega.
- Ação: um caminho é criado; a mensagem percorre o espaço e alcança um destino.
- Desenvolvimento: a mesma mensagem assume formas adequadas aos outros destinos, preservando sua identidade.
- Conclusão: o quadro aberto mostra o percurso e a ideia principal, sem inventar métricas de sucesso.
- Som proposto: pausa na ausência de conexão, efeito de percurso e chegada vinculado ao evento, trilha com função de continuidade; a escolha concreta depende da narração e da audição dos candidatos.

O **res** deverá propor ao menos duas abordagens, escolher com critérios explícitos, buscar ou pedir os materiais, produzir o storyboard/animatic, montar e registrar as avaliações. O Codex pode melhorar código, conectores e testes; não deve escrever o plano final desse ensaio para que ele conte como autonomia. Uma intervenção manual deve ser registrada e excluída desse critério.

Critérios de passagem:

1. Rodada iniciada pela API/interface a partir de briefing, roteiro e identidade, com evidência da chamada real do planejador e dos jobs de produção.
2. Cada cena mostra uma mudança explicativa; retirar a cena tem uma consequência identificável. Nenhum corte ou efeito é justificado apenas por uma palavra-chave.
3. Um avaliador consegue explicar o papel da distribuição; assistir sem áudio também permite perceber a relação visual principal. Esse teste precisa de observação humana, não de pontuação inventada pelo modelo.
4. Voz inteligível, material sonoro adequado e sincronismo ouvido integralmente. Sem narração utilizável, essa versão não passa.
5. Material ausente é resolvido ou solicitado de forma concreta, sem substituir silenciosamente por uma forma genérica.
6. A revisão “mais calmo e menos texto” melhora leitura e pausas sem eliminar informação necessária; alterações não relacionadas permanecem intactas.
7. O mesmo processo adapta outro tema/identidade. Um plano específico que só funciona para distribuição não qualifica produção contextual.

Somente depois desse ensaio aprovado expandir para 45–60 segundos e para novas combinações. A reprovação atual deve entrar como caso negativo no conjunto de avaliação: válido tecnicamente, insuficiente editorialmente. Atualizar esse conjunto e o repertório não equivale a treinar automaticamente o modelo.

## Evidências locais

- `evidence.json`: autoria, quadros observados, método, medidas e reprovação do usuário.
- `COMPARADOR.html`: reprodução local, intervalos clicáveis e mapa da distância entre objetivo e execução.
- Runner: `backend/scripts/qualify_editorial_v2.py`, linhas 25, 45, 127, 136, 339 e 381.
- Planejador: `backend/app/services/studios/gemini_editing.py`, linhas 422–452 e 494–515.
- Repertório: `backend/app/services/studios/editing_repertoire.py`, função `rank_repertoire`.
- Materiais: `backend/app/services/studios/editing_resources.py`, função `catalog`; `contextual_editing_v2.py`, `resolve_materials`.
- Revisão: `backend/app/services/studios/contextual_editing_v2.py`, função `revise_direction`.
- Avaliação: `backend/app/providers/studios/editorial_preflight.cjs`, `contextual_motion_render.py` e `backend/app/services/studios/video_render.py`.

Não houve audição da referência, nota estética objetiva, inferência causal de métricas, chamada paga ou nova produção de vídeo nesta revisão.
