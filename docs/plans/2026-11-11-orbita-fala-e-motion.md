# ÓRBITA com fala real e motion original

## O que explica a diferença em relação à IDE

O Reel de Matheus Gobbi apresenta um tutorial de edição com Claude e filmagem do apresentador. O player abriu, mas as capturas permaneceram no mesmo quadro. A explicação falada, os prompts e as ferramentas da demonstração seguem sem confirmação. A Clicko já reproduz o ciclo verificável em integrações documentadas de Claude Code: o modelo acessa material e contexto, usa as ferramentas do editor, inspeciona o resultado e corrige ou exporta. Em uma IDE, o agente também pode usar arquivos, comandos e integrações externas do projeto. [Reel de Matheus Gobbi](https://www.instagram.com/p/DflIbFny1zw/) · [Claude Code](https://code.claude.com/docs/en/how-claude-code-works) · [Claude Code com Premiere](https://docs.primcut.app/guides/connect-claude-code)

Na rodada anterior de FilmCraft, o modelo recebeu apenas dois anúncios motion terminados. Reaproveitou uma entrada, o plano de Saturno e a assinatura, e a trilha perdeu 8,4 dB de pico em relação à fonte principal. Isso comprovou remontagem, mas a disponibilidade de cenas já fechadas deixava pouco espaço para demonstrar criação ou edição de fala. Quatro tentativas falharam. Uma rejeição veio da regra de sincronismo. Outra veio de um esquema incorreto que anunciava movimentos como lista de números, embora o motor exigisse objetos.

## Correções e condições

- FilmCraft recebe a descrição correta de cada movimento de clipe, incluindo clipe, faixa e tempo. O contexto indica que a posição da faixa na lista pode divergir do seu identificador nativo.
- EffectCraft ganhou a chamada direta de script no rascunho. Ela pode montar várias cenas e camadas e salva o lote por meio da mesma validação e persistência dos outros comandos. A escolha de quantas chamadas, revisões e camadas fazer é do Opus. O teto de gasto e a execução isolada continuam valendo.
- O teste local com o motor real verificou que o atalho de script funciona depois de reabrir um rascunho salvo. Também verificou a forma aninhada do comando de mover clipes.
- Os dois ensaios usam copy preparada antes da montagem. A filmagem recebe “Histórias curtas. Universos inteiros.” O motion recebe “O futuro cabe num curta.” Ambos recebem a categoria e o convite para conferir a programação. As decisões de cenas, efeitos, ritmo e uso da trilha são do modelo.
- O teste de FilmCraft usa gravação de arquivo com Powtawche Williams em câmera e fala original. Há imagens adicionais de Saturno e uma assinatura opcional da ÓRBITA. O texto da fala veio da transcrição do JPL, com marcações aproximadas a partir das pausas da faixa. Uso no estudo interno, com crédito e sem atribuir a mostra à entrevistada. [Gravação e transcrição](https://www.jpl.nasa.gov/videos/news-from-saturn-6/) · [Imagens de arquivo](https://www.jpl.nasa.gov/videos/saturns-weirdest-ring/) · [Política do JPL](https://www.jpl.nasa.gov/jpl-image-use-policy/)
- O motion parte de uma composição vazia de 16 s e de uma faixa local original, com acentos disponíveis em momentos conhecidos. O efeito isolado de entregar copy pronta fica em aberto porque os materiais, o motor e a tarefa também variam.
- O teto combinado é US$ 1,50. A primeira sessão reservou US$ 0,80. O motion usa o saldo medido, arredondado para baixo, descontando eventual exposição incerta.

## Resultados e limites da autonomia

| Ensaio | Filme final | API | Autonomia observada |
| --- | --- | --- | --- |
| FilmCraft, gravação e fala | 13,71 s, vertical, 24 fps, com fala real | US$ 0,7311124 em 28 chamadas | O Opus selecionou e montou os trechos, reenquadrou a apresentadora e salvou quatro lotes. O histórico consumiu a margem de previsão antes de finalizar. O rascunho foi exportado localmente. A tradução, os créditos editoriais, a copy intermediária e o ganho de voz foram acrescentados localmente. |
| EffectCraft, motion original | 16 s, vertical, 24 fps, com trilha original | US$ 0,6452094 em 12 chamadas | O Opus escreveu o script principal, conferiu prévias e salvou dois lotes. A revisão ficou salva, mas a sessão não chamou finish_project. O rascunho foi exportado localmente, sem edição adicional. |

Total medido de US$ 1,3763218, abaixo do teto de US$ 1,50, sem exposição de cobrança incerta. As retomadas usaram a mesma reserva de cada sessão. Elas não reiniciaram os contadores de gasto. A autonomia de exportação ainda não ficou comprovada nestes dois casos.

Na filmagem, a fala está entre 2,5 s e 6,9 s. O trecho recebeu ganho local de 7,5 dB. O pico medido passou de −16,8 para −9,3 dBFS. A tradução apareceu no quadro e a assinatura ficou preservada. As legendas foram alinhadas a partir do trecho selecionado e das pausas, sem verificação de cada palavra por reconhecimento de fala.

No motion, um ponto orbitando se revela como parte de um fotograma, outros fotogramas formam uma tira e a composição abre para a marca. O CTA permanece legível a 300 px no fechamento. A transição em torno de 7,5 s ainda tem um clarão dominante. A trilha mediu média −26,8 dBFS e pico −11,6 dBFS.

A inspeção agora devolve identificadores, nomes e tempos por padrão, com as propriedades completas disponíveis sob demanda. Ao retomar por orçamento, a sessão recebe um resumo do rascunho e os tempos das prévias válidas do lote atual. Corrigimos também os tipos de identificadores das faixas em comandos de legenda e edição. O teste local de recuperação e exportação do EffectCraft passou com o atalho de script. A correção reduz reenvios, mas a previsão conservadora de entrada ainda pode interromper uma revisão sob teto baixo.

FilmCraft, sessão 3ed934bb-4386-44e1-8436-e66d7c6ac6d4 e render legendado f892b419-d8a1-44aa-88ef-a7ff8e99e0a0. EffectCraft, sessão fbb0da8b-83d9-43c3-b062-8d558910fd8b e render 6f572fb9-3586-4888-bff0-1de02133cc47.
