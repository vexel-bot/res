# Método da investigação e protocolo de busca

Tier 0, 13/11/2026. Responsabilidade: Booth, após o [diagnóstico de Sackett](01-question.md) e antes do desenho de Creswell. Esta etapa define o método; não executa a busca, novos renders, implementação ou APIs pagas.

## Tipo de revisão e alcance

Selecionar **revisão de escopo técnica**, na tipologia de Grant e Booth, com síntese temática e análise crítica narrativa. A decisão envolve mecanismos heterogêneos: motor, integração, materiais, direção, percepção e conclusão de tarefa. Precisamos mapear capacidade comprovada e lacunas antes de testar a suficiência do fluxo híbrido.

Uma revisão sistemática exaustiva ou meta-análise não cabe nesta rodada: as fontes disponíveis não têm intervenções, materiais e resultados comparáveis. A revisão de escopo delimita o campo; comparações locais pareadas, propostas separadamente, poderão sustentar alegações causais. Não declarar PRISMA, saturação, efeito médio, probabilidade de atingir a meta ou PPV sem dados apropriados.

## SALSA: processo e responsáveis

| Fase | Entrega e execução |
|---|---|
| **Search** | Booth define o protocolo abaixo. Cochrane executa o levantamento técnico/científico; Forsgren examina código, contratos, testes e recibos. Higgins verifica origem e cobertura dos exemplos. Klein/Gilad interpretam alternativas e riscos de decisão. |
| **AppraisaL** | Cada executor qualifica fonte, versão, acesso, observação e limites. Usar ficha de adequação técnica e de procedência; estudos empíricos recebem avaliação de desenho e validade externa. Ioannidis audita a confiabilidade depois da coleta. |
| **Synthesis** | Matriz por Q1–Q5 de Sackett: alegação → fonte → mecanismo → alcance → contraprova → implicação para a Clicko. Separar achados concordantes, contraditórios e ausentes. |
| **Analysis** | Creswell integra medidas técnicas e julgamento editorial. A síntese compara opções e explicita quais provas mudariam a recomendação. Kahneman audita decisão e vieses após Ioannidis; o coordenador fecha o relatório. |

## STARLITE: busca reproduzível

| Componente | Especificação |
|---|---|
| **S — amostragem** | Intencional, orientada aos mecanismos de Q1–Q5. Buscar cerca de 10–16 fontes úteis como dimensão inicial de trabalho, sem transformar isso em critério de qualidade nem quota de vídeos. Parar por cobertura das alegações decisivas e registrar lacunas. |
| **T — tipo de evidência** | Documentação oficial, código/commits/issues do projeto, projetos e renders reproduzíveis, recibos locais, publicações originais dos criadores, artigos de pesquisa e relatos primários de produção. |
| **A — abordagens** | Busca web por domínio/assunto, navegação pela documentação, referências dos trabalhos e inspeção de artefatos locais. Registrar consulta literal, data, URL, versão, decisão de inclusão e trecho que sustenta a alegação. |
| **R — intervalo** | Documentação/modelos: versão integrada e informação vigente até 13/11/2026, priorizando 2024–2026. Aceitar fundamentos anteriores de animação, montagem e percepção quando pertinentes; justificar sua transferência. |
| **L — limites** | Português e inglês; sem limite geográfico. Fontes públicas ou arquivos já disponíveis. Sem novas compras, inferência paga ou acesso autenticado indisponível. Fonte inacessível permanece registrada, sem afirmar que foi assistida ou lida integralmente. |
| **I — inclusão/exclusão** | Incluir quando houver relação explícita com a tarefa, procedência e alcance identificáveis. Excluir como prova decisiva marketing sem demonstração, números de paridade sem corpus, vídeos sem projeto/processo verificável, espelhos duplicados e testes com variáveis trocadas sem controle. |
| **T — termos** | Combinar os blocos abaixo, registrando os ajustes reais de consulta. |
| **E — fontes eletrônicas** | Repositório integrado e upstream EffectCraft/FilmCraft; documentação Adobe; MDN/Chromium e FFmpeg; Anthropic; artigos originais via arXiv/página dos autores; páginas e publicações originais dos três criadores e de processos de motion. Locais de busca ainda por verificar. |

### Blocos iniciais de consulta

```text
(EffectCraft OR FilmCraft) (gaps OR fidelity OR scripting OR mask OR text OR render)
site:helpx.adobe.com/after-effects (keyframes OR graph editor OR alpha OR color)
(site:developer.mozilla.org OR site:chromium.org) (canvas OR rendering) (animation OR fonts OR color)
site:ffmpeg.org (alpha OR framerate OR timebase OR audio synchronization)
site:anthropic.com (context engineering OR agent evaluation OR long-running agents)
(MotionBench OR video understanding) (temporal OR motion OR evaluation)
(motion design OR animation) (storyboard OR styleframes OR sound design) process
```

Nas referências, partir dos URLs aceitos: `Dd5Md7NMj7P`, `DdW0UoSxXsX` e `Dcys2J3MfYK`. Investigar a diferença entre resultado, tutorial e preparação, sem generalizar o método por perfil ou atribuir ferramentas não vistas. Os tempos anteriormente capturados são marcos amostrados, não limites exatos dos planos. Áudio indisponível significa **não auditado**.

## Extração, avaliação e síntese

Cada registro deve conter: ID da alegação, Q correspondente, fonte/versão, autoria, acesso, material ou intervalo observado, afirmação sustentada, limitação, explicação alternativa e teste discriminante. Classificar a evidência como **observação direta**, **comportamento reproduzido**, **declaração documentada** ou **hipótese de aplicação**. Confiança é julgada por dimensão e justificativa, sem porcentagem inventada.

Para capacidades, perguntar se o recurso existe, funciona no build integrado e produz o estado esperado. Para craft, perguntar se o princípio explica uma decisão observável e em quais briefings falha. Para artigos sobre modelos, separar resultado no benchmark de qualidade de edição comercial. Para relatos de agentes, separar o software disponível, o material recebido e a intervenção humana.

## Handoff para Creswell

Definir integração mista com comparações determinísticas de motores, análise qualitativa das passagens e teste de compreensão anterior à preferência. Fixar fatores e gabaritos antes da coleta; não usar Reels como controles equivalentes. Relatórios de execução devem distinguir **funciona tecnicamente**, **serve à mensagem** e **agrada ao público**. Tempo/custo incluem preparação, render, tentativas e recuperação. O desenho deve localizar o menor próximo experimento capaz de mudar a decisão, preservando a liberdade editorial do Opus.
