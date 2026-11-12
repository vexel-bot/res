# Clicko · gargalos adicionais e ÓRBITA independente

## Escopo e hipótese

Pedido: investigar outros limites, corrigir os comprovados e executar uma única peça com o Claude fora da estrutura de edição da Clicko. Em seguida, o usuário pediu uma referência clara entre @creators, @paulo.ia e @moonsol.design. A seleção está em [Referências e meta da ÓRBITA](../studios/research/CLICKO_ORBITA_REFERENCIAS_META_2026-11-12.md).

Hipótese a examinar: o EffectCraft pode limitar o resultado. A comparação também envolve ferramentas, contexto, materiais, briefing e gestão da sessão. Uma geração independente não isola todas essas variáveis e não prova superioridade de um motor.

## Problemas comprovados e correções

| Problema | Evidência e efeito | Correção implementada |
|---|---|---|
| Inspeção integral muito volumosa | No ensaio anterior, o caminho Clicko terminou antes de editar e gravou 159.803 tokens de cache em uma chamada após inspeções grandes. O catálogo foi paginado naquela entrega, mas faltava focar propriedades de camadas específicas. | `inspect_project` aceita busca pelo nome, IDs e paginação, incluindo propriedades nativas quando solicitado. A inspeção completa continua disponível. |
| Compactação podia apagar as fontes vistas | A renovação guardava a última prévia do rascunho, mas não os pixels de materiais examinados antes da primeira edição. | Fontes inspecionadas permanecem identificadas por assetId e separadas da evidência do rascunho. A renovação por orçamento passa a funcionar também antes do primeiro lote de edição. |
| Contagem e renovação concentradas no experimento de enxame | O caminho Anthropic convencional usava uma estimativa para o orçamento e não entrava na mesma contagem preventiva de contexto longo. | Habilitar contagem de tokens e compactação também nas sessões Anthropic com cache. A recuperação de uma resposta truncada usa o mesmo checkpoint com evidências. |
| Inventário perdia informação já cadastrada | O diretor recebia ID, tipo e título, embora descrição, função e dados técnicos estivessem disponíveis no cadastro. | Acrescentar descrição, função, checksum, duração, dimensões e presença de áudio quando conhecidos. Usar também a ingestão pronta do mesmo workspace e checksum para uploads comuns. Não inventar metadados de arquivos ainda não analisados. |
| Repetição de inspeção no mesmo estado | A deduplicação de inspeções era restrita ao enxame. | Estender o reaproveitamento à sessão normal, somente para a mesma ferramenta, argumentos e lote, com vínculo ao resultado anterior. A revisão mantém distinção entre material de origem e montagem. |
| Primeira página da revisão podia cobrir apenas 0,5 s | Em 24 fps, os 12 quadros padrão consecutivos cobrem aproximadamente o primeiro meio segundo, embora o relatório também cubra o áudio e o trecho reproduzível inteiro. | Acrescentar `review_clip sampling=overview`, cobrindo início e fim do intervalo. Preservar o modo de quadros consecutivos para movimento. Cada relatório declara qual amostragem foi usada e suas limitações. |
| Rastreabilidade incompleta dos atos | Os recibos anteriores registravam nomes de ferramentas e alguns resultados; não preservavam sempre os argumentos e scripts executados. | Guardar toolUseId, parâmetros, hash e a revisão no pedido de exportação. O checkpoint usa um resumo desses recibos, sem reinserir o código completo no contexto. |
| Meta estética pouco explícita | O acervo reunia muitas técnicas e gêneros, sem uma peça principal escolhida para calibrar o acabamento da ÓRBITA. | Ficha `research.target.orbita.reference_triad`, recuperável por briefing e com escopo de projeto. Seleção cinematográfica, composição e produto em ação têm referências e critérios distintos. O áudio dessas referências continua fora da avaliação. |

## O que a auditoria do motor permite afirmar

EffectCraft é uma implementação independente, não uma distribuição open source do After Effects da Adobe. O build integrado é v0.8.0, revisão `67434e90`; a distribuição pública usada no ensaio anterior estava em `f953cd2`. Consulte a origem em `workers/craft/sources.lock.json` e as lacunas em `third_party/craft/effectcraft/docs/gaps.md` e `docs/scripting-parity.md` daquele projeto.

O projeto documenta incompatibilidades com formatos e presets Adobe e com o ecossistema de plugins. Isso exige verificar cada operação necessária. Não demonstra que essas lacunas causaram a composição fraca de uma peça específica. Encontrar um retorno neutro em código de contexto padrão de um efeito também não prova que o efeito é sempre inoperante.

Não removemos isolamento entre workspaces, integridade de materiais ou preservação do projeto: eles protegem dados e não prescrevem o estilo do diretor. Não foi acrescentado MCP ao fluxo. A direção continua podendo escolher duração, camadas, cortes e efeitos entre operações disponíveis.

## Método do ensaio independente

Pasta de execução: `C:/Users/edugu/Downloads/clicko-orbita-independent-20261112`, fora do repositório. Sessão nova de Claude Code com API direta Anthropic, modelo `claude-opus-5-5`, esforço alto e teto informado de US$ 3 para uma peça. A copy é “O futuro cabe num curta. ÓRBITA, mostra de curtas de ficção científica. Confira a programação.”

O Claude recebeu o pedido de MP4 vertical com áudio e fonte editável, o inventário de ferramentas gerais e permissão para escolher a técnica e buscar materiais. Não recebeu corte anterior, projeto Craft, roteiro de cenas, ficha de estilo nem mídia da Clicko. As bibliotecas locais foram disponibilizadas por `NODE_PATH`; os caminhos da aplicação não fizeram parte do briefing. O teste preservou esse briefing após o pedido posterior de selecionar referências.

Para executar o Opus 5.5 foi necessário atualizar o Claude Code de 2.1.257 para 2.1.322. Duas tentativas de preparação terminaram rejeitadas por configuração de workspace/versão, com US$ 0 reportado. Ficaram arquivadas separadamente. A execução paga é uma sessão; revisões e tentativas de render que o próprio Claude fizer pertencem a essa mesma peça. Não há outro teste pago da Clicko nesta rodada.

Nos primeiros atos, ele escolheu fontes OFL do Google Fonts e começou a escrever um renderizador próprio em JavaScript. Encontrou `ENAMETOOLONG` ao tentar um comando Bash extenso e um erro de aspas; passou a dividir arquivos e usar a ferramenta Edit. Esses erros ocorreram no ambiente geral de Claude Code/Windows, fora do EffectCraft. O registro os separa de limitações do motor.

## Validação e resultados

Os primeiros 26 testes passaram para inspeção, histórico/finanças e revisão temporal. A rodada seguinte de repertório, direção e histórico passou em 16 testes, incluindo recuperação da ficha da ÓRBITA. São testes locais, com chamadas de inferência simuladas; a revisão temporal usa FFmpeg real. A prova adicional de exportação nativa e inventário está registrada no fechamento abaixo.

Uma terceira rodada passou em 10 testes, incluindo o EffectCraft e FilmCraft reais: inspeção de fontes, edição, persistência após duas interrupções, retomada e exportação. O inventário distingue metadados de ingestão atual e desatualizada por checksum e não revela dados de outro workspace. As rodadas têm testes em comum; seus totais não devem ser somados como casos distintos.

No fechamento, os 12 testes de histórico/finanças passaram novamente após corrigir a conservação de evidências em compactações sucessivas. O checkpoint conserva pixels de fontes e da mesma revisão do rascunho, sem reapresentar uma prévia antiga como evidência de uma montagem alterada. A Clicko local foi reiniciada para carregar as correções.

## Resultado do teste independente

| Item | Resultado verificável |
|---|---|
| Modelo / agente | Um Opus 5.5, Claude Code 2.1.322, esforço alto; nenhum enxame ou MCP. |
| Direção escolhida | Canvas 2D próprio, tipografia Unbounded e Space Grotesk, planeta laranja, tira de filme com vinhetas de ficção científica, assinatura e CTA. Fontes OFL incluídas com licenças. |
| Duração escolhida | 16 s, 1080 × 1920, 30 fps. A duração veio do próprio Opus. |
| Tempo da sessão | 1.002,525 s, aproximadamente 16 min 43 s. |
| Consumo informado pelo Claude Code | **US$ 3,0205758**, todo atribuído ao Opus em `modelUsage`; preço de lista informado pelo CLI, sem conciliação com fatura. |
| Contexto e saída | `modelUsage`: 130.565 tokens de criação de cache, 1.355.574 de leitura, 104.823 de saída, dos quais 41.039 de raciocínio. O agregado `usage` do CLI tem contadores diferentes; ambos foram preservados, sem misturá-los para recalcular um total. |
| Encerramento | `error_max_budget_usd`, após 26 turnos. O teto do Claude Code é verificado entre requisições; a última levou a US$ 0,0205758 além dos US$ 3. |
| Autonomia | Escreveu o renderizador, consultou quadros e aplicou revisões. **Não criou o áudio, não pediu exportação e não entregou MP4 final.** |
| Recuperação local | Codex executou o renderizador sem alterar a criação e codificou os 480 quadros com FFmpeg. API adicional US$ 0. Arquivo `orbita-independente-previa-sem-audio.mp4`, explicitamente uma prévia silenciosa recuperada. |
| Integridade | SHA-256 do MP4 `040484f64c32e9d7d47aff43b5d1fe69626382dfc598ae0b217296ec7f490391`. |

O script `clicko-orbita-independent-evidence.py` registrou o consumo como experimento externo encerrado na Clicko, job `2e418fc1-dd9d-4149-b450-b0d832cae866`, associado ao projeto de referência sem alterar sua revisão 3. `costSource=claude-code-receipt-list-pricing`, `invoiceVerified=false` e `exportRequested=false` preservam as qualificações. A importação é idempotente pelo recibo e não dispara inferência.

## Comparação e diagnóstico editorial

A leitura dos quadros exportados a 300 px mostra uma metáfora mais vinculada à copy: mundos de ficção científica cabem em quadros de uma tira de filme. A linguagem continua sendo ilustração procedural. Ela não alcança a profundidade fotográfica, a presença e a integração de material da referência principal. Não há prova de preferência estética ou compreensão por espectadores.

No corte local anterior de 18 s havia sete planos de filmagem licenciada, 35 camadas, categoria a partir de aproximadamente 2,67 s e duas pistas de áudio. A peça independente recebeu somente copy e ferramentas, criou suas próprias cenas e só completa a categoria depois de cerca de 10 s. Não houve comparação cega nem controle dos materiais. O braço Clicko pago anterior não chegou a montar; portanto não há um MP4 desse braço para comparar como se estivesse concluído.

Na transição de aproximadamente 8 s, o MP4 recuperado mantém um clarão amplo. A medição em quadros decodificados e reduzidos a 90 × 160 encontrou variação média máxima de luminância de 107,22 em um quadro e 187,81 em três; em 8,0 s, 100% dos pixels reduzidos variaram mais de 50 níveis. No código autoral `phaseB`, o próprio Opus desenha um retângulo de tela inteira com alpha inicial 0,9, decaindo entre 8,0 e 8,35 s. Isso localiza a origem na direção/código escolhido fora do Craft. O agente revisou um problema de flash, mas não eliminou esse evento. A inspeção técnica não implica um diagnóstico médico ou julgamento de percepção.

Sem faixa de áudio, não se avaliam mixagem, ritmo audiovisual ou sincronismo. O resultado está registrado como tentativa sem entrega autônoma; não entra como vídeo aprovado.

**Conclusão sustentada:** dar acesso geral ao computador permitiu criar outro vocabulário visual, mas transferiu para o modelo o trabalho de programar um renderizador e não garantiu entrega ou bom anúncio. O teste não sustenta atribuir toda a fraqueza ao EffectCraft. Permanecem separadas três necessidades: preparação de materiais/cenas adequados ao conceito, referência estética explicitamente recuperada e revisão do MP4 real com som. As correções de contexto e inspeção foram validadas localmente; seu ganho estético ainda exige um ensaio posterior com a mesma mídia e briefing. Não foi feita outra geração paga para simular esse ganho.

## Entrega reproduzível

Pasta para revisão: `C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-independente-2026-11-12`. Contém a prévia silenciosa, os fontes editáveis em ZIP, recibo, medições e quadros. O ZIP inclui as fontes e licenças do trabalho; não inclui chaves, `.env` ou logs brutos da sessão.

Os próximos testes da ÓRBITA devem declarar a comparação com `research.target.orbita.reference_triad`, preservando a liberdade de direção. Não há frequência obrigatória de cortes ou número de efeitos. A referência serve para discutir e medir diferenças observáveis, e não para autorizar a reprodução de mídia de terceiros.

## Atualização após o feedback do usuário

Em 12/11/2026, o usuário confirmou as três referências e classificou a prévia independente como o primeiro resultado positivo, ainda com trabalho a fazer. Esse feedback passa a orientar a evolução estética. A versão foi preservada como baseline com o hash acima; a ausência de áudio e a recuperação da exportação permanecem no recibo técnico. A classificação é `positive_progress_needs_revision`, sem marcar aprovação de anúncio final ou estudo com espectadores.

O [manual de storyboards e adaptação](../studios/knowledge/playbooks/tres-referencias-storyboards-2026-11-12.md) detalha as três linguagens, os critérios de escolha, procedimentos propostos e próximos passos. O feedback está ligado ao arquivo no [registro da primeira versão positiva](../studios/knowledge/orbita-quality-baseline.v1.json) e no contexto do projeto da Clicko. Essa entrega documental consumiu US$ 0 de API e não gerou outro vídeo.
