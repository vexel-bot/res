# Evidência primária: execução híbrida e qualidade de edição

Tier 1, Cochrane, 13/11/2026. Revisão independente curta das fontes indicadas pelo coordenador, após [o método](02-method.md) e [o desenho](03-design.md). Sem implementação, render ou API paga. A revisão foi reduzida conforme a instrução de recuperação do coordenador; não é revisão sistemática exaustiva, meta-análise ou validação empírica da Clicko.

## Resposta à pergunta

**Coordenar EffectCraft e Canvas/Chromium é uma hipótese de melhoria da execução, não uma intervenção já demonstrada como suficiente para atingir a meta criativa.** As fontes convergem na necessidade de preparar mensagem/design, perceber a sequência temporal, revisar craft e som e julgar o artefato final. Não há neste levantamento comparação causal entre esses dois renderizadores, nem probabilidade calculável de chegar ao nível dos Reels.

## Alegações, suporte e alcance

| Alegação | Fonte primária consultada | O que sustenta | Limite e implicação para a Clicko |
|---|---|---|---|
| Um vídeo tecnicamente entregue pode continuar fraco como edição. | [Timeline-Bench, v1, 28/09/2026](https://arxiv.org/abs/2609.35143). | O resumo descreve 56 tarefas de edição a partir de material bruto, incluindo comerciais; relata que a maior parte das execuções não resolvidas falhou somente na avaliação de qualidade. | Preprint sob revisão; consultei o resumo, não reproduzi a avaliação ou auditei seu grader. Não transformar a taxa do benchmark em chance de sucesso da Clicko ou de um Opus específico. Separar integridade/aderência/craft na aceitação. |
| Amostras esparsas não bastam para avaliar movimento fino. | [MotionBench, v2, 12/05/2026](https://arxiv.org/abs/2501.02955). | O resumo relata dificuldades de VLMs em compreensão fina do movimento e melhorias com entrada em maior taxa de quadros nos sistemas estudados. | Não avalia o atual Opus 5.5 na Clicko nem determina uma taxa universal de amostragem. Conferir janelas temporais relevantes e controles corretos/defeituosos; não aprovar suavidade por três stills. |
| Qualidade deve ser examinada por dimensões. | [VBench, v1, 29/11/2023](https://arxiv.org/abs/2311.17982). | Propõe dimensões de geração de vídeo e anotações humanas para examinar o alinhamento de suas métricas. | Geração de planos difere de montagem publicitária. Não importar uma nota agregada como aprovação de copy, ritmo ou CTA. Usar dimensões como questões separadas e calibrar a rubrica local. |
| Design e áudio integram a preparação do motion. | [Ordinary Folk, processo](https://www.ordinaryfolk.co/process). | O estúdio descreve mensagem/roteiro, investigação de linguagem, sketches/storyboards e animação sobre essa base. Considera som desde o início e desenvolve a composição musical após o animatic. | É relato primário de prática, também promocional; não ensaio de eficácia nem receita universal. Preparar quadros de estilo e ritmo, materiais e plano sonoro antes de investir numa peça completa. |
| Liberdade precisa de contexto utilizável e ferramentas claras. | [Anthropic, engenharia de contexto, 29/09/2025](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents). | Discute seleção de informação relevante, contratos de ferramentas e equilíbrio entre instruções rígidas e orientação vaga. | Recomendação de engenharia do fornecedor; não mede qualidade de anúncios. Preservar escolhas do diretor, mas disponibilizar materiais, referências, estado e ferramentas de forma recuperável e econômica. |
| Avaliar o resultado e calibrar o julgamento é diferente de conferir uma sequência de ferramentas. | [Anthropic, avaliações de agentes, 09/01/2026](https://www.anthropic.com/research/demystifying-evals-for-ai-agents). | Distingue avaliadores determinísticos, de modelos e humanos; recomenda calibração humana e alerta para avaliações rígidas ou desalinhadas com a tarefa. | Casos e orientação de fornecedor, não garantia independente de ganho. Usar testes de arquivo/contrato, rubrica editorial e revisão humana em funções diferentes, preservando soluções criativas válidas. |

Os registros, cobertura e limitações por fonte constam em [11-sources.json](11-sources.json). As três fontes de pesquisa foram lidas no nível do resumo; não usar seus números como resultados replicados. As páginas de processo e engenharia foram examinadas nos trechos explicitamente registrados.

## Julgamento de certeza

- **Alta rastreabilidade para o conteúdo declarado:** páginas dos autores/fornecedor e artigos originais, com versão e acesso identificados.
- **Moderada ou limitada para transportar o mecanismo:** motion perception e avaliação de tarefas ajudam a desenhar testes locais, mas domínio, modelos, mídia e critérios diferem.
- **Muito baixa para a alegação causal específica:** não há, neste conjunto, estudo de Clicko + Opus + EffectCraft versus Clicko + Opus + híbrido sobre materiais equivalentes.
- GRADE/RoB clínicos não foram aplicados a documentação de software e relatos de craft. Não há base para PPV, efeito combinado, IC ou probabilidade numérica. O corpo heterogêneo recebe síntese narrativa e limites por alegação.

## Princípios de melhoria sustentados condicionalmente

1. Preparar objetivo, promessa, informação por cena e quadros de estilo; transformar a copy em relações observáveis. É uma proposta de aplicação do processo de craft, não um storyboard estático obrigatório.
2. Preparar materiais que consigam mostrar essas relações. A capacidade de compor não assegura que uma imagem ou filmagem adequada esteja disponível.
3. Manter referências e decisões recuperáveis, com poucos contratos claros e fontes de cada cena preservadas. Não confundir disponibilizar uma ficha com demonstrar sua aplicação em outro briefing.
4. Revisar o MP4 com evidência temporal nas passagens críticas e som efetivamente ouvido. Detecção de colisão e medidas de áudio são componentes da revisão, não nota artística completa.
5. Calibrar uma avaliação local que aceite soluções válidas e encontre defeitos sem condenar o controle correto. Julgar sentido e compreensão antes de preferência; preservar o baseline positivo.

## Próxima prova discriminante

Executar as propostas P0 de Creswell: mesma cena determinística pela integração Clicko, pelo mesmo Craft diretamente e pelo caminho Canvas; controles corretos e defeituosos para revisão; retomada/exportação com resposta simulada. Essas provas localizam falhas de execução e integração. Depois, estudar isoladamente preparação de materiais ou política editorial com briefing/mídia fixados, antes de atribuir uma melhora estética ao híbrido.

Nenhuma fonte consultada autoriza afirmar que adicionar agentes, dinheiro, camadas ou outro motor garantirá acabamento. Também não autoriza concluir que o modelo é incapaz de editar. A alegação sobre modalidade nativa de síntese fotográfica/áudio do Opus não foi verificada nesta recuperação e não é usada como premissa.

## Busca e exclusões

Uma busca inicial em 13/11/2026 usou quatro consultas: `site:anthropic.com research effective context engineering agents long running harness evals`; `MotionBench 2501.02955 motion understanding video original paper`; `VBench 2311.17982 human video quality evaluation dimensions paper`; `site:platform.claude.com docs vision limitations audio image generation`. Após a orientação de recuperação, não ampliei a busca: abri os cinco URLs apontados e VBench já localizado, examinando os trechos acima.

Resumos gerados do Hugging Face, glossário Ultralytics, opiniões Reddit, notícias e espelhos duplicados não sustentam alegações técnicas desta síntese. Harnesses e modalidades apareceram na busca, mas ficaram fora desta revisão curta. Não há contagem PRISMA completa ou dupla triagem independente. Encaminhar este parecer à auditoria de confiabilidade e decisão do squad, com essa restrição explícita.
