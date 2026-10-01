# Café Aurora versus referências — diagnóstico e próximas perguntas

**Missão desta rodada:** pesquisar e documentar. Este relatório não promove nenhuma integração, não escolhe provedor e não substitui a revisão humana dos animatics. Fontes: [caderno dos 15 Reels](./INSTAGRAM_EDITING_VIEWING_LOG_2026-09-30.md), [gramática observada](./INSTAGRAM_EDITING_GRAMMAR_2026-09-30.md), [tutoriais operacionalizados](./INSTAGRAM_TUTORIAL_WORKFLOWS_2026-09-30.md) e os artefatos locais do [piloto Aurora](../../../output/hybrid-aurora-pilot/README.md).

**Atualização de escopo após a expansão:** Aurora é somente um caso de diagnóstico do sistema. A análise de [30 Reels inéditos](./INSTAGRAM_EDITING_VIEWING_LOG_EXPANSION_2026-09-30.md) e o [modelo de conhecimento transferível](./INSTAGRAM_EDITING_KNOWLEDGE_MODEL_2026-09-30.md) definem a direção geral: aprender operações, pré-condições, evidências e resultados entre briefs diferentes. Nenhuma conclusão deste documento específico deve virar regra exclusiva para café ou para um vídeo de 15 segundos.

## O que o piloto atual efetivamente demonstra

Os arquivos locais `output/hybrid-aurora-pilot/animatic-g.mp4` e `animatic-h.mp4` têm 15 s, 720 × 1280 e 450 frames, segundo `pilot-evaluation.json`. A avaliação registra **8 s de filmagem com movimento** em ambos, render técnico aprovado, revisão visual humana pendente e autonomia parcial. O planejador não produziu uma direção aceita pelo contrato; as versões foram dirigidas pelo agente. A tentativa de geração de vídeo e a de música não renderam material utilizável por HTTP 429. O produto real utilizado tem baixa resolução e licença comercial pendente. Esses fatos impedem chamar o resultado de edição autônoma ou peça final aprovada.

Os contatos `contact-g.jpg` e `contact-h.jpg` permitem ver o arco visual: grãos sobre bancada, água entrando em filtro, bebida servida, depois embalagem fixa sobre o mesmo take até o fim. Na variante H, o packshot já ocupa essencialmente a mesma região dos quadros de 8,5 a 14,5 s; a chamada troca texto, mas não há novo gesto de produto, novo ponto de vista ou payoff visual. A imagem real da embalagem tem escala reduzida em relação ao quadro, e o recipiente escuro do take compete com ela na parte superior. A crítica do usuário — “parece só juntar peças de banco” — é compatível com essa evidência visual.

Não há nada tecnicamente errado em usar banco de vídeo. O problema visível é que os planos parecem **fontes independentes**: grãos, filtro e servir mudam de ambiente, óptica e materialidade sem uma âncora preparada no corte; a marca chega depois como cartão superposto, em vez de participar do acontecimento. O sistema cumpriu uma regra quantitativa de ação nos primeiros 8 s, mas não demonstrou uma gramática de continuidade e transformação.

## Comparação de mecanismos

| Pergunta editorial | No Aurora H observado | Referência que ensina o mecanismo | Lacuna de aprendizagem |
|---|---|---|---|
| O que persiste de um plano ao outro? | categoria “café”, porém não uma xícara/mão/objeto identificável entre takes | [Messi/Yamal](https://www.instagram.com/paulo.ia/reel/Da-sXkcRpSS/) preserva posição e dupla; [podcast](https://www.instagram.com/paulo.ia/reel/DdRkmq4M_7e/) preserva dupla e barco | selecionar e registrar uma âncora de continuidade antes de adquirir materiais |
| Por que acontece o corte? | troca de fase genérica: grãos → filtro → servir | [Magritte](https://www.instagram.com/paulo.ia/reel/DdpXHPksYVm/) faz olhar → entrar → revelar → tornar-se imagem | declarar informação nova e causa de cada passagem |
| Há interação entre gráfico e filmagem? | embalagem como cartão sobreposto, texto estável pequeno | [texto atrás da pessoa](https://www.instagram.com/creators/reel/DdwS-6oRvL8/) usa três planos; [cutout](https://www.instagram.com/creators/reel/Dd4dfPnRkgb/) atravessa moldura | planejar profundidade, oclusão, gesto e legibilidade antes do render |
| O produto causa algo? | surge aos 8 s e permanece | [doodle → café](https://www.instagram.com/moonsol.design/reel/Dd3k4cBtFrK/) faz forma virar objeto; [raio X](https://www.instagram.com/moonsol.design/reel/Ddv4nmHIsWI/) revela camada interna | transformar o produto numa consequência de ação, sem sintetizar marca errada |
| Há mundo visual único? | takes de banco com luz/fundo distintos; packshot de outra origem | [chamada da TV](https://www.instagram.com/paulo.ia/reel/DdZ6dY-M12g/) começa com metáfora e direção de arte; [colagem](https://www.instagram.com/moonsol.design/reel/DdwecRoI4Bf/) cria superfície comum | definir cenário, paleta, óptica, textura e regras de composição antes dos assets |
| O final responde à abertura? | chamada textual final sobre o mesmo take | [Magritte](https://www.instagram.com/paulo.ia/reel/DdpXHPksYVm/) fecha o motivo da maçã; [podcast](https://www.instagram.com/paulo.ia/reel/DdRkmq4M_7e/) retorna à moldura inicial | construir payoff visual, não somente CTA |

## O que pode ser aprendido primeiro, sem apostar numa nova ferramenta

Há quatro capacidades conceituais prioritárias. Esta lista é **agenda de pesquisa/prototipagem posterior**, não solicitação de implementação nesta rodada.

1. **Continuidade rastreável.** Para cada corte, identificar âncora de forma/posição/direção/personagem/objeto, estado antes e depois e frame de passagem. O sistema deve poder responder “o que o espectador reconhece como o mesmo?”.
2. **Material condicionado à montagem.** Em vez de buscar “café cinematográfico”, buscar/gravar/gerar “mesma xícara, mão entrando pela direita, luz quente, plano detalhe, movimento para baixo, duração útil de 1,5 s”. Se a fonte não atende ao encaixe, rejeitar o material, mesmo que bonito.
3. **Composição temporal em profundidade.** Recorte, máscara, placa limpa e keyframes devem ser planejados como intervalos; qualificar bordas e oclusões nos frames intermediários. Não basta medir geometria média ou diferença de pixels.
4. **Direção de arte do mundo.** Definir como tudo se relaciona: superfície, cor, luz, textura, lente, escala, tipografia, embalagem real e contato físico. A direção deve anteceder aquisição e geração.

Essas capacidades podem usar Remotion/FFmpeg, geração de imagem, captura própria ou APIs futuras. A observação dos tutoriais não autoriza concluir que o res precise abandonar a stack atual.

## Experimentos que realmente diferenciariam o diagnóstico

Uma rodada seguinte pode comparar **três versões de 15 s com os mesmos materiais e o mesmo orçamento**, mudando uma variável editorial de cada vez:

| Versão | Hipótese | Prova esperada | Reprovação clara |
|---|---|---|---|
| A: continuidade de ação | cortes motivados por mãos/fluxo/líquido criam unidade sem VFX novo | um gesto passa de plano geral para detalhe preservando direção e objeto | continuidade espacial contraditória ou mesmo “catálogo de café” |
| B: transformação localizada | placa limpa + traço/grão/vapor que revela a embalagem real cria causalidade | transição perceptível sem deformar rótulo; produto participa do acontecimento | máscara/registro fracos ou embalagem parecendo sticker |
| C: mundo editorial | superfícies, luz, sombra e tipografia com regras próprias integram fontes heterogêneas | peças parecem da mesma campanha em vez de três bancos | estética bonita porém ainda sem ação e payoff |

As três devem ser vistas completas em velocidade normal, sem mostrar antes o roteiro/legenda ao avaliador. Medir ao menos: clareza do objeto, continuidade, ritmo, qualidade de máscara, plausibilidade do produto, leitura em celular e sensação de unidade. Observar abertura, transições e final em movimento, além de frames amostrados. Uma avaliação separada de áudio será necessária; os Reels desta pesquisa estavam mudos no player.

## Higgsfield MCP: decisão adiada com critério explícito

O usuário levantou Higgsfield como possibilidade **a definir após a análise**. Os vídeos observados não justificam, por si, instalar um MCP específico. Parte do que impressiona vem de edição manual, seleção de imagens, recorte, direção de arte e roteiro. O caso [Messi/Yamal](https://www.instagram.com/paulo.ia/reel/Da-sXkcRpSS/) declara explicitamente ausência de IA de vídeo.

Antes de decidir fornecedor, uma prova comparativa deveria responder:

1. **Problema concreto:** falta de filmagem de uma ação específica? Falta de continuidade de personagem/produto? Ou incapacidade do editor atual de compor material já disponível? Um gerador só ajuda nas duas primeiras perguntas se entregar tomadas úteis.
2. **Controle verificável:** consegue preservar embalagem/logotipo reais por composição posterior, manter direção do movimento, produzir placas limpas, especificar câmera, duração e quadro de entrada/saída?
3. **Integração:** existe MCP/API estável que permita orçamento prévio, reserva de custo, idempotência, recibos, proveniência, cancelamento, revisão de candidatos e licença comercial?
4. **Qualidade em movimento:** dois candidatos por necessidade, inspeção de frames intermediários e comparação cega com geração já disponível e com solução não generativa.
5. **Custo total:** geração, tentativas rejeitadas, upscaling, armazenamento, retrabalho de máscara e supervisão humana, dentro do teto do piloto.

Nenhuma capacidade, preço, licença ou disponibilidade atual do Higgsfield foi verificada nesta missão; não registrar alegações de fornecedor como fato. A próxima decisão deve vir de teste lado a lado **depois** de uma necessidade visual definida, não da expectativa de que um MCP faça direção sozinho.

## Riscos de interpretação dos Reels

- Os tutoriais de @moonsol.design dedicam grande parte do tempo à tela de editor. O anúncio Aurora deve aprender o **procedimento**, não imitar a estética de screencast.
- O vídeo de processo da chamada de TV mostra equipe, moodboard e trecho final; não é evidência de que a peça inteira saiu automaticamente de um prompt.
- Efeitos de IA podem gerar identidade, pose e produto falsos; referência real e render final devem ser comparados.
- “Mais cortes”, “mais motion” e “mais texto” não são métricas de qualidade. O alvo é mudança com causa, continuidade e payoff.
- A pesquisa visual não substitui auditoria de som. A presença de uma faixa chamada *x-ray machine operation* num tutorial indica intenção, mas não prova que o efeito é bem mixado ou sincronizado.

## Estado ao encerrar esta missão

**Aprendizado visual documentado:** sim, com links, tempos aproximados e distinção entre observação, declaração do autor e inferência. **Tutoriais traduzidos em operações:** sete fichas iniciais. **Sistema ensinado/implementado:** não; esta missão foi somente de análise. **Qualidade do Aurora aprovada:** não, e o próprio recibo local ainda registra revisão humana pendente. **Higgsfield MCP escolhido:** não. **Próximo trabalho útil:** reproduzir uma técnica por vez em material próprio e verificar seu valor editorial antes de alterar a arquitetura de provedores.
