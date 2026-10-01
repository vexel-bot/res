# Clicko Studios — revisão de UGC, motion e reconstrução do piloto Caio

Data: 04/09/2026, America/Sao_Paulo. Acesso final às fontes: 05/09/2026 UTC. Público: responsável pelo produto, direção criativa e engenharia. Workspace: `C:\Users\edugu\Downloads\res`; projeto no OneDrive intocado.

## Resposta direta

O piloto foi um **apresentador sintético animado**, não um anúncio construído pelo fluxo de edição UGC pretendido. Sora produziu a fonte visual ficcional de 12 segundos; MuseTalk aplicou a fala e estendeu a fonte por repetição bidirecional até 44,52 segundos. **HeyGem não criou esse avatar.** A voz veio de síntese local Chatterbox condicionada a uma referência autorizada. O usuário rejeitou voz, rosto, vídeo, cenário e edição; essa avaliação permanece válida, apesar da aprovação técnica de decodificação e transcrição.

A correção proposta é construir um anúncio a partir de **performance aprovada + demonstração verificável + montagem com função**. Geração por modelo entra apenas como fornecedor de um plano específico quando captura, interface ou motion não resolvem a necessidade. Não há motivo demonstrado para gerar outro anúncio inteiro ou trocar de API nesta etapa.

Evidência local: [execução do piloto](../../pilots/CLICKO_CAIO_LOCAL_CLONE_EXECUTION_2026-09-04.md), [script efetivo](../../../../backend/scripts/musetalk_fixed_camera_pilot.py) e [registro desta revisão](review-record.json). O SHA-256 do MP4 foi reconferido nesta pesquisa. Este relatório não altera estados operacionais, não publica mídia e não promove providers.

## 1. Alcance real da pesquisa

Esta é uma rodada comparativa focalizada, não a conclusão do corpus de 900 unidades.

- Quatro análises R1 existentes foram reutilizadas: duas de Paulo e duas de Mep. A aprovação global de R1 permanece preservada; cabeçalhos individuais antigos não representam uma nova reprovação.
- Houve reconferência visual pontual no navegador: Mep em aproximadamente 20 s e Paulo em aproximadamente 40 s. Não foi uma nova assistência integral dos Reels.
- Foram estudadas documentalmente seis famílias de projetos de motion/híbridos: Webflow, Spline, Twilio, Zapier, Headspace e Asana. Projetos e campanhas não equivalem a seis vídeos integralmente anotados.
- Goodcall e Skycop foram examinados como casos de desempenho declarado; The Social Savannah, como processo de produção e descoberta de formatos.
- Os players de BUCK e o portfólio incorporado de Savannah não forneceram reprodução verificável nesta sessão. Texto de produção, créditos e descrição de post não foram convertidos em timestamps inventados.
- O contact sheet local foi inspecionado em nove amostras de 0 a 44,48 s. Isso não substitui inspeção contínua de movimento nem audição. Não afirmo ter ouvido a voz nesta rodada; o julgamento auditivo negativo é do usuário.

Classificações utilizadas: **O** = observação direta limitada ao material visto; **D** = declaração da fonte ou registro técnico; **I** = inferência criativa; **H** = hipótese ainda não testada. Confiança na descrição de um processo não significa confiança na sua eficácia comercial.

Não foram baixados novos vídeos remotos, copiados anúncios para assets nem enviadas referências vocais a serviços. Capturas do navegador são evidência temporária de inspeção, não material de produção. URL pública não concede licença para reutilizar cenas, rostos, músicas ou interfaces de terceiros.

## 2. O que realmente foi produzido

| Etapa | Resultado confirmado | O que não aconteceu |
|---|---|---|
| Fonte do rosto | Sora, identidade ficcional, 12 s, 720 × 1280, sem áudio | Captura de apresentador real; modelo facial independente treinado no HeyGem |
| Voz | Chatterbox local, PT-BR, seis segmentos; WAV de 44,52 s | Aprovação humana de naturalidade; voz fornecida pelo Sora |
| Articulação | MuseTalk 1.5 local; adaptação de região facial para câmera fixa | Direção corporal vinculada à copy; renderer HeyGem |
| Extensão | 300 frames de fonte a 25 FPS, reutilizados em ciclo bidirecional | 44,52 s de atuação original contínua |
| Entrega | MP4 privado, 1.113 frames, H.264/AAC | Anúncio editorialmente montado com prova, inserts e motion |

A base teve uma operação paga, estimada em US$ 1,20. A fatura não foi consultada; nenhum gasto novo foi feito nesta rodada. Identificador e checksums estão no registro de execução citado acima, sem chaves de API.

As inversões de movimento ocorrem perto de 11,96, 23,92 e 35,88 s. O mecanismo está documentado no script; o quanto o público percebe cada inversão ainda requer observação contínua. A estabilidade do fundo é útil, mas não transforma movimentos repetidos em atuação intencional.

O [estudo local do HeyGem](../../knowledge/repositories/heygem-caladog.md) descreve cadastro a partir de vídeo e síntese com vídeo + áudio, não criação de pesos faciais independentes. O backend principal está em container externo. A auditoria mantém limitações de hardware e cadeia de fornecimento; não se assume que o HeyGem resolverá a qualidade. HeyGem e o serviço comercial HeyGen não devem ser tratados como o mesmo produto.

## 3. Diagnóstico dos cinco eixos

| Eixo | Evidência | Mecanismo de falha ou limite | Correção a validar |
|---|---|---|---|
| Voz | Rejeição humana; síntese em seis partes com intervalos fixos de 120 ms; ASR recupera o texto (D) | Completude lexical não mede timbre, intenção ou fluidez. Reinícios de prosódia entre segmentos são uma hipótese, não diagnóstico auditivo confirmado (H) | Casting local comparável à referência autorizada; direção por intenção; aprovação de trecho curto antes de síntese integral |
| Rosto | Close quase invariável, sem mãos; suavização de boca/barba nas amostras (O); animação concentrada na região facial (D) | Articulação não dirige olhar, corpo e reação. A aprovação estrutural anterior não foi aprovação estética (I) | Separar identidade, textura, atuação e lip-sync; avaliar base e resultado lado a lado, sem promover o rosto atual |
| Vídeo | 44,52 s de apresentador; nenhuma demonstração de produto no piloto (D/O amostral) | O espectador recebe uma lista de capacidades, mas não acompanha uma transformação verificável (I) | Um problema concreto, uma operação real, uma consequência observável |
| Cenário | Fundo cinza, camisa verde-petróleo, câmera fixa (O) | Fundo estável serve à prova de lip-sync, mas não fornece contexto de trabalho nem objetos relacionados à mensagem (I) | Espaço de agência autorizado ou interface como cenário; objetos usados em uma ação, não decoração genérica |
| Edição | Sem B-roll, motion, trilha, captions ou sequência de inserts, conforme escopo bruto anterior (D) | O laboratório de avatar foi confundido com capacidade de editar um anúncio. Não se trata apenas de adicionar efeitos (I) | Montagem orientada a argumento e evidência, com pontos de corte motivados pela fala/ação |

O primeiro escopo deliberadamente não incluía edição final. Portanto, sua ausência não é uma falha de execução desse requisito antigo. O erro foi tomar o bruto como aproximação suficiente do resultado criativo desejado e avançar sem aprovação perceptiva da voz e atuação.

### Onde a copy pede uma imagem e não a recebe

Timestamps abaixo vêm dos segmentos de síntese, não de alinhamento fonético.

| Intervalo | Função da fala existente | Informação visual que falta | Decisão editorial proposta (I) |
|---|---|---|---|
| 0–6,64 s | Acusa começar escolhendo cenas | Um problema reconhecível por uma agência | Abrir com uma mudança concreta de briefing; substituir a acusação universal por uma situação verificável |
| 6,76–16,08 s | Oferta, público e referências viram decisões soltas | Quais decisões se contradizem | Mostrar dois elementos de um projeto fictício de demonstração com uma incompatibilidade legível |
| 16,20–25,72 s | Nomeia Clicko e enumera etapas | O funcionamento do produto | Capturar uma operação realmente disponível, não uma tela fictícia apresentada como funcional |
| 25,84–30,36 s | Vincula decisão ao objetivo | O vínculo prometido | Exibir um vínculo auditável caso exista; se não existe, revisar a alegação |
| 30,48–40,96 s | Revisão e preservação de identidade | Uma correção antes/depois | Comparar duas versões do mesmo elemento; não inserir imagem de escritório por palavra-chave |
| 41,08–44,52 s | Solicitar acesso ao piloto | Marca, destino e próxima ação legíveis | Fechar com CTA visível e falado, sem prometer acesso imediato ou resultado comercial não comprovado |

Não basta desenhar uma interface convincente para suprir a prova. Um storyboard conceitual deve estar identificado como tal. O produto aparecer pela primeira vez na fala a 16,20 s é um dado do piloto, não prova de que esse instante causaria abandono.

## 4. Referências: técnica, transferência e contraexemplo

### 4.1 Paulo e Mep — conhecimento R1 reaproveitado

**Paulo — tutorial de depth map, 90,667 s.** A análise R1 registra entrada → representação de profundidade → composição → resultado, com apresentador e demonstração. A amostra reconferida perto de 40 s mostra o rosto abaixo de um exemplo visual. Transferência: quando o Clicko disser que organiza uma decisão, mostrar a entrada, a intervenção e a saída. Contraexemplo: rosto explicando a ferramenta durante toda a peça enquanto a única prova é verbal. Não reutilizar os inserts cinematográficos do Reel em publicidade. [Fonte](https://www.instagram.com/reel/DcuHK9ChRrP/) · [análise existente](../../knowledge/corpus/instagram-DcuHK9ChRrP/analysis.md).

**Paulo — precauções com deepfake, 40,8 s.** R1 registra continuidade de cenário e transformação facial usada para demonstrar o assunto. Transferência: a técnica precisa tornar o argumento observável; não basta mostrar que o sistema consegue gerar um rosto. Limitação: demonstração de risco de identidade não autoriza replicar pessoas nem comprova eficácia de anúncio. [Fonte](https://www.instagram.com/reel/DTRBJoOAUl1/) · [análise existente](../../knowledge/corpus/instagram-DTRBJoOAUl1/analysis.md).

**Mep — anatomia de um vídeo, 87,792 s.** R1 descreve o vídeo dentro de uma timeline com funções narrativas localizadas. A amostra perto de 20 s confirma a composição anotada; a tentativa posterior de seek para 55 s exibiu frame aparentemente stale e foi descartada como evidência temporal. Transferência: tornar revisão, sequência e dependências visíveis. Contraexemplo: jogar palavras como hook e CTA em tela sem relação com a ação mostrada. [Fonte](https://www.instagram.com/reel/DcsuFSGhnlw/) · [análise existente](../../knowledge/corpus/instagram-DcsuFSGhnlw/analysis.md).

**Mep — distribuição, 87 s.** R1 descreve problema, prova, framework e CTA com cards e montagem. Transferência: reservar a cada bloco uma pergunta respondida e uma mudança de informação. Limitação: densidade de cards pode exigir mais atenção do que um público frio concede; não copiar o pacote visual como receita. [Fonte](https://www.instagram.com/reel/DciIBRYBHBK/) · [análise existente](../../knowledge/corpus/instagram-DciIBRYBHBK/analysis.md).

Esses exemplos ensinam gramática, não garantem performance. A legenda de Mep atribui ao vídeo anterior ganho de seguidores; isso é autorrelato sem analytics verificado. Números que aparecem dentro do próprio vídeo não devem ser confundidos com métricas atuais do post.

### 4.2 Motion e formatos híbridos — fontes de produção, não análises integrais novas

**BUCK / MyHeadspace.** O estúdio descreve pessoas reais, suas experiências e animação geométrica integrada às histórias. É campanha produzida com depoimentos, não prova de UGC espontâneo. Inferência transferível: preservar o sujeito humano enquanto o motion explica uma experiência. Contrapeso: Caio ficcional não pode ser apresentado como cliente que viveu um resultado. Fotografia de Jonathan Wang; montagem de Billy Kostka, Cameron Kelly e Peter Brandi, entre outros créditos. Sem métricas comerciais disponíveis na página. [Case oficial](https://buck.co/work/headspace-members).

**BUCK / Asana Silos.** A produção usa silos em CGI compostos sobre material filmado para representar isolamento, depois passa à interface do produto. A página distingue manifesto de 30 s e derivações de 15 s; cita montagem de Billy Kostka e Rick Wilson e som de Malfred Sound. Inferência: uma cena especial merece existir se transforma um problema abstrato em ação compreensível e conduz à prova. Não copiar os silos nem confundir CGI com geração por IA. Sem resultado de campanha divulgado. [Case oficial](https://buck.co/work/asana-silos).

**BUCK / Zapier Motion Library.** A campanha documenta seis peças, com metáforas distintas para situações de trabalho. Há relações entre organização, tempo e transformação; o ponto é a ligação entre conceito e produto. Inferência: definir uma regra visual por conceito e variar campanhas, não trocar de estética a cada frase de um mesmo anúncio. Contraexemplo: animação bonita sem significado verificável. Não foram medidas durações de planos nem desempenho. [Case oficial](https://buck.co/work/zapier-motion-library).

**Ordinary Folk / Webflow: A New Era of No-Code.** A página informa 1:44, 2D/3D e continuidade de linguagem com trabalho anterior. Créditos separam roteiro de Julie Rybarczyk, direção de Jorge R. Canedo E., arte de Grace Pedersen, animação de Greg Stewart e som de Ambrose Yu. Inferência: modelar dependências do produto com linguagem visual consistente. Não transpor duração e densidade de filme de conferência para anúncio frio. A página marca 2022, mas o texto fala da conferência de 2021; data de estreia não resolvida. [Projeto](https://www.ordinaryfolk.co/project/webflow-a-new-era-of-no-code).

**Ordinary Folk / Introducing Spline.** A equipe declara ter aprendido e usado Spline para criar a peça; página informa 1:25, 2022. Inferência: usar o próprio processo do produto como prova, em vez de um manifesto genérico de inovação. Aplicação possível: demonstrar uma edição realizada no Clicko, desde que o caminho seja realmente reproduzível. O case não comprova conversão nem autoriza afirmar capacidades atuais da ferramenta a partir de material de 2022. [Projeto](https://www.ordinaryfolk.co/project/introducing-spline).

**Ordinary Folk / Twilio CEP.** A fonte descreve personagens e elementos 3D para representar relações humanas; duração publicada de 1:41, 2022. Roteiro de Kris Cantrell, locução de Thomas A. Aglio Jr. e som de Ambrose Yu. Inferência: representar consequências para pessoas, não apenas caixas abstratas de software. Contrapeso: personagens exigem intenção e ação; avatar que recita termos não é demonstração de relacionamento. [Projeto](https://www.ordinaryfolk.co/project/twilio-cep).

### 4.3 UGC publicitário e processo de testes

**Goodcall / TikTok.** Caso B2B relevante: a plataforma relata creators, peças de 15–30 s, Spark Ads e segmentação. Publica CAC de US$ 185 para US$ 7 e retenção de novos clientes de 75%. Esta última **não é retenção do vídeo**. O próprio texto associa a queda de custo à segmentação; não é teste isolado de edição. Inferência útil: testar mensagem, criativo e audiência com rastreabilidade. Não projetar o CAC para o Clicko nem impor 30 s como duração universal. [Case oficial](https://ads.tiktok.com/business/en-US/inspiration/goodcall-drives-signups-with-spark-ads).

**Skycop / Rock Paper Marketing.** A agência relata produção combinada de UGC e motion, localização e testes de hooks/mensagens. É evidência do processo declarado, não auditoria independente. A soma dos leads detalhados é 58.264, enquanto o cabeçalho diz 60.000+; o gasto detalhado e o agregado também diferem. Período, arredondamento ou atualização podem explicar, mas isso não está resolvido. Não usar esses totais como benchmark confiável do Clicko. [Case da agência](https://rockpapermarketing.io/case-studies/skycop).

**The Social Savannah.** O processo publicado separa filmagem por creators/atores, edição, revisão e iteração com dashboards. O portfólio Apps contém descrição de composição entre apresentador, gravação de tela e telefone; o player não foi validado. Inferência: capturar cobertura para montagem, não esperar que uma única tomada frontal contenha todo o anúncio. Alegações de melhores formatos e depoimentos de clientes não são comparação controlada. [Processo](https://thesocialsavannah.com/) · [portfólio Apps](https://thesocialsavannah.com/ad-examples/apps).

**TikTok Creative Codes.** Recomenda estrutura hook–corpo–fechamento, vídeo vertical, área segura e uso intencional de som e edição. As pesquisas citadas incluem estudos de 2020–2022; uma delas analisa 3.500 anúncios de 2021. São referências históricas de plataforma, não medição atual do Instagram nem previsão de resultado deste piloto. [Guia e fontes](https://ads.tiktok.com/business/en/blog/creative-best-practices-top-performing-ads).

## 5. Comparação de performance sem inventar métricas

Hoje podemos comparar **execução criativa**, não conversão. O piloto permaneceu privado: não há impressão, retenção, CTR, CPA ou venda atribuída para confrontar com campanhas publicadas.

| Pergunta | Piloto | Evidência de referência | Conclusão permitida |
|---|---|---|---|
| Há prova visual do mecanismo? | Não no bruto | R1 Paulo/Mep descreve transformações e estruturas visíveis | Existe uma lacuna editorial concreta |
| O cenário participa da mensagem? | Fundo neutro e invariável | Asana documenta metáfora espacial; Mep usa timeline | Há alternativas funcionais a estudar, não obrigação de cenário complexo |
| A atuação sustenta a fala? | Face animada, corpo herdado e cíclico; rejeição humana | Headspace registra pessoas e jornadas reais | A origem da performance é diferente; não há nota comparativa objetiva de naturalidade |
| Motion melhora compreensão? | Não aplicado | Cases documentam aplicações explicativas | Hipótese testável, sem promessa de ganho percentual |
| O anúncio converte melhor? | Sem campanha | Resultados agregados e autorrelatados de terceiros | Não comparável com os dados atuais |

Não usar curtidas absolutas para escolher os dez melhores; não chamar retenção de clientes de watch time; não atribuir resultado do tráfego apenas à montagem.

### Protocolo futuro de medição

Antes da publicação: três revisores, exibição em celular, uma passagem sem som e outra com som. Cada um identifica público, problema, operação demonstrada e CTA; marca timestamps de confusão e artefatos. Meta interna proposta: os três compreendem promessa e ação, sem falha crítica de voz/rosto. Isso é critério de aceitação, não estatística de mercado.

Após autorização separada de mídia: comparação controlada com objetivo, audiência, posicionamento, janela e atribuição equivalentes. Registrar impressões, inícios qualificados de reprodução, alcance em 3 s, conclusão, cliques de saída e conversões qualificadas, usando as definições reais exportadas da plataforma. Não misturar denominadores. Definir amostra e regra de decisão a partir do baseline e orçamento, hoje ausentes. Não iniciar campanha como parte desta pesquisa.

## 6. Conselho criativo — duas lentes, sem simular pessoas

Aplicações abaixo são **inferências operacionais** dos perfis locais, não opiniões pronunciadas por cineastas nem alegações de que eles conceberiam este anúncio.

### Lente de precisão comportamental — Fincher

- Observação: o apresentador descreve controle, mas não executa ação controlável; repetição corporal não acrescenta informação.
- Princípio operacional: tratar a cena como procedimento com mudança observável.
- Decisão: escolher uma única alteração de projeto; mostrar estado anterior, decisão e consequência. Dirigir olhar e pausa para a evidência, em vez de pedir genericamente uma atuação natural.
- Efeito pretendido: o espectador verifica o argumento.
- Risco: excesso de procedimento e rigidez retirarem calor humano. Remover detalhes que não mudam a compreensão.

### Lente de clareza para o espectador — Spielberg

- Observação: há vários conceitos abstratos antes de uma situação concreta que importe a alguém.
- Princípio operacional: definir onde o espectador olha, o que espera e qual revelação muda seu entendimento.
- Decisão: abrir com um pedido de revisão reconhecível por uma agência e uma reação contida; revelar depois a operação que resolve aquele caso.
- Efeito pretendido: reconhecimento antes da explicação.
- Risco: reação teatral, música sentimental ou falsa solução. A ação deve justificar o sentimento.

Perfis consultados: [Fincher](C:/Users/edugu/.codex/skills/cinematic-mind-council/references/profiles/david-fincher.md) e [Spielberg](C:/Users/edugu/.codex/skills/cinematic-mind-council/references/profiles/steven-spielberg.md). O conselho levou à escolha de **demonstração procedural com presença humana**, não espetáculo cinematográfico. Roteiro, direção, fotografia, montagem e som mantêm responsabilidades separadas.

## 7. Direção única para a próxima pré-produção

**Objetivo:** agências entenderem uma operação verificável do Clicko Studios e solicitarem acesso ao piloto. **Emoção:** reconhecimento seguido de confiança informada. **Gramática dominante:** apresentador em linguagem UGC + demonstração. **Apoios:** anotações motion funcionais e comparação antes/depois. Caio é porta-voz ficcional, não consumidor dando depoimento.

### Manter

- Projeto privado, voz local e referências autorizadas.
- Uma identidade consistente, se uma versão for posteriormente aprovada.
- Fonte imutável, checksums, histórico e vínculo entre revisão e render.
- CTA de solicitação de acesso, sem promessa de conversão ou volume.

### Mudar

- Sair da enumeração de etapas para um caso de uso demonstrável.
- Definir a ação do apresentador antes de escolher ou produzir a tomada.
- Dar duração ao plano conforme informação, fala e gesto; não usar grade de três segundos.
- Usar som para orientar ações e transições, não cobrir uma voz ruim.

### Reconstruir

- Casting e direção de voz; amostra facial de atuação; cenário contextual; mapa argumento–prova; montagem.
- Não promover o bruto rejeitado por simplesmente adicionar captions, zoom e música.

### Cartões de cena para o paper edit — não são roteiro final aprovado

| Cartão | Estado do espectador e ação | Material preferido | Função de edição/som | Dependência |
|---|---|---|---|---|
| A — Pedido | Reconhece uma revisão concreta de oferta | Apresentador aprovado junto a tela ou documento de demonstração | Começar pela ação; pausa de reconhecimento, sem alarme genérico | Performance e situação aprovadas |
| B — Contradição | Vê o que deixou de fazer sentido | Dois elementos reais do mesmo projeto de teste | Corte de relação; rótulos apontam diferença, sem chuva de palavras | Evidência legível e sem dados privados |
| C — Operação | Entende o que o Clicko efetivamente faz | Captura original de uma função comprovada | Reenquadrar para o alvo; cursor e fala apontam o mesmo objeto | Validação funcional, não só mockup |
| D — Consequência | Confere a mudança | Antes/depois com referência ao mesmo objeto | Comparação estável; motion só destaca o vínculo | Resultado reproduzível |
| E — Convite | Sabe para quem é e como pedir acesso | Retorno ao apresentador + CTA | Finalização vocal sem pressa; card legível | Destino de solicitação validado |

Nenhum cartão exige geração por IA por padrão. Se um conceito futuro realmente precisar de plano gerado, especificar: função, estado de entrada e saída, sujeito autorizado/ficcional, ação, câmera, luz, continuidade, restrições, duração motivada, custo e critério de rejeição. Não pedir ao gerador que invente o argumento nem que simule resultados da interface.

### Voz: aprovação antes de outro render longo

1. Preservar os arquivos autorizados e escolher referência com fala limpa, sem música, imitação forçada ou efeitos. Não identificar o locutor como celebridade sem evidência.
2. Preparar um trecho original de 8–12 s contendo marca, frase explicativa e convite, com intenção e palavras de ênfase explícitas. Intervalo é proposta de teste, não duração final do anúncio.
3. Comparar poucos candidatos locais sob a mesma frase e volume de reprodução, mantendo referência original para comparação de timbre. Uma semelhança de timbre não basta: exigir atuação apropriada à mensagem.
4. Anotar por timestamp dicção, acento, respiração, ritmo, continuidade entre frases e pronúncia de Clicko. Não corrigir fala ruim por aceleração automática ou música.
5. Aprovar por audição humana; depois produzir a fala integral e medir a duração natural. Se falhar, revisar fonte, texto e direção antes de parâmetros do modelo.

### Rosto, performance e cenário: gates separados

Primeiro aprovar a identidade-base. Depois comparar base e amostra animada com o mesmo trecho de áudio. Observar dentes, lábios, barba, olhos, piscadas, textura, junção rosto/pescoço e coerência entre emoção vocal e expressão. Avaliar o movimento continuamente, não apenas nove frames.

Não usar loop bidirecional como substituto de atuação longa. O limite anterior de uma fonte de 12 s deve aparecer como restrição explícita; não se resolve escondendo repetição ou submetendo uma segunda geração sem decisão. Uma nova fonte autorizada com cobertura apropriada pode ser necessária — ainda não está selecionada nem produzida.

Para cenário real, preservar geometria e regiões autorizadas. Para cenário original, definir posição de apresentador, tela, objeto manipulado, direção da luz e profundidade antes da produção. Para extensão híbrida, testar perspectiva, oclusão, bordas e sombras. O próximo corte não precisa de ambiente luxuoso: precisa de um ambiente que explique o trabalho.

## 8. O que o código atual permite — e onde falta integração

Revisão estática de [FFmpegUgcVideoRenderProvider](../../../../backend/app/providers/studios/video_render.py), especialmente `_validate_snapshot` e `_plan`. Não houve execução da suíte nesta rodada; existência de testes não equivale a resultado atual de teste.

| Capacidade | Evidência atual | Implicação |
|---|---|---|
| Montagem entre fontes | Até oito fontes visuais, uma track de vídeo, clips contíguos, até 128 clips | Já existe base para corte entre apresentador e demonstração |
| Reconform e controles | Faixas de origem, fit/anchor, limites de duração e validação de áudio pareado | Usar timeline canônica, não script ad hoc como anúncio final |
| Texto e captions | Texto/retângulos e uma track de legendas, com subconjunto restrito | Anotações básicas possíveis; raio e ênfase têm limitações declaradas |
| Áudio adicional | Categorias governadas de som natural e música licenciada, com ganhos/fades | Não afirmar que aceita narração externa arbitrária: categoria de voz não foi admitida nesse conjunto |
| Motion e composição avançada | Recusa video effects/keyframes, múltiplas tracks visuais e transforms fora do subconjunto | Split-screen, recorte de apresentador e motion livre não estão comprovados nesse provider |
| Proveniência de fontes | Requer `source=user-upload` e `originalPreserved=true` | Não etiquetar asset Sora como upload humano para passar validação; precisa de admissão fiel à origem |

Há limite agregado de nove assets, que restringe combinações de muitas fontes com áudio adicional. Reutilização de ranges sobrepostos da mesma fonte é recusada. Esses detalhes precisam ser considerados antes de prometer uma montagem executável.

O [ADR-009](../../adr/ADR-009-frame-exact-ugc-render-and-review-binding.md) documenta um primeiro escopo de fonte única; o código atual já é multi-source. Essa divergência fica registrada aqui, sem sobrescrever o ADR histórico. Há também provider HyperFrames; esta revisão não demonstrou que seu caminho entregue o híbrido completo desejado.

Testes encontrados: [FFmpeg UGC](../../../../backend/tests/test_ffmpeg_ugc_video_render_provider.py) e [áudio governado](../../../../backend/tests/test_natural_sound_render.py). Próxima implementação, se autorizada, deve verificar o caminho real de ingest → timeline → render → revisão, preservar proveniência de material sintético e não contornar direitos ou enums existentes.

## 9. Ordem de retomada e critérios de parada

1. **Produto/prova:** selecionar uma única função que possa ser demonstrada na versão real. Saída: cadeia alegação → evidência → ação. Sem prova, revisar promessa.
2. **Casting/performance:** aprovar trecho vocal e identidade separadamente; depois amostra conjunta curta. Sem aprovação, não renderizar anúncio integral.
3. **Pré-produção editorial:** escrever copy, cartões de cena, materiais e som; aprovar storyboard/animatic. Sem cobertura suficiente, não usar loop como solução silenciosa.
4. **Integração técnica:** provar admissão e render dos materiais no fluxo canônico. Recursos não suportados permanecem bloqueados ou precisam de implementação isolada e testada.
5. **Rough cut:** montar apresentador + prova + anotação, preservando fontes. Geração de cena apenas se houver necessidade documentada e autorização específica.
6. **Revisão:** avaliar os cinco eixos e vínculo versão/checksum. Publicação exige autorização posterior.

Critérios de rejeição imediata: rosto/voz reprovados; cenário sem função; fala com promessa sem prova; B-roll escolhido só por palavra-chave; motion que não explica relação; loop involuntário de atuação; mídia sintética registrada como humana; render diferente da versão aprovada.

**Nenhum desses passos futuros é declarado concluído por este relatório.** As 900 unidades, audição integral, comparação paga e benchmark HeyGem seguem fora da evidência desta rodada. A pesquisa encerra a rodada documental porque novos cases semelhantes não resolveriam as lacunas decisivas: performance aprovada, prova do produto e composição validada.

## 10. Lacunas e rastreabilidade

| Lacuna | Estado | Próxima evidência necessária |
|---|---|---|
| Vídeos novos de referência integralmente anotados | Não concluído nesta rodada | Player acessível, observação temporal e audição, sem contornar controles de acesso |
| Melhor formato por conversão para Clicko | Desconhecido | Campanha autorizada com métricas comparáveis |
| Causa perceptiva exata da voz ruim | Rejeição confirmada; causa não isolada | Audição comparativa localizada por timestamp |
| Nova identidade/atuação de Caio | Não aprovada | Avaliação de fonte e amostra conjunta |
| HeyGem superior ao MuseTalk neste caso | Não demonstrado | Benchmark mesmo input, condições e custo; licenças/hardware revisados |
| Híbrido no fluxo de produção | Não comprovado nesta rodada | Teste end-to-end da composição exata |

Fontes, classificações, datas e limites constam no [ledger de afirmações](claim-source-ledger.json). O [resumo de leitura](README.md) aponta a decisão e os arquivos principais. Nenhuma alteração foi feita em código de produção, chaves, modelos globais, ledgers históricos ou no projeto OneDrive.
