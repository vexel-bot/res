# Geração audiovisual integrada OpenRouter — 07/11/2026

A Clicko agora pode solicitar vídeo e narração pela conexão OpenRouter já cadastrada, sem chaves no navegador. No editor, “Gerar cenas e narração” descobre modelos e vozes, permite escolher um orçamento por produção e acompanha os materiais até a biblioteca e o documento.

O contrato da edição automática foi corrigido: o Opus recebe o schema executável de animação. Keyframes abreviados inequívocos são convertidos antes da validação estrita; propriedades desconhecidas continuam rejeitadas. A direção editorial preserva narração, origem dos clipes e IDs, descreve o tempo relativo das animações e recomenda entrada, sustentação e saída legíveis.

A pesquisa de 15 vídeos e suas limitações está em docs/research/2026-11-07-claude-video-motion.md. Aplicações: narração medida guia o corte, alterações locais preservam materiais, motion organiza relações, e a revisão ocorre após o render. O teste curto não certifica desempenho ou sincronismo de um vídeo longo.

Confiabilidade: identidade do pedido e intenção de submissão persistidas antes do POST externo; replay evita repetir cobrança; saldo externo e reserva mensal são conferidos; orçamento por produção é cumulativo; respostas desconhecidas permanecem bloqueadas para conciliação. A biblioteca guarda proveniência e IDs do provedor. Uploads continuam em streaming; JSON de edição tem buffer e limite próprios.

Limitações: calculadoras para preços por token de vídeo ainda não foram implementadas e esses modelos são recusados. O custo de fala é estimativa tarifária até a conferência de saldo. As gerações não são disparadas ao abrir a tela. Usar as rotas autenticadas da aplicação para criação e consulta.

Validação: 8 regressões de animação, 5 testes de mídia e 2 testes do proxy; TypeScript sem erros. Os testes de mídia cobrem orçamento, replay, resultado desconhecido, importação e preservação de referências. O registro do teste real fica no pacote de saída do vídeo.
