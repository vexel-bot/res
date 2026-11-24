# Claude editando vídeo e o próximo teste da Clicko

13/11/2026. Análise dos dois links enviados, do corte revisado da ÓRBITA e de fontes locais. Gasto adicional de API: US$ 0.

## O que as duas demonstrações mostram

| Fonte e trecho | Evidência | Aplicação na Clicko |
|---|---|---|
| Matheus Gobbi, 0:08–0:16 | A tela apresenta quatro etapas e separa os vídeos brutos das referências em pastas. | Separar material de produção, referência visual e resultado de revisão. Registrar o propósito de cada fonte antes de decidir os cortes. |
| Matheus, 0:26–0:38 | O Reel mostra ferramentas distintas para motion, cortes, transcrição e estudo de referências. | Oferecer ferramentas por função. O roteiro de trabalho pode ser reaproveitado com os Crafts e os serviços da Clicko. |
| Matheus, 0:51–0:56 | O exemplo transforma referências em um guia e mostra revisão do gancho antes da entrega. A cadência e o estilo de legenda da tela pertencem àquele guia. | Guardar preferência por projeto ou marca. Usar o briefing e o tipo de material para decidir quando essa preferência cabe. |
| Maestros da IA, 0:11 e 0:52 | A peça usa um gráfico para explicar a relação entre capítulos e trilha. Depois intercala imagem de edição manual e tipografia de apoio. | Escolher uma imagem que demonstre a ideia do trecho. Dividir o som e os elementos visuais por função editorial. |
| Maestros da IA, 3:27 e 4:52 | O quadro mostra pontos no rosto e um indicador de rastreamento. Outro trecho mostra avatar e uma representação do áudio. | Dar ao diretor medições de tempo e posição com origem identificável. Confirmar o resultado renderizado quando um efeito depender de rosto, fala ou posição. |
| Maestros da IA, perto de 5:37 e 6:01 | A peça exibe um quadro de conferência com amostras e, depois, o pedido estruturado que orientou o trabalho. | Ligar revisão à versão do vídeo e registrar objetivo, público e restrições num briefing executável. |

Fontes: [Reel do Matheus Gobbi](https://www.instagram.com/reel/DfmkaDZuTCl/) e [vídeo de Maestros da IA](https://www.youtube.com/watch?v=WuzMxEKJHkQ). Inspeção visual por amostras, com reprodução muda. O player falhou em algumas buscas de tempo e essas capturas foram descartadas da análise. Os trechos verificados não estabelecem continuidade de toda a peça, inteligibilidade ou qualidade da mixagem.

A descrição de Maestros da IA relata um pedido inicial, 3 h 48 min de produção e 91 cenas. Atribui a direção ao Fable 5.2, com recursos especializados para voz, avatar, animação, rastreamento, transcrição, trilha e render. O tempo e as etapas são declarados pelo criador. Não há log bruto, custo comparável ou execução controlada com o Opus na Clicko. O vídeo demonstra uma produção longa com ferramentas e insumos preparados. [Descrição e capítulos do vídeo](https://www.youtube.com/watch?v=WuzMxEKJHkQ).

O processo do Matheus converte gosto em instruções recuperáveis. O exemplo do Fable converte o briefing em tarefas executáveis. Na Clicko, essas duas ideias se encontram quando a IA consegue localizar a ação no bruto, escolher como mostrá-la, renderizar uma versão e conferir se a edição preservou a ação e seu resultado. Uma técnica pode ser ensinada com instrução, exemplo e contraexemplo consultados conforme o trabalho. [Documentação sobre skills da Anthropic](https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills).

## O que o material revelou na Clicko

As referências visuais, a leitura de fontes registradas, a transcrição quando disponível, a prévia temporal, o rascunho e a exportação já existem. A última ÓRBITA local preservou a montagem central do Opus. Seu ponto fraco vai além da assinatura: excertos previamente preparados contêm cortes próprios que chegam à timeline sem uma decisão editorial explícita.

Implementei a ferramenta `scan_source_shots` no diretor dos Crafts de vídeo. Ela lê mídia registrada no projeto, devolve candidatos de mudança visual em tempo de fonte e registra o resultado no recibo. O diretor pode examinar os momentos relevantes com `inspect_source_media` e `review_clip`. O limiar local é de triagem. Movimento rápido, luz e cortes suaves podem exigir inspeção adicional. A janela de até 30 s é paginável e independe da duração do anúncio.

| Material já existente | Resultado do teste local | Interpretação editorial |
|---|---|---|
| ÓRBITA revisada, 18,005 s | Seis candidatos em 5,00, 7,00, 7,37, 9,00, 10,00 e 11,00 s. | Em 7,33–7,37 e 9,96–10,00 s, os quadros confirmam trocas internas adicionais, além das entradas principais do corte. O centro da peça perde continuidade quando essas trocas entram sem função definida. |
| Excerto Travessia, 3 s | Um candidato em 2,625 s. | Os quadros mostram a passagem das pessoas em primeiro plano para outro enquadramento. O arquivo é fonte de mais de um plano, ainda que tenha sido preparado como um único excerto. |
| Captura real da divisão de clipe, 6,917 s | Zero candidatos. | A imagem muda de um clipe para dois. É a prova central da demonstração e ocorre dentro da mesma tomada. Uma lista de cortes sozinha não localiza o gesto. |

As fontes e medições têm hashes no [recibo local](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-quality-cycle-2026-11-13/referencias-novembro/varredura-local.json). As transições foram examinadas nos [quadros de conferência](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-quality-cycle-2026-11-13/referencias-novembro/candidatos-verificados.jpg). A ferramenta local não classifica ação, áudio ou qualidade artística.

Também varri os sete excertos disponíveis para a ÓRBITA. Todos produziram pelo menos um candidato, oito no total. O inventário guarda os intervalos para conferência antes do próximo corte. O significado da troca foi conferido apenas nas amostras anotadas acima. [Inventário dos sete brutos](C:/Users/edugu/OneDrive/Documentos/res/output/clicko-quality-cycle-2026-11-13/referencias-novembro/orbita-inventario-de-planos.json).

A verificação local passou com corte de tempo conhecido, janela contínua e integração no FilmCraft real. Na integração, um diretor simulado recebeu o mapa da fonte, consultou imagens e transcrição, aplicou a edição e solicitou a exportação. Isso confirma a ligação entre ferramenta e editor. A escolha criativa do modelo em material inédito permanece uma etapa de avaliação.

## Sequência de implementação e prova

| Ordem | Trabalho no fluxo | Como medir |
|---|---|---|
| 1 · Identificar o material | Mapear planos candidatos e intervalos úteis. Somar transcrição com tempos quando há fala, OCR quando a informação está na tela e rastreamento quando importa preservar um objeto. Indicar quais fontes faltam. | Verificar tempos contra o bruto e medir acertos e falsos positivos por sinal. Incluir eventos importantes dentro de um plano contínuo. O mapa de cortes foi implementado nesta rodada. |
| 2 · Escolher a edição | Para cada batida, registrar o que o espectador deve entender, o trecho que sustenta a escolha e o que muda na tela. Recuperar fichas por função. Escolher entre manter a ação, cortar, reframar ou criar uma composição. | Fazer a mesma pergunta de compreensão antes da preferência. Uma cena passa quando ação e consequência são localizáveis na prévia. Preparar um exemplo que pede o efeito e outro em que ele esconde a prova. |
| 3 · Montar e revisar por trecho | Usar a timeline real e as operações comprovadas do Craft. Verificar quadros antes, durante e depois da ação, e escutar o mix nas passagens relevantes. Manter resultados e fonte editável vinculados à revisão. | Rejeitar cortes que eliminem uma etapa essencial, textos ilegíveis, identidade trocada e áudio exigido ausente. Medir tempo de revisão, reparos e intervenção. |
| 4 · Provar transferência | Usar a mesma mídia e o mesmo modelo em dois braços, com o fluxo atual e com evidência temporal organizada. Iniciar com ÓRBITA, demonstração de interface e uma filmagem inédita de produto em ação. Ampliar depois para entrevista, narrativa longa e híbridos. | Avaliar antes/depois em pares e registrar cada dimensão. Manter o gabarito fora do contexto. A gravação inédita da luminária segue pendente. A comparação com modelo real precisa de autorização de gasto em etapa própria. |

O próximo teste da ÓRBITA deve preservar a abertura e a assinatura locais e remontar apenas o miolo com planos limpos: estabelecer o mundo, mostrar uma ação ou descoberta e fazer a mudança justificar a passagem. No caso da interface, a prova deve manter o gesto e a confirmação visíveis. A versão atual passou no alinhamento da película, mas o teste anterior de transferência acertou só um dos dois casos. A lição continua candidata.

Há duas referências de pesquisa para o desenho dos testes. Cassette-Editor descreve alterações verificadas na timeline e erros localizados para revisão. Timeline-Bench separa entrega técnica, aderência ao briefing e qualidade julgada. Ambos são preprints consultados no resumo. Seus resultados não estimam a probabilidade de sucesso da Clicko. [Cassette-Editor](https://arxiv.org/abs/2610.37690) · [Timeline-Bench](https://arxiv.org/abs/2609.35143).
