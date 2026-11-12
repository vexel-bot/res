# ÓRBITA com direção livre e edição em paralelo

## Implementação e prova local

A sessão experimental usa a API direta da Anthropic com Opus como diretor, Sonnet como editor delegado e Haiku para indexação de materiais. Os especialistas editam cópias do mesmo rascunho, renderizam uma prévia e devolvem o script, os IDs dos materiais e a evidência. O diretor pode aplicar a contribuição, reescrevê-la ou descartá-la. Somente a sessão principal publica uma nova revisão e inicia a exportação.

O histórico mantém a base de briefing e ferramentas no cache. A contagem gratuita da Anthropic mede a entrada inicial e contextos grandes. Ao renovar o contexto, preserva o resumo da timeline, o plano editorial, as contribuições disponíveis, os erros recentes e os pixels da última prévia válida da revisão. A inspeção completa continua disponível sob demanda. O modo experimental registra reservas por chamada e não aplica os tetos mensais ou por vídeo da Clicko. O Console da Anthropic controla o saldo.

A conciliação anterior à geração fechou cinco reservas com uso verificável, liberando US$ 1,9048244. O uso medido desses cinco jobs foi US$ 4,1551756. Seis jobs antigos permaneceram com cobrança incerta, somando US$ 2,50 reservados. Esses valores não representam a fatura do Console.

A prova local usou EffectCraft real e respostas simuladas, com dois especialistas sincronizados em paralelo. Renderizou 30 s e 45 s. A timeline principal recebeu apenas a contribuição selecionada e o pedido de exportação do diretor entregou MP4 sem intervenção. Repetir o pedido devolveu o mesmo recibo. Os testes de contagem multimodal, conciliação, orçamento e detecção de clarão passaram. O TypeScript passou. A opção experimental fica disponível em uma conexão Anthropic direta com os três modelos e orçamento interno configurado em zero. As conexões com teto próprio continuam a aplicá-lo.

Na cópia nativa da ÓRBITA de 16 s, desativar a camada Clarão retirou o pico de tela inteira em 7,5 s. O detector marcava 99,32% de área e elevação média de 100,66 na escala de cinza. A mesma janela de 31 quadros passou após a alteração. O original ficou na mesma revisão e com o mesmo checksum.

## Repertório e aprendizado

O repertório v2 contém 12 referências em proporção 4/4/4 de YouTube, Shorts e Pinterest. Cinco têm quadros observados, sete têm cobertura parcial. As técnicas novas entram como candidatas e a cobertura é explícita. Cada projeto registra o hash da versão consultada. A evidência do render vira candidata no conhecimento do workspace. A promoção exige um teste local identificado com checksum do artefato e resultado observado.

## Ensaio pago

A copy aprovada é “O futuro cabe num curta. ÓRBITA, mostra de curtas de ficção científica. Confira a programação.” O Opus recebeu liberdade de duração e realização. O projeto inicial tem 540 × 960 a 24 fps e uma faixa original opcional de 60 s. O MP4 e o projeto editável serão acompanhados do recibo por agente/modelo, tempos, prévias e indicação de qualquer intervenção.

As cinco primeiras chamadas ao Sonnet consumiram saída em raciocínio adaptativo e terminaram sem enviar a ferramenta com o script. A tentativa de exigir a ferramenta foi recusada pela contagem de tokens do Sonnet 5.5 antes de chamar a API paga. O formato `between_tools` com `tool_choice` automático passou pela contagem real e pelos testes locais. O Haiku entregou o índice após a retomada. A sessão foi retomada no mesmo rascunho e com o mesmo identificador. As retomadas ficam registradas como intervenções técnicas e as cobranças sem uso final ficam em aberto. [Mudanças do Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5)

## Resultado da ÓRBITA de 34 segundos

O Opus alterou a duração de 36 para 34 s e editou 21 lotes no projeto. O Sonnet produziu três contribuições com prévia. O Opus abriu as propostas e incorporou duas, a película vertical com vinhetas e a ponte de 22,4 a 24,5 s para a órbita. Um script delegado de categoria foi recusado pelo motor por tentar gravar opacidade estática sobre uma propriedade com quadros-chave. O Opus montou o fechamento final e chamou `finish_project`. A exportação `b1667378-3958-4c2b-9d15-f92c4c2cc196` terminou em 91 s. A sessão levou 1 h 47 min e 47 s desde a criação, incluindo as pausas técnicas. A última retomada até o pedido de exportação levou 4 min e 22 s. O ZIP contém o `.ecproj`, a faixa original e seu manifesto.

| Indicador | Corte de 16 s | Corte de 34 s |
|---|---|---|
| Abertura e variação de escala | Órbita pequena sobre fundo escuro, seguida de película estreita | Horizonte iluminado, película com cinco motivos sci-fi e passagem para órbita em escala grande |
| Categoria e CTA em largura de 300 px | Categoria menor, CTA em texto simples | Categoria em duas linhas e CTA em botão laranja, ambos legíveis no quadro de 31 s |
| Clarão detectado | Um evento em 7,5 s, 99,32% da área | Zero eventos nos 816 quadros |
| Som | Média de −26,8 dBFS | Média de −35,8 dBFS, 9 dB abaixo do corte de 16 s |

O eclipse abre com mais presença visual. A peça fica cerca de 10 s no mesmo motivo antes de revelar a primeira vinheta. A luz muda da borda quente do eclipse para o azul da órbita e o laranja do CTA. As vinhetas dão variedade e o fechamento segura a composição para leitura. O áudio está presente e é discreto. Na forma de onda do MP4, o ataque de 22,53 s fica 0,13 s após a entrada prevista da ponte. Os ataques mais próximos das marcas de 11,5 e 23,5 s antecedem essas marcas em 0,22 e 0,23 s. Essa checagem aproxima ações e pulsos, com avaliação de sincronismo percebido ainda pendente. A qualidade editorial foi inspecionada internamente e a compreensão ainda não foi medida com espectadores.

### Uso medido pela Anthropic

| Modelo e etapa | US$ |
|---|---:|
| Opus · direção e primeiros lotes, chamadas 1–12 | 0,4440890 |
| Opus · recuperação e montagem, chamadas 13–26 | 1,1766124 |
| Opus · colaboração e revisão, chamadas 27–62 | 1,9285124 |
| Opus · revisão final e exportação, chamadas 63–81 | 0,8935368 |
| Sonnet · nove chamadas de edição, incluindo seis entregas falhas | 0,5014860 |
| Haiku · indexação concluída com uso disponível | 0,0007123 |
| **Total calculado pelo uso retornado** | **4,9449489** |

Há US$ 0,5435261 de exposição adicional estimada, com uma chamada interrompida do diretor e uma resposta incompleta do Haiku. O valor medido resulta dos tokens retornados e das tarifas publicadas. A confirmação da cobrança pendente depende do Console. O render foi local. O recibo preserva as tentativas e a versão do repertório. A base do workspace recebeu a evidência da passagem sem pico e da leitura a 300 px, vinculada ao checksum deste MP4. [Preços da Anthropic](https://platform.claude.com/docs/en/about-claude/pricing)

## Revisão após o feedback sobre sentido e custo

A cartela confirma a categoria tarde. Antes dela, a abertura dedica cerca de dez segundos ao eclipse, a película apresenta vinhetas de ficção científica e a órbita volta como assinatura. O motivo aparece em três funções, mas a passagem entre elas raramente mostra um objeto causando a mudança seguinte. O espectador pode ler a peça como um teaser de ficção científica até a cartela explicar que se trata de uma mostra. A avaliação anterior mediu legibilidade e brilho e superestimou o que esses indicadores dizem sobre a qualidade do anúncio.

No Pin do Galileo, o fragmento no quadro de 1,25 s participa do nome legível no quadro de 5 s. Na ÓRBITA, um princípio comparável é fazer os elementos que já ocupam os fotogramas convergirem para a própria palavra “curta” e fazer esse quadro carregar a assinatura. A categoria aparece desde a abertura para situar o convite. A revisão procura o primeiro momento em que a oferta faz sentido, o que cada mudança acrescenta e o que continua reconhecível. [Galileo](https://www.pinterest.com/pin/505740233168774773/)

Das 81 chamadas do Opus, a leitura do recibo encontrou 21 pedidos de inspeção da timeline e 16 de prévia por sequência. Doze prévias foram feitas nas duas mesmas revisões, com tempos parcialmente diferentes. A gravação de 539.599 tokens no cache custou US$ 2,697995, cerca de 55% do valor total medido. A Clicko agora fixa o briefing em um ponto próprio do cache, preserva a parte já enviada entre prévias e devolve o resultado anterior para pedidos idênticos quando a timeline e o contexto continuam iguais. Mudanças na timeline e pedidos diferentes continuam acessíveis ao diretor. A redução de custo na Anthropic ainda depende de uma nova medição. [Cache de prompts da Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

## Prova editorial local após a reprovação

O proprietário avaliou que o anúncio perdeu o sentido. Esse comentário foi gravado na evidência do projeto, que passou para “revision requested”. Repetir o recibo de exportação preserva essa avaliação. A sessão seguinte no mesmo projeto recebe o comentário no contexto. A prova de brilho e legibilidade continua documentada no artefato, com a aprovação editorial pendente.

Foi produzido um animatic de 10 s, escrito por Codex e executado no EffectCraft com US$ 0 de API. A duração e o layout simplificado foram escolhas para testar a sequência. O nome e a categoria aparecem na abertura. Um ponto laranja deixa o motivo orbital, atravessa o espaço entre os dois quadros e acende os prédios em sequência. Os quadros convergem para a caixa que recebe “curta”. A caixa sobe e recebe “ÓRBITA”, seguida do convite. A relação pretendida é que mundos de ficção científica cabem nos filmes reunidos pela mostra.

| Intervalo | Ação a conferir | Evidência que a contradiz |
|---|---|---|
| 0–1,4 s | Nome e categoria situam a peça, ponto percorre o primeiro quadro | Texto cortado ou ponto surge na cidade sem passagem |
| 1,4–2,6 s | Ponto cruza a cidade e os prédios clareiam na sua passagem | Todos os prédios já acesos antes da passagem |
| 2,85–4,3 s | Quadros se concentram e a palavra “curta” recebe uma caixa | Elementos desaparecem e outra caixa aparece em posição sem ligação |
| 5,6–6,51 s | A mesma caixa sobe para a assinatura e o convite entra | Salto de posição ou título ilegível durante o pouso |

As leituras de causalidade e de atenção do conselho foram usadas como inferências operacionais nesta revisão, sem execução de agentes adicionais. A leitura de causalidade pede uma consequência visível para cada passagem. A leitura de atenção pede que o público reconheça o evento enquanto observa a ação. A primeira orientou o sinal e o acendimento da cidade. A segunda orientou o nome e a categoria na abertura. O risco é a metáfora dominar o anúncio. O teste de compreensão permanece a descrição espontânea por um espectador do que está sendo anunciado e do convite final. Os quadros observados verificam execução e leitura. O repertório visual e o som da peça ainda exigem desenvolvimento.

O render tem 240 quadros e passou pela detecção de pico de brilho. O projeto anterior permaneceu na revisão 3. A primeira repetição local falhou com o serviço Docker desligado, que foi reaberto para concluir a prova. O arquivo e o projeto editável ficam em `C:/Users/edugu/OneDrive/Documentos/res/output/clicko-orbita-prova-editorial`. A mudança de cache, a reutilização de inspeções e o registro de reprovação foram verificados com respostas de modelo simuladas. As provas de 30 e 45 s passaram após a reabertura do serviço. A prova reutiliza a faixa anterior, com nível baixo e sem desenho de som específico para o sinal. A qualidade e a economia em uma nova sessão paga ainda não foram medidas.
