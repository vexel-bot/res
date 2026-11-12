# ÓRBITA · teste pago do aprendizado editorial · 12/11/2026

## Hipótese e comparação

O usuário autorizou um teste com consumo de API após a validação local. A sessão usa Opus 5.5 na API direta da Anthropic e o EffectCraft real; especialistas Sonnet/Haiku estão disponíveis no fluxo corrigido. Não há compra de mídia. Mantém-se a política já autorizada do Console, sem teto interno de US$ 1,50, e não se força consumo mínimo.

Copy aprovada: **“O futuro cabe num curta. ÓRBITA, mostra de curtas de ficção científica. Confira a programação.”** Mostra fictícia, sem data, local ou seleção de obras inventados. Opus decide realização e duração. Referência editorial de 30–45 s, com liberdade para outra duração. O documento começa em 540×960, 24 fps, com uma faixa original opcional já disponível.

Comparador: corte de 34 s em `output/clicko-orbita-swarm-2026-11-11/orbita-opus-swarm.mp4`, rejeitado pelo usuário por perda de sentido. Seu custo registrado foi US$ 4,9449489, com exposição incerta adicional de US$ 0,5435261. A comparação deste ensaio é exploratória: o briefing agora inclui o feedback e o novo repertório, portanto não isola causalmente cada mudança.

## Critérios definidos antes do render

- Identificar em que intervalo o vídeo comunica uma mostra de curtas sci-fi, separando informação explícita de inferência visual.
- Descrever a progressão de cada trecho e a função das transições. Motivos espaciais devem contribuir para o convite de cinema, em vez de substituir o assunto por astronomia genérica.
- Inspecionar a legibilidade da categoria, nome e CTA a 300 px; conferir estados durante o movimento e pausas de leitura.
- Conferir continuidade de objetos, hierarquia, escala, luz e sombra. Detectar clarões tecnicamente e distinguir passagens deliberadas de picos sem função.
- Registrar áudio presente, nível, silêncios e eventos medidos. Sem escuta, qualidade musical e sincronismo percebido ficam inconclusivos.
- Registrar uso do repertório, revisão temporal, erros/correções, edição isolada, aplicação de contribuições, rascunhos e chamada de exportação pelo Opus.
- Medir tempo, turnos, custo por modelo, custo conhecido e exposição incerta. Quantidade de efeitos e gasto não são pontuação de qualidade. Compreensão de espectadores continua não medida.

## Conselho: hipóteses editoriais, sem impersonação

Aplicam-se três lentes conceituais independentes, não três agentes executados no Codex:

- **Spielberg — legibilidade:** a peça anterior pede interpretação antes de situar a oferta. Inferência operacional: uma revelação deve mudar o entendimento de quem vê. O teste será localizar o primeiro momento em que nome/categoria/convite podem ser compreendidos. Fonte e limites: [perfil documentado](C:/Users/edugu/.codex/skills/cinematic-mind-council/references/profiles/steven-spielberg.md).
- **Gilligan — consequência:** motivos desconectados não constroem argumento por compartilharem o tema espacial. Inferência: descrever a mudança produzida por cada ação e o que ela prepara no trecho seguinte. Contraexemplo: objetos reconhecíveis que apenas se substituem sem relação observável. [Perfil documentado](C:/Users/edugu/.codex/skills/cinematic-mind-council/references/profiles/vince-gilligan.md).
- **Villeneuve — tradução visual:** escala e atmosfera podem materializar uma ideia. Inferência: avaliar a função de cada enquadramento e transformação, sem prescrever sua escolha ao diretor. Risco: atmosfera alongada consumir o tempo da oferta. [Perfil documentado](C:/Users/edugu/.codex/skills/cinematic-mind-council/references/profiles/denis-villeneuve.md).

Síntese: preservar direção livre e cobrar coerência do resultado, com evidência do render. Não impor um storyboard do Codex ao Opus.

## Preparação e rastreabilidade

- Documento novo: `1b295922-5884-411b-a54f-eebf1da83593`. O comparador fica preservado.
- Primeira preparação recusou um briefing longo em `editorial_context` por enviar a instrução inteira ao contrato curto de busca. **Zero chamadas pagas, zero custo.** A busca agora recebe até 2.000 caracteres para recuperação inicial; a instrução integral continua no contexto do diretor. O teste de regressão passou com os outros dois testes de conhecimento (3/3).
- A tentativa sem cobrança foi conservada em `preflight-sem-cobranca.json`. A nova sessão tem chave própria; nenhuma chamada incerta foi repetida.
- Pasta dos resultados: `C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12`.
- Tarifas conferidas na [documentação Anthropic](https://platform.claude.com/docs/en/about-claude/pricing): Opus US$ 4/20 por milhão de tokens entrada/saída; Sonnet US$ 2/10; Haiku US$ 0,10/0,50 até 100 mil tokens de entrada. Cache de 5 min custa 1,25× na gravação; leitura 0,05× no Opus/Sonnet e 0,1× no Haiku. O recibo mede uso devolvido, não substitui a fatura do Console.

## Resultado

**Concluído: MP4 exportado pelo pedido do próprio Opus. Execução técnica passou; acabamento editorial ainda requer revisão.** Não houve montagem ou exportação manual substituindo a entrega do modelo.

| Indicador | Resultado observado |
|---|---|
| Duração | 19,5 s de vídeo; contêiner com áudio 19,52 s. Decisão do Opus, dentro da liberdade do briefing. |
| Entrega | 540×960, H.264/MP4, 24 fps, faixa de áudio presente. |
| Tempo da sessão válida, incluindo exportação | 1.012,47 s = **16 min 52 s**. |
| Edição | 12 lotes salvos; 40 camadas na composição principal e 26 nas seis composições de cenas. |
| Direção | Opus escreveu e depois comprimiu o próprio plano; montou a peça e chamou `finish_project`. |
| Especialistas | Disponíveis, mas **não acionados**. Opus declarou preferir manter o registro geométrico tela→grade na própria edição. Este ensaio não valida o enxame pago. |
| Chamadas | 33 respostas com uso retornado e uma interrupção com uso não confirmado. |
| Atrito nativo | Três scripts recusados: dois erros de objeto nulo/indefinido e um método não chamável. O modelo corrigiu e prosseguiu. |
| Revisão do diretor | Duas folhas de prévia; três `review_clip`: uma análise da fonte sonora e duas janelas da montagem. |
| Clarão | Detector local passou nos **468 quadros**, sem evento marcado. |
| Compreensão por espectadores | Não medida. Não foi registrada aprovação do cliente. |

Job de direção: `58dd197a-8bd3-401b-a9fc-cb7acf52eb79`. Exportação: `f9b5a783-3029-4491-8ff4-716bb523e0a1`. SHA-256 do MP4: `a1f34ac8e30b25f22226d73f0575ce38603bbc409507699e01f0270559be1d72`.

### Uso e conciliação

| Modelo | Custo calculado pelos tokens retornados |
|---|---:|
| Opus 5.5 | US$ 1,9753218 |
| Sonnet 5.5 | US$ 0 |
| Haiku 5.5 | US$ 0 |
| Render local e mídia paga | US$ 0 |
| **Total medido** | **US$ 1,9753218** |

O total foi recalculado de forma independente: 76 tokens de entrada sem cache = US$ 0,000304; 61.718 de saída = US$ 1,23436; 108.499 de gravação de cache = US$ 0,542495; 990.814 de leitura = US$ 0,1981628. As parcelas somam exatamente o recibo.

**Há exposição adicional incerta de até US$ 1,068272**, após uma interrupção de conexão e retomada automática do rascunho. O total medido mais esse limite é **US$ 3,0435938**; não é uma cobrança confirmada. O sistema conservou uma reserva de US$ 3,6359162, que também não representa gasto: inclui margem conservadora da autorização de chamada. Sem o uso retornado da chamada interrompida ou conciliação no Console, não é correto declarar US$ 1,98 como fatura final nem converter a reserva inteira em consumo.

A auditoria de capital omitia essa condição quando uma chamada posterior encerrava com sucesso. Foi corrigida para conservar a pendência de um turno anterior mesmo em job bem-sucedido. Um teste isolado passou, distinguindo uso medido, reserva e exposição. O relatório posterior registra **US$ 12,8083183 de custo Anthropic conhecido no histórico local**, dos quais US$ 1,9753218 são deste ensaio. A diferença aritmética para os US$ 200 informados é US$ 187,1916817, **exclui cobranças incertas e não é saldo confirmado do Console**. Não houve mudança nos limites do provedor.

### Comparação com o corte anterior

| Evidência | Corte anterior de 34 s | Novo corte de 19,5 s |
|---|---|---|
| Situação da oferta | Eclipse e vinhetas antes da marca; categoria ausente em 24,933 s e legível em 27,2 s na amostra | Sala de cinema reconhecível em 3 s; categoria legível em 4,583 s na prévia e em 5,2 s na grade comparativa |
| Relação entre trechos | Eclipse → película → órbita; a conexão com mostra era sobretudo da cartela final | Planeta → tela de cinema → variedade de cenas na mesma tela → grade e convite |
| Leitura a 300 px | Fechamento legível; abertura alongada e palavra ampliada com recorte em 6,8 s | Nome/categoria/CTA legíveis nos repousos; **moldura atravessa “O futuro” em 2,625 s** |
| Continuidade da transição final | Motivos diferentes se substituem | A mesma cena do disco voador passa da tela ao primeiro quadro da grade em 11,5–12,375 s |
| Áudio medido | Média −35,8 dBFS; pico −23,3 dBFS | Média −32,1 dBFS; pico −20,3 dBFS. Presente, ainda discreto; escuta não certificada. |
| Clarões pelo detector | Zero nos 816 quadros | Zero nos 468 quadros |
| Custo conhecido | US$ 4,9449489 + exposição incerta de US$ 0,5435261 | US$ 1,9753218 + exposição incerta de até US$ 1,068272 |

O novo custo medido é menor. Duração, briefing, contexto e decisões também mudaram; a comparação não estima o ganho causal de cada correção nem qualidade por dólar aprovada.

### Parecer do conselho conceitual sobre o render

**Observado:** 16 quadros por corte a 300 px; recuo de câmera entre 1,75 e 3,625 s a 8 amostras/s; tela→grade entre 11 e 13,375 s na mesma taxa; varredura técnica de clarão em todos os quadros. As grades temporais cobrem cada terceiro quadro da fonte, não todos. Não houve escuta nem teste cego com espectadores.

- **Legibilidade / Spielberg, inferência operacional:** há avanço de contexto: tela e plateia estabelecem cinema, e a categoria aparece durante o desenvolvimento. O ponto contrário é a passagem da moldura sobre a frase em 2,625 s, que a revisão do diretor não cobriu em detalhe. **Manter** o vínculo tela/cinema; **mudar** a sobreposição entre texto e moldura.
- **Consequência / Gilligan, inferência operacional:** a mesma cena passa de projeção para grade; agora há uma relação observável entre desenvolvimento e convite. Entretanto, as pequenas ilustrações são sobretudo ícones de gênero. Não demonstram a qualidade ou a existência de curtas reais. **Manter** a continuidade; **aprofundar** ações dentro das cenas se a ambição for um filme publicitário mais expressivo.
- **Escala / Villeneuve, inferência operacional:** o recuo transforma uma imagem grande em imagem projetada e cumpre função narrativa. O acabamento permanece simples: desenho plano, facho luminoso genérico, assentos pouco definidos e pouca variação compositiva. O cartão final permanece aproximadamente de 13 a 19,5 s, um terço da duração, com pouca informação nova. **Rever** tempo final e direção de arte antes de chamar a peça de equivalente às referências.

**Veredito interno: mais claro como anúncio, ainda abaixo do acabamento pretendido.** A execução técnica passa. O alvo de qualidade visual das referências não foi demonstrado. Não promover o ensaio como aprovado pelo cliente ou validado com espectadores.

### O que o teste realmente demonstrou sobre o aprendizado

O contexto reproduzido contém 68 entradas no índice e seis referências recuperadas inicialmente, com a versão `f771f533bf47727a27f4a193a211b67f4cf38e79f59ca2052560700448ccd18f`. O Opus usou descoberta de comandos e revisão temporal, mas não chamou `search_repertoire`, `consult_repertoire` ou os especialistas. Portanto, não se deve atribuir o resultado ao estudo completo das 68 fichas nem ao enxame.

As revisões temporais escolhidas pelo diretor foram 11–13 s (6 amostras/s) e 5,3–9,7 s (2,5 amostras/s). A transição que cruza o texto, perto de 2,6 s, ficou fora dessas janelas. A ferramenta de revisão existe e funcionou; a seleção das janelas não cobriu uma falha importante. Três falhas de contrato também consumiram tempo/tokens. Os recibos atuais registram os erros, mas não conservam todos os scripts recusados, limitando o diagnóstico preciso do método incompatível.

Próxima hipótese registrada, **sem nova geração nesta rodada**: comparar uma direção de arte e prévia de movimento aprovadas antes da montagem completa, cobrir também as transições de maior mudança de escala e conservar os argumentos dos comandos recusados. Nenhum desses pontos justifica simplesmente aumentar o gasto.

### Arquivos e verificações

- [Vídeo](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/orbita-aprendizado.mp4)
- [Projeto editável com mídia e manifesto](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/orbita-editavel.zip) — integridade ZIP verificada.
- [Recibo completo](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/recibo.json)
- [Custo recalculado](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/custo-conferido.json)
- [Verificação de render e comparação](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/verificacao.json)
- [Quadros novos a 300 px](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/novo-quadros-300px.jpg)
- [Recuo temporal com a falha de sobreposição](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/recuo-temporal.jpg)
- [Passagem tela→grade](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/tela-grade-temporal.jpg)
- [Capital após o teste](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-aprendizado-2026-11-12/capital-apos-teste.json)

O localhost foi reiniciado após o encerramento do trabalho pago para carregar a correção do briefing longo. A sessão normal de desenvolvimento continua com provedores pagos desativados; o ensaio autorizado foi executado pelo serviço nativo real da Clicko com sua conexão registrada.
