# Pesquisa de edição com Claude e diagnóstico da Clicko

> Encaminhamento atualizado: o editor de motion da Clicko é EffectCraft. As alternativas pesquisadas abaixo são registro histórico.

## Pergunta e cobertura

O usuário reprovou o vídeo de 18 segundos e pediu uma pesquisa no YouTube sobre produções editadas pelo Claude e Opus. Esta rodada consultou descrições, capítulos, páginas dos criadores e documentação oficial das ferramentas, além do código e do recibo local. Dez referências centrais estão registradas abaixo.

A inspeção pelo navegador abriu páginas públicas do YouTube, incluindo Ülviye Suna, kaye.creatives e Felipe Borges. A descrição expandida de Felipe foi lida diretamente. A reprodução apresentou anúncios e buffering. As capturas feitas nessa sessão mostram capa ou anúncio, portanto ficam excluídas da evidência estética. Esta pesquisa não estabelece que os dez vídeos foram assistidos integralmente. Áudio e transcrições completas permaneceram fora da cobertura. As conclusões sobre arquitetura usam as explicações públicas dos criadores e as documentações dos motores.

Nenhuma API paga foi chamada durante esta pesquisa.

## Referências consultadas

| Referência | Cobertura disponível | Processo descrito e trechos a conferir |
|---|---|---|
| [Claude Edited This Video, Ülviye Suna](https://www.youtube.com/watch?v=tdb9B5VJW70) | Descrição e capítulos indexados. Página pública aberta. | Whisper, FFmpeg e HyperFrames. Primeiro resultado em 5m56, detecção de erro em 6m18, revisões em 8m01 e criação de skills em 9m18. A descrição evidencia correção posterior ao primeiro resultado. |
| [Edit Videos with Claude Code, Santiago Munoz](https://www.youtube.com/watch?v=M1UQzYaQl4Y) | Descrição e capítulos indexados. | Claude Code como orquestrador em 3m29, timestamps com Whisper em 8m48, prévia em 13m47, depuração em 14m36, efeitos sonoros em 26m17. Separa edição, mídia e som. |
| [How I Fully Automated My Video Editing, Jason Cooperson](https://www.youtube.com/watch?v=XeTAlZiIWHE) | Descrição indexada e capítulos reproduzidos publicamente. | Rough cut em 6m57, gráficos em 10m19, segunda passagem em 11m42, captions em 15m43 e música em 17m36. O autor descreve render parcial e ajustes por gráfico. Qualidade final sem avaliação independente nesta rodada. |
| [I Made Motion Graphics Using Only Claude Code & Hyperframes, Stefan Karsen](https://www.youtube.com/watch?v=LDXka90NQ0Q) | Descrição e capítulos indexados. | WhisperX, HTML/CSS com HyperFrames e MCP do Premiere. Corte em 2m51, construção e refinamento de gráficos em 3m47. A integração com editor e o motor de gráficos têm papéis separados. |
| [How to Edit Videos With Claude Code, KVK AI](https://www.youtube.com/watch?v=mXwXwdrMMaM) | Descrição e capítulos indexados. | Limpeza com Descript em 4m00, Claude Code e Remotion em 6m00, regras de estilo em 11m00. O autor descreve desenvolvimento e iteração do próprio fluxo. |
| [Watch Claude Code edit my YouTube video, Brian Casel](https://www.youtube.com/watch?v=GlvH_waCx8w) | Metadados indexados. Descrição ampliada do fluxo consultada em [registro secundário](https://frontiermodels.cc/video/watch-claude-code-edit-my-youtube-video/). | O registro descreve transcrição, biblioteca de B-roll, vídeo-use/FFmpeg, HyperFrames e revisão de planos. Essa composição específica de ferramentas requer conferência direta do vídeo antes de tratá-la como implementação de referência. |
| [Como Fazer Motion Graphics INSANOS com Opus 5.5, Felipe Borges](https://www.youtube.com/watch?v=4wk7nTZler4) | Página e descrição expandida lidas diretamente no navegador. | O criador descreve regras do estúdio, marca real, captura de site, referência visual, lista de estados, grade de batidas e ciclos de crítica. Os números promocionais atribuídos ao peso de prompt e ambiente não são medições adotadas por esta pesquisa. |
| [Como editar Reels com Claude Code, Viegas Estudio](https://www.youtube.com/watch?v=cNsW8R8uHmA) | Página identificada e explicação pública do próprio criador em [Viegas Academy](https://www.skool.com/viegas-academy-free-2786/nuevo-tutorial-claude-code-edita-tus-reels-guia-skill-kit-gratis). | Pasta com referências, fontes, logos e cores. O criador recomenda Opus 5.5 com esforço médio e cinco passagens de revisão. O uso de esforço máximo não aparece como pré-requisito universal. |
| [How I Edit YouTube Videos Entirely with AI, Wilco](https://www.youtube.com/watch?v=5RrDBJT3LTw) | Vídeo incorporado e explicação técnica no [site do autor](https://www.growonrepeat.com/guides/how-i-edit-youtube-videos-entirely-with-ai). | Três etapas para corte/sincronia, animação em React e finalização com B-roll. O autor relata revisão humana e evolução das instruções. Resultados e economia são relatos próprios. |
| [How I Edit YouTube Videos With Claude Opus 5.5, Learn With Seb](https://www.learnwithseb.com/blog/edit-youtube-videos-with-claude-opus-5-5/) | Tutorial do próprio autor com vídeo YouTube incorporado, lido pela pesquisa web. | Talking head e captura separados, HyperFrames, referências, gráficos ligados a ideias faladas e efeitos sonoros. O autor usa esforço máximo em motion complexo e modelos menores em ajustes simples. O ID do vídeo incorporado não foi recuperado nesta rodada. |

Outros candidatos encontrados incluem [Claude Code + Remotion Edited this Entire Video](https://www.youtube.com/watch?v=QYUV9FjR5-M), [Opus 5.5 e Borumi](https://www.youtube.com/watch?v=AW3Uku__BBE) e [Claude Code + Premiere Pro](https://www.youtube.com/watch?v=upvDkK_Wobc). A abertura direta sofreu limitação de acesso. Esses candidatos ficam em triagem e não sustentam sozinhos as conclusões técnicas.

## O que as ferramentas permitem

O HyperFrames descreve composições em HTML e animações controláveis por quadro com GSAP, CSS, Lottie, Three.js e outros adaptadores. Seu CLI oferece prévia, inspeção, validação e render. Chrome captura os quadros e FFmpeg codifica vídeo e áudio. A documentação distingue as partes do motor e da produção. [Repositório oficial](https://github.com/heygen-com/hyperframes)

O fluxo documentado do Remotion cria um projeto, instala instruções para agentes, abre uma prévia e deixa o agente trabalhar nos arquivos do projeto. Essa é uma combinação de autoria, execução e observação. [Documentação oficial](https://www.remotion.dev/docs/ai/coding-agents)

Na API Anthropic, ferramentas são declaradas na requisição. O modelo solicita uma operação com `tool_use`. A aplicação executa e devolve `tool_result`, mantendo a conversa. A aplicação pode implementar um ambiente de edição por esse protocolo. Claude Code já organiza esse tipo de trabalho com ferramentas. [Documentação oficial de ferramentas](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)

## Causas confirmadas na Clicko

| Gargalo | Evidência local | Consequência e limite da conclusão |
|---|---|---|
| A última produção falhou antes de existir uma direção do Opus | Tarefa `37ede534-6076-4f49-b0cc-752833649e8b` terminou com `llm_provider_transport_failed`, 307172 ms e `submissionOutcome=unknown`. | O MP4 entregue foi montado pela recuperação local de `clicko-deep-local-cut.cjs`. A rejeição do vídeo avalia essa entrega. A tentativa paga deixou o custo pendente. |
| A chamada pede uma composição completa antes da execução | `UniversalLLMPlanner.plan` manda uma mensagem com projeto, schemas e instrução. O corpo Anthropic não declara ferramentas de edição. `production_editing.direct` executa direção, validação, render e uma revisão em ordem predefinida. | O modelo não escolhe uma sequência de consultas e pequenas ações sobre o projeto durante a geração. Erros são corrigidos em uma resposta completa adicional. |
| A autoria visual fica limitada ao contrato local | `LocalLayerStyle` permite texto, imagem e formas retângulo/elipse, duas famílias de fontes e um conjunto de keyframes. `VisualMotion` cobre posição, escala, rotação, crop, opacidade e revelação. | Há composição útil, mas SVG, grupos/precomposições, paths, desenho vetorial e animações procedurais não estão expostos nesse caminho. A liberdade adicionada continua dentro desse repertório. |
| A percepção é pré-selecionada pelo servidor | `production_editing.direct` amostra os dois primeiros materiais visuais. Referências viram contact sheets. `_cut_samples` escolhe quadros por frações e algumas emendas. A revisão recebe os dois primeiros strips. | O agente não pede mais evidência de um gesto ou transição que não compreendeu. O tempo contínuo, a seleção de tomadas e os demais materiais ficam parcialmente observados. |
| O som está desconectado da direção nessa rota | A cobertura registra `audioObserved=False`. O novo fluxo não consulta a transcrição nem os mecanismos existentes de seleção por fala em `contextual_assembly.py`. | O repertório existente de transcrição não compõe a inteligência desse planejador. Ritmo sonoro, pausas, palavra de impacto e edição por fala não são avaliados por essa chamada. |
| A execução longa não tem recuperação de progresso | O caminho aprofundado aumenta o timeout para 300 s. A requisição Anthropic pede a resposta completa. `client.stream` lê o transporte HTTP e o código só interpreta JSON no final. | O timeout perde o resultado utilizável e deixa a cobrança em aberto. Streaming de eventos, persistência de uso e recuperação de tarefa precisam de desenho próprio. |
| A revisão técnica ainda tem alcance menor que o objetivo de publicidade | O render verifica geometria, arquivo, amostras, quadros uniformes, tamanho de texto e presença de áudio. A prova local teve 432 quadros válidos e o usuário reprovou a peça. | Esses testes sustentam funcionamento e detectam defeitos específicos. Qualidade editorial e atratividade exigem observações próprias. |

O diagnóstico atribui os limites observados à integração, ao repertório exposto, ao material e ao método de revisão. A contribuição isolada de cada causa para a qualidade ainda requer experimento controlado.

## Correção proposta para o próximo ciclo

1. Fazer um ensaio de uma cena de 4–6 s em um motor de motion com autoria por código. HyperFrames é candidato por oferecer HTML/GSAP e inspeção por quadro. Comparar a mesma cena com o caminho canônico atual. Essa escolha ainda exige prova no computador e na arquitetura da Clicko.
2. Expor operações que permitam ao agente listar materiais, inspecionar intervalos, consultar fala, alterar um trecho, renderizar prévia parcial e inspecionar o resultado. A Clicko executa e registra cada operação com projeto, revisão e custo.
3. Persistir o projeto gerado e devolver à timeline um trecho de motion renderizado, com vínculo para sua fonte editável. As camadas internas do motor externo precisam de editor próprio ou de tradução explícita. Registrar esse limite na interface.
4. Fazer a revisão apontar diferenças observáveis em relação à referência. O agente deve corrigir o trecho criticado e renderizá-lo novamente. O número de rodadas e seu custo precisam de limites compartilhados por tarefa.
5. Separar profundidade do modelo de qualidade do ambiente. Comparar esforço médio e alto somente após confirmar que ambos conseguem concluir o mesmo ciclo. Registrar custo do provedor, tempo até prévia, retrabalho e aceite do usuário.

Nesta rodada, as mudanças são o diagnóstico e o registro das fontes. A integração de um novo motor e do ciclo de ferramentas permanece trabalho de implementação. O teto de US$ 1,50 pendente da tentativa anterior continua registrado até conciliação.
