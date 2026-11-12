# Clicko: edição nativa com os Crafts

A entrada de Motion Design abre EffectCraft. A de vídeo abre FilmCraft, e as de edição e composição de imagem abrem PhotoCraft. São projetos independentes, com funcionalidades semelhantes às dos editores Adobe. O projeto antigo permanece disponível para conversão; a Clicko arquiva a origem e mostra os pontos que não conseguiu converter.

| Bloqueio encontrado | Alteração |
|---|---|
| O canvas simplificado era o caminho padrão. | Removidos os dois editores paralelos da aplicação. Geração de mídia, biblioteca e preparação de anúncios continuam disponíveis. |
| O planejador antigo exigia a montagem canônica e filtrava comandos por nome, removendo scripts, expressões e operações nativas. | Novas solicitações do Claude vão para o Craft. O modelo pesquisa o catálogo em execução e carrega as assinaturas dos comandos de que precisa. |
| Planejamento e aplicação em uma única resposta, sem acesso ao resultado. | Na API direta da Anthropic, o modelo pode inspecionar, executar lotes, renderizar quadros e corrigir um rascunho temporário antes de concluir. |
| A prévia por IA passava pelo prazo genérico da ponte HTTP. | A sessão nativa recebe prazo próprio e usa respostas incrementais da Anthropic. O mesmo identificador não dispara outra cobrança. |
| HyperFrames aparecia como opção de projeção e recomendação, embora já não estivesse instalado. | Retirados a rota, a configuração, o código arquivado do adaptador e a recomendação ativa. Recibos e relatórios antigos conservam seus nomes originais. |

O EffectCraft carregado localmente expôs 663 comandos para a sessão, incluindo script.run e prop.setExpression. A prova executou script.run com dois quadros-chave de posição, conferiu que os quadros 0 e 18 diferiam e exportou 24 quadros H.264 em 240 × 320. É uma prova do motor, não uma avaliação de qualidade do anúncio. O teste de integração usou respostas simuladas do Claude para executar, ver, corrigir, salvar e verificar repetição idempotente. **Gasto real de API nesta etapa: US$ 0.**

A sessão usa uma cópia do projeto com materiais vinculados. A Clicko controla caminhos, importação de arquivos e a revisão a salvar. Scripts ficam dentro do motor isolado. A sessão tem prazo de execução e teto de US$ 1,50, além dos limites já definidos por conexão e workspace. Uma solicitação cujo resultado de cobrança é incerto mantém a reserva. A reserva é diferente de um gasto medido. Não aumentar limites para compensar uma reserva sem conciliar o histórico.

Os quadros permitem inspecionar composição e legibilidade, mas não confirmam ritmo, movimento contínuo ou sincronismo de áudio. O modelo não recebe o vídeo e o áudio completos nessa sessão. Geração de filmagem, narração, fontes ausentes e efeitos que o motor instalado não suporta continuam dependendo de material ou capacidade adicional. Provedores sem o protocolo direto da Anthropic continuam com proposta de comandos em uma etapa.

Próximo ensaio: abrir um projeto EffectCraft com uma referência e materiais autorizados, usar a conexão direta Anthropic e comparar a prévia/render final com a referência. Antes da chamada, conferir a reserva incerta e o saldo do modelo e da conexão. Registrar custo, tempo e problemas de imagem e som por trecho.
