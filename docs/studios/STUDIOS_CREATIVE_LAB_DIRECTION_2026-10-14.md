# Clicko Studios — bancada de experimentação criativa

Data: 14/10/2026. Status: proposta histórica, superada pela direção de departamento criativo; não é uma interface implantada.

> A decisão posterior do usuário define Studios próprios, operados por agentes, com conteúdo como prioridade e anúncios como segunda frente. O cliente define objetivo, escolhe direção e revisa a entrega; edição e controles técnicos permanecem internos. A KLIC encaminha contexto e não cria a entrega. As sugestões abaixo de bancada técnica para o cliente e de KLIC criadora não orientam o próximo design. A direção vigente e o acervo estão em [Departamento criativo](knowledge/creative-department-2026-10/README.md). O histórico do pull e dos conflitos continua válido no momento registrado.

Esta proposta substitui a direção dos dois protótipos anteriores. Mantém os dois resultados escolhidos pelo usuário: campanhas e produção recorrente de conteúdo. O novo pedido exige uma experiência visual moderna, com uma visão científica e laboratorial do processo, acessível a profissionais de marketing e responsáveis por marcas.

## 1. Atualização do time: o que foi efetivamente recebido

- Remoto: `https://github.com/vexel-bot/res.git`.
- A busca em 14/10 encontrou um novo commit no período de 13–14/10, na branch `codex/klic-atualizacao-20260823`.
- Commit: `e6a2ba45d4bd1f8325395cd700420f900271f155`, de 13/10/2026 às 20:52:17 -03:00, “Evolui plataforma Clicko e arquitetura central da KLIC”.
- `origin/main` permanece em `9399f88cf`, de 01/10. Não foi encontrada uma atualização de 14/10 nas branches anunciadas pelo remoto no momento da consulta.
- Foi executado `git pull --ff-only origin codex/klic-atualizacao-20260823` no checkout `C:/Users/edugu/Downloads/res-team-update-20261014`, branch local `codex/team-update-20261014`, agora com tracking da branch do time. O checkout está limpo e seu HEAD é idêntico ao remoto consultado.
- O checkout Craft ativo, `C:/Users/edugu/Downloads/res`, permanece na branch `codex/craft-studios-active`, revisão `69b83380e`. Os arquivos locais e os fontes integrais Craft foram preservados.
- A simulação de merge identificou **51 arquivos com conflito**. Nenhum merge foi aplicado ao checkout ativo. A integração entre a plataforma do time e o trabalho Craft permanece pendente; o pull em checkout separado não significa que os novos contratos já funcionem juntos.

### Evidências que orientam o produto

A atualização inclui a KLIC central, contexto de marca isolado por cliente, autenticação, governança, integrações sociais e um sistema visual claro/escuro. `src/components/CreativeWorkspace.css` traz superfícies neutras, coral Clicko e azul associado à KLIC; `ThemeSystem.css` e `theme/appearance.ts` concentram tema e assets oficiais.

As telas Imagem e Vídeo do time exibem “em construção”. Portanto, esses componentes não substituem os motores nem o trabalho Craft existente. A futura união precisa conectar a plataforma atualizada aos contratos reais de documentos, assets, jobs e permissões.

Fontes internas consultadas no checkout atualizado: `docs/klic-central-architecture.md`, `docs/CLICKO_EVOLUTION_2026-10-03.md`, `CLICKO-BRAND.md` e os componentes/temas citados acima.

## 2. O que os Studios serão

Um ambiente em que o usuário desenvolve e verifica uma ideia de comunicação com materiais, versões e decisões rastreáveis. A mídia ocupa a maior parte da tela; a bancada mantém ao alcance as referências, a intenção, as possibilidades e a versão escolhida.

O usuário deve conseguir responder cinco perguntas na mesma experiência:

1. O que queremos comunicar e para quem?
2. Em quais informações e materiais estamos nos apoiando?
3. O que estamos variando neste experimento?
4. O que mudou no resultado e por que estamos escolhendo esta versão?
5. O que aprendemos depois de usar o conteúdo?

A complexidade fica disponível para inspeção em níveis. O primeiro nível apresenta decisões de comunicação. O segundo revela roteiro, cenas, conteúdo visual, voz, música e adaptação. O terceiro abre edição precisa, procedência e operações técnicas quando necessários.

## 3. A visão científica precisa aparecer no comportamento

| Conceito | Tradução para o usuário | Comportamento esperado |
| --- | --- | --- |
| Hipótese | “Vamos testar uma abertura centrada no benefício.” | Registrar a intenção sem apresentar previsão como fato. |
| Materiais | Produto, referências, identidade da marca e informações verificadas | Mostrar origem e validade; distinguir dado da marca de sugestão da IA. |
| Variável | Abertura, mensagem, cenário, estilo ou ritmo | Declarar o que muda e o que permanece fixo. |
| Experimento | Duas ou mais abordagens comparáveis | Preservar a base e criar variantes vinculadas; permitir exploração livre sem chamar toda comparação de A/B. |
| Verificação | Texto legível, produto fiel, duração, direitos e contexto de marca | Mostrar verificações comprovadas, pendências e necessidade de revisão humana. |
| Decisão | “Escolher esta versão para continuar.” | Registrar a escolha, justificativa e revisão do resultado. Seleção não equivale a aprovação ou publicação. |
| Aprendizagem | Dados observados depois da publicação | Relacionar resultado, período e fonte. Exibir “ainda sem dados” quando não houver mensuração. |

O caráter laboratorial decorre de hipóteses, controle de mudanças, procedência e repetibilidade. Indicadores de qualidade arbitrários, previsões de conversão sem evidência e animações decorativas de “processamento científico” não representam esse método.

## 4. Composição da experiência

### Bancada como tela principal

- **Cabeçalho discreto:** cliente, projeto/campanha e versão; navegação consistente com a plataforma atualizada.
- **Área central dominante:** resultado atual com dimensão suficiente para avaliar imagem, cena ou peça. Comparação substitui temporariamente a prévia por duas versões lado a lado, ou alternância no celular.
- **Materiais próximos ao resultado:** produto, identidade, referências e fontes. São amostras reutilizáveis e inspecionáveis, com miniaturas e vínculo ao contexto da marca.
- **Instrumentos contextuais:** controles relevantes à intenção atual. Por exemplo: abertura, promessa, CTA, atmosfera, cenário, apresentação do produto e ritmo. O instrumento mostra o efeito solicitado e os limites de preservação.
- **Bandeja de experimentos:** versões com miniatura e descrição do que mudou. Deve permitir retomar uma linha de exploração sem perder as anteriores.
- **KLIC contextual:** pedido em linguagem natural conectado à seleção atual. A IA propõe a alteração, explicita informações ausentes e informa se preparou, executou ou encontrou um bloqueio.
- **Registro do processo sob demanda:** referências utilizadas, revisão da marca, operações realizadas, provedor/modelo quando houver, versões dos motores, execução, duração/custo efetivamente disponíveis e avisos.

O espaço de trabalho permanece contínuo. Criar, comparar e refinar são modos da mesma bancada. O acesso a campanha, biblioteca, aprovação e calendário utiliza os módulos compartilhados da plataforma.

### Entradas por intenção

Exemplos: “Apresentar um produto”, “Criar um anúncio”, “Explicar um benefício”, “Criar conteúdo para a semana”, “Transformar este material”. Imagem e vídeo continuam disponíveis como tipos de entrega dentro desses objetivos.

Uma primeira peça pode abrir diretamente na bancada com os materiais existentes. Quando faltar informação essencial, a KLIC pede apenas o necessário para a operação selecionada. Informações comerciais ausentes não são inventadas.

## 5. Exemplo concreto: campanha de lançamento

O usuário solicita um anúncio de um produto para Instagram. A bancada recebe o contexto do cliente, a fotografia do produto, referências autorizadas e a campanha existente.

A primeira exploração apresenta duas abordagens: benefício e demonstração de uso. Cada abordagem informa a intenção; ainda não existe uma “vencedora”. O usuário escolhe benefício para continuar e testa duas aberturas preservando produto, oferta e duração.

Na comparação, vê a peça e a alteração textual lado a lado, com as verificações disponíveis. Pode pedir “mais humano”, “mostre o produto antes” ou “mantenha a cena e mude apenas a primeira frase”. Alterações incompatíveis com esse limite são explicitadas antes de executar.

A versão escolhida origina adaptações vinculadas para formatos. O envio para revisão usa a aprovação compartilhada. Depois da publicação, os dados reais podem informar um novo experimento. A recomendação da IA e o desempenho medido permanecem distinguíveis.

## 6. Exemplo concreto: produção recorrente

O pedido “conteúdo para a semana” gera propostas editoriais conectadas ao contexto existente. Cada peça tem sua bancada, materiais e versões; a coleção mantém a coerência da série.

O usuário pode fixar a identidade da série, variar o assunto ou a abertura e reaproveitar uma receita de produção. A receita inclui instruções e vínculos de contexto; duplicá-la atualiza o cliente e a campanha, sem herdar segredos ou informações de outra marca. Agendamento e mensuração continuam nos módulos responsáveis.

## 7. Direção visual a explorar no próximo protótipo

O protótipo deve demonstrar uma bancada aberta com resultados visuais grandes, miniaturas reais ou claramente ilustrativas, referências próximas e controles compactos. O tom é preciso, contemporâneo e imersivo. A marca e os temas devem partir da atualização do time, com coral para ações Clicko e o azul da KLIC usado com parcimônia.

Hierarquia: resultado → variantes → controles da experiência atual → materiais/contexto → rastreabilidade. Espaçamento e contraste devem separar a mídia dos instrumentos sem encher a tela de caixas. Nomes como “Abertura”, “Ritmo” e “Referências” são mais úteis ao público que termos de renderização ou uma árvore de nós como primeira interação.

As duas telas a prototipar primeiro são **exploração na bancada** e **comparação de versões**. Deve ser possível testar a experiência com uma pessoa que trabalha com marketing: ela precisa compreender o resultado, formular uma alteração limitada e reconhecer o que mudou sem aprender a usar uma timeline.

Os protótipos anteriores permanecem como histórico. Esta proposta não autoriza tratar aquelas interfaces como direção final nem aplicar uma reforma global do frontend.

## 8. Referências externas e adaptação

Consulta às páginas públicas oficiais do Higgsfield em 14/10/2026. São descrições do fornecedor, não uma qualificação técnica ou um teste de conta autenticada.

- [Higgsfield Canvas](https://higgsfield.ai/canvas-intro): reúne referências, instruções e resultados conectados, com variantes e receitas reutilizáveis. A adaptação Clicko é a continuidade da experimentação e a procedência das peças; a manipulação de nós permanece uma possibilidade avançada.
- [Guia de escolha de ferramentas Higgsfield](https://higgsfield.ai/creator-hub/help-center/tools/which-higgsfield-tool-should-i-use): distingue produção de anúncios, direção cinematográfica, workflows e planejamento por conversa. Marketing Studio e o planejamento por intenção são referências mais próximas do público Clicko.
- [Guia Cinema Studio](https://higgsfield.ai/creator-hub/help-center/tools/how-do-i-use-cinema-studio): referências, elementos reutilizáveis e direção da cena ajudam a pensar na preparação do resultado. No Clicko, os controles iniciais devem falar em atmosfera, ritmo e mensagem; controles profissionais podem ser contextuais.

A proposta de bancada é uma inferência de design para o Clicko. Não é cópia da interface Higgsfield, integração com o fornecedor ou promessa de acesso aos modelos anunciados por ele. O navegador automatizado não conseguiu abrir a página para inspeção visual nesta consulta; a pesquisa se baseia no conteúdo público das páginas acima.

## 9. Relação com os três projetos Craft

PhotoCraft, FilmCraft e EffectCraft permanecem integralmente importados, com as revisões auditadas. São responsáveis pela edição, composição e renderização nativa. Os provedores generativos e a KLIC possuem responsabilidades distintas: gerar materiais e planejar/solicitar operações conforme contratos disponíveis.

A bancada apresenta uma camada de produto sobre os documentos nativos. Cada variante precisa referenciar a revisão de origem, materiais, mudanças solicitadas, revisões resultantes e artefatos renderizados. A edição precisa abre o mesmo documento usado pela IA, com histórico e controle de concorrência. Selecionar ou comparar uma variante não pode silenciosamente alterar o original.

A nova camada de experimentação ainda precisa ser implementada. Os contratos Craft existentes não constituem, por si só, o modelo completo de hipóteses, experimentos e aprendizagem descrito aqui. A validação de LLMs reais permanece adiada por decisão do usuário.

## 10. Integração técnica pendente após o pull

1. Conciliar sessão autenticada, usuário, workspace e escopo de cliente entre o core do time e o backend de documentos Craft; nenhuma identidade pode ser confiada somente a campos enviados pelo navegador.
2. Conciliar os dois sistemas de rotas preservando os acessos de criação, biblioteca, revisão e reabertura de projetos; direcionar os Studios ao novo ambiente.
3. Incorporar temas, assets oficiais, contexto da marca e handoffs da KLIC sem reativar os editores antigos nem trocar os contratos nativos por componentes “em construção”.
4. Resolver os conflitos de dependências, proxy, servidor e tipos; manter streaming, cancelamento, revisão esperada e erros explícitos.
5. Validar login, isolamento de clientes, criação, salvar/reabrir, operação manual/IA, biblioteca, revisão e publicação nos módulos responsáveis. Executar novamente a integridade dos fontes Craft antes de ativar a versão unificada.

O checkout separado torna a atualização do time concreta e inspecionável. A ativação de uma versão unificada só pode ser reportada depois da resolução desses contratos e da validação dos fluxos.
