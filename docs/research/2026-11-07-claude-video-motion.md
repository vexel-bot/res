# Pesquisa — Claude, edição longa e motion graphics

Data: 07/11/2026. Escopo: referências de YouTube para orientar melhorias na Clicko. Não houve download de vídeos, reprodução, escuta ou validação visual dos resultados. Foram verificados 15 IDs por metadados oficiais YouTube oEmbed (HTTP 200, título e autor). Foram lidas descrições originais de 12 páginas watch; capítulos são os fornecidos pelos próprios criadores. Alegações de qualidade, custo e automação dos autores não foram auditadas. As recomendações abaixo são inferências de engenharia e direção, e não comprovação de resultados equivalentes.

## Vídeos verificados

| Vídeo / autor | Evidência e relevância |
|---|---|
| [How to Create Motion Graphics with Claude AI — Kevin Stratvert](https://www.youtube.com/watch?v=ZE9URNHaP5M) | Metadados + descrição original. Narração/SRT orienta gráficos (2:24); exportação (4:22). Inspira sincronismo por trecho e preservação de marca. |
| [AI Motion Graphics Just Got Scary Good — Zane Hoyer](https://www.youtube.com/watch?v=3GlRCBqx1Gc) | Metadados + descrição. Distingue texto para motion, imagem para motion e modelo gerador. Inspira separar decisão do Claude e execução do motor. |
| [Claude acaba de mudar a criação de conteúdo para sempre — Maestros da IA](https://www.youtube.com/watch?v=wopu5lYP0MM) | Metadados + descrição primária indexada na busca. Áudio e sincronismo (10:38), exportação (12:09). Fluxo em português de montagem por código. |
| [Crea Videos Profesionales con IA en Minutos — soypacoia](https://www.youtube.com/watch?v=MdDf3M-YjZk) | Metadados + descrição original. Templates e parametrização. Inspira reutilização de regras de marca sem regenerar o projeto inteiro. |
| [Claude Code + Remotion Edited this Entire Video — Guney Topcu](https://www.youtube.com/watch?v=QYUV9FjR5-M) | Metadados + descrição original. Narração dirige visuais (3:00), Remotion (4:50), problemas (7:20). Autor relata dessincronismo após alterar velocidade e apagamento de áudio; requer invariantes de timeline. |
| [How I Edit Videos with Claude Code — Aidan Stanik](https://www.youtube.com/watch?v=BNPlUj-CxB0) | Metadados + descrição original; capítulos até 26:50. Assets (7:39), primeiro render/revisão (15:55), transições (18:05), iteração de motion (19:02), regras reutilizáveis (23:52). Referência de processo para vídeos longos. |
| [Vox Motion Graphics Tutorial using Claude Code & Codex — Lukas Margerie](https://www.youtube.com/watch?v=W1jRF5hDAfo) | Metadados + descrição primária indexada. Revisão (4:01), comparação (6:58), correção de mapas (11:54). Mostra importância da revisão; não adotar assinatura visual de terceiro como preset automático. |
| [Claude + CapCut Completely Changes Everything For Editors — Matt Loui](https://www.youtube.com/watch?v=8oIFBQ9BhVU) | Metadados + descrição original. LUTs (0:54), listas (9:44), realce de texto (18:30), mapas (19:40). Biblioteca de componentes e acabamento são operações distintas. |
| [I Made Vox-Style Motion Graphics Using Only Claude Code & Remotion — MoSidd](https://www.youtube.com/watch?v=7wuYBfE131U) | Metadados + descrição original. Roteiro/estilo (1:30), cenas (2:26), ajuste (8:00), áudio/render (11:01). Inferência: plano de cenas e tokens visuais antes da animação. |
| [Claude Just Changed Content Creation Forever! — Sabrina Ramonov](https://www.youtube.com/watch?v=M4cmrdoUKxI) | Metadados + descrição original. Texto, assets, legendas e zonas seguras. Inspira QA de legibilidade e preservação de rosto/produto. |
| [Claude Code is Taking Video Editor Jobs Now — Chase AI](https://www.youtube.com/watch?v=4N_TfYVNM7k) | Metadados + descrição original. Skill, projeto e edição de cenas específicas. Inspira revisões locais e cenas com IDs persistentes. Não endossa título/alegação sobre empregos. |
| [I Finally Solved AI Video Editing — Jason Cooperson](https://www.youtube.com/watch?v=sGt1ACELN4k) | Metadados + descrição original. Presets (6:36), edição curta (10:01), longa (15:36), custos (17:28). Inspira políticas versionadas e medição separada de execução/custo. |
| [Full Remotion Tutorial to Create Insane Motion Graphics — MoSidd](https://www.youtube.com/watch?v=f393grXJn9E) | Metadados + descrição original. Gráfico (6:50), timeline (11:12), reel (14:24). Inspira motion como explicação de relações e tempo, com composição parametrizada. |
| [This Claude Skill Just Changed EVERYTHING — Brock Mesarich](https://www.youtube.com/watch?v=FVrNRnfC8oM) | Metadados oficiais + descrição indexada. Geração (8:00), voiceovers (14:00). Inspira handoffs explícitos entre roteiro, voz e render. |
| [Claude Opus 5.5: How To Make Motion Graphics — Rourke](https://www.youtube.com/watch?v=cDb-wPq0Iyk) | Metadados + descrição original. Storyboard (3:54), construção (5:58), sound design (6:52), voz/música (9:56). Inspira pré-planejamento e continuidade de objetos; não exige morph em toda troca de cena. |

## Tradução pelo conselho cinematográfico

Painel conceitual: Fincher (precisão de comportamento e continuidade) e Spielberg (clareza emocional e reação). Os princípios abaixo são I1, inferências operacionais dos perfis documentados da skill, não falas ou aprovação dos cineastas. Não foram executados clones separados.

- Fincher: antes de gerar, definir uma ação concreta por cena e um estado final verificável. Na Clicko, cena precisa de objetivo, estado inicial/final, direção de atenção, intervalo e restrições; o render deve preservar áudio, IDs e duração mesmo quando revisa texto/motion. Efeito: o espectador percebe transformação, em vez de apenas imagens bonitas. Risco: excessiva precisão pode eliminar espontaneidade. Teste: o evento e sua consequência aparecem na sequência, com trechos inspecionados.
- Spielberg: dar acesso humano ao problema antes do espetáculo e reservar tempo para compreender a consequência. Na Clicko, storyboard identifica foco, reação, revelação e pausa de leitura. Efeito: a promessa é legível. Risco: emoção não deve depender só da música. Teste: ver sequência sem trilha; ainda deve ser possível explicar a mudança.
- Motion: uma âncora de atenção por transição, animação de palavras inteiras e relação causa→consequência. Não aplicar a mesma transição a cenas sem relação. Contraexemplo: todos os títulos pulsam, todos os cortes dão zoom e o assunto fica ilegível. Teste: frame anterior/posterior mantém ponto focal claro e leitura a 300 px de largura.

## Melhorias executáveis na Clicko

1. Planejamento audiovisual versionado antes de gerar: beats, voz, duração medida, ativos, mensagens, ações, estado final, limites do motor e orçamento. Separar capacidades: Claude decide/edita, gerador cria pixels, TTS cria voz, renderer executa.
2. Voz como relógio mestre: medir áudio e mapear unidades de sentido a frames. Preservar origem/velocidade/faixas na revisão. Rejeitar alterações que apaguem narração ou excedam fonte. Não acelerar vídeo sem recalcular toda a relação entre source e timeline.
3. Biblioteca pequena de receitas validadas: title reveal, realce de palavra inteira, marcador de etapas, gráfico e ligação visual. Expor parâmetros e capacidades reais ao Opus; plano não deve mencionar recursos que o renderer não executa. Não executar código arbitrário retornado pelo modelo.
4. Para longo formato: capítulos/sequências, cenas com IDs e dependências, mudanças locais, política visual global, sincronismo ancorado em timestamps e revisão de continuidade entre capítulos. Um exemplo de 18 segundos não valida automaticamente um editor de 30 minutos.
5. Revisão após render: existência e duração de voz, ausência de cortes de palavra, material gerado rastreável, resolução/FPS, amostras em fronteiras, leitura e ação semântica. Status PASS/FAIL/INCONCLUSIVO; imagens isoladas não comprovam movimento fino nem inteligibilidade.

## Direção do próximo teste de 18 segundos

North star: uma ideia solta torna-se uma entrega compreensível. Promessa: clareza do processo criativo. Público: sócios/equipe do piloto. Formato: horizontal 720p, 24fps. Usar cenas geradas + narração PT-BR e motion que explique a conexão entre etapas. Manter paleta da Clicko e tipografia consistente; logos e frases no renderer, jamais texto confiável inventado pelo gerador.

Proposta de montagem que preserva verba: 0–6s cena gerada com problema físico observável; 6–12s segunda cena com resolução observável; 12–16s motion de três etapas conectadas com uma âncora; 16–18s assinatura com pausa de leitura. Usar duas gerações de 6s em vez de três deixa margem para locução e Opus, mas a escolha final depende do preço confirmado e saldo. Não gerar novamente material já aprovado sem necessidade.

Exemplo de locução a cronometrar, sem promessas não comprovadas: “Uma ideia precisa de direção. Cada escolha conecta o próximo passo. Até tudo ganhar forma. Clicko. Da ideia à entrega.” Não assumir que cabe em 18s antes de medir.

Assertiva A: objeto (materiais criativos), estado inicial disperso, evento organização, final arranjo distinto, intervalo 0–6s, evidência trecho contínuo; contraprova mãos apenas se mexem sem mudança identificável.
Assertiva B: relação entre etapas, estado inicial separado, evento linha de conexão, final caminho completo, intervalo12–16s, evidência início/meio/final e playback; contraprova só piscam sem mostrar relação.
Aceite: >=2 cenas realmente geradas, fala PT-BR presente inteira, cortes em limites semânticos, CTA legível, orçamento rastreado, export salvo no projeto. Revisão humana da compreensão/voz deve continuar explícita se só ferramentas técnicas foram usadas.

## Documentação técnica primária

- [Remotion Agent Skills](https://www.remotion.dev/docs/ai/skills): práticas de composição, layout, timing, áudio, legendas, render e integração. Claude não define sozinho uma estética fixa; a biblioteca e o briefing delimitam o resultado.
- [Remotion Sequence](https://www.remotion.dev/docs/sequence): composição temporal com from/durationInFrames/trimBefore. Usar como referência arquitetural, sem alegar que instalar Remotion é pré-requisito para corrigir a timeline existente.
