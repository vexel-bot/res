# Changelog

## Não publicado — 2026-10-24

### Revisão incremental da navegação e experiência dos Studios

- “Alterar Studio” substituído no desktop por categorias e ferramentas sempre
  visíveis; dois seletores compactos no tablet/celular. Nove rotas, permissões,
  proteção de saída e descoberta honesta de recursos futuros preservadas.
- Gerar imagem vem após ideia/formato/estilo, antes das opções recolhidas;
  autorização e bloqueio do provedor indisponível continuam reais.
- Reprodução do Motion na barra superior e altura inicial da timeline adaptada
  ao notebook; timeline ainda redimensionável por ponteiro e teclado.
- Um acesso KLIC no cabeçalho dos Studios. Desktop largo reserva espaço lateral;
  janelas menores alternam temporariamente para a conversa existente, sem
  desmontar o editor. Corrigida a largura herdada que cortava o Fechar no celular;
  estado acessível e retorno do foco verificados no navegador.
- Projetos de vídeo e renderer local carregam independentemente do preflight de
  IA. Falhas ou serviços não confirmados não habilitam geração artificialmente.
- QA no DEV com PNG/MP4 reais, recuperação dos projetos salvos, quatro tamanhos
  de tela, teclado, temas e KLIC. Sem provedores pagos, backend novo, push ou deploy.
- Relatório atualizado: `CLICKO_REVISAO_EXPERIENCIA_STUDIOS_2026-10-24.md`.

### Simplificação e organização dos Studios

- Ajuste posterior de dimensões do Gerar Imagem: ações em uma barra única,
  formulário inicial mais largo, espaçamentos menores e opções recolhidas lado
  a lado no desktop. Seções abertas usam largura completa; móvel mantém coluna
  única e entrada de texto legível. Nenhum contrato ou processamento alterado.

- Inventário funcional antes das mudanças; navegação única agrupada preserva
  rotas, permissões, ferramentas adicionais e descoberta de opções futuras.
- Workspace compartilhado com prévia central, materiais/camadas, inspector
  contextual e timeline inferior redimensionável; painéis por etapas no móvel.
- Motion e composição de imagem mantêm comandos, versões, keyframes, crop,
  ajustes, originais e exportação. Seleção do canvas considera letterboxing.
- Montagem de vídeo preserva cortes, áudio, títulos, efeitos, faixas, keyframes,
  recuperação e MP4. Projetos/ajuda foram recolhidos; prévia e timeline cabem na
  janela do notebook. Troca de documento protege a montagem não salva.
- Briefings de imagem/vídeo usam opções progressivas e defaults locais
  revisáveis. Publicidade prioriza produto, público e resultado, reutilizando
  os editores e materiais existentes, sem simular publicação de campanhas.
- Acesso discreto à KLIC global e atalhos de salvar/desfazer/refazer; não foram
  alterados Gemini, voz, cotas, credenciais, backend ou contratos de API.
- QA real no navegador DEV encontrou e corrigiu colisão de classe com CSS de
  progresso, espaço insuficiente da prévia no notebook e sincronização da rota
  após salvar. Capturas e artefatos ficam privados em `.codex-runtime`.
- Relatório distingue regressões técnicas, fluxos reais locais e dependências
  de IA/Craft ainda indisponíveis. Sem APIs pagas, push ou deploy.

## Não publicado — 2026-10-23

### Auditoria funcional e audiovisual

- Relatório completo do estado real dos Studios, agentes, modelos, qualidade
  artística, motores Craft e roadmap; sem afirmar homologação de produção.
- Novos instrumentos de sessão DEV real, composição/render/export, edição por
  comando, preservação de fontes/versões, reinício e análise dos arquivos gerados.
- Triagem JUnit normaliza rootdir conhecido e não trata testes não coletados como
  resolvidos; evidências brutas e artefatos de QA continuam privados.
- Node, tipagem e build aprovados; Python completo do backend permanece com
  277 falhas e 112 pulados, Ruff global com 323 achados e npm audit com 1 alta.
- Nenhum redesign, novo modelo, chamada paga ou mudança de credencial nesta
  auditoria; homologação atual pelo navegador continua bloqueada.

### Modo desenvolvedor local isolado

- `dev:local` provisiona identidade, cliente, workspace e plano Desenvolvimento
  reservados e persistentes, sem conta comercial ou duplicação em reinícios.
- Sessão opaca do servidor, expiração de 8 h, cookie HttpOnly/SameSite Strict;
  identidade não é concedida por cabeçalhos ou cookie inventado.
- Bloqueios por ambiente, bundle, listener, endereço real da conexão, Host,
  Origin, Fetch Metadata, proxy e isolamento de arquivos; produção preservada.
- Cliente DEV reconhecido na governança e na ponte JWT Express/FastAPI, sem
  remover escopo, permissões, licenças ou validações dos Studios.
- Dados, conversas, arquivos e logs privados em `.codex-runtime/clicko-dev`;
  `dev:reset` exige confirmação e arquiva somente o perfil DEV parado.
- Indicador DEV e estado real dos serviços/modelos; pagamentos, integrações e
  provedores pagos bloqueados, sem alterar credenciais existentes.
- Corrigidos dois problemas encontrados no teste real: histórico atrasado que
  rebaixava tarefa concluída e contexto React duplicado no carregamento HMR/lazy
  do Vídeo. A correção de contexto fica restrita ao HMR, sem cache global em produção.
- Provas de PNG/MP4, edição contextual KLIC e recuperação por sessão DEV real;
  relatório distingue testes técnicos de homologação visual ainda pendente.

## Não publicado — 2026-10-22

### Etapa 3 · validação e correções dos Studios

- KLIC encaminha desfazer ao plano de restauração da versão salva anterior;
  revisão, locks, seleção, idempotência e versões preservados, sem inferência.
- Pedidos incompletos de cor/título pedem o valor necessário, sem adivinhar edições.
- Links de projeto não recuperam rascunhos/operações de outro documento; backup preservado.
- Motion com erro acionável, orientação de escopo e controles avançados sob demanda;
  ajustes responsivos sem reconstrução da interface.
- Novas regressões e prova PNG → Motion/Vídeo com FFmpeg real; cenário KLIC de
  15 s ampliado, duas exportações, persistência após reinício e playback HTML5.
- Relatório `CLICKO_ETAPA3_HOMOLOGACAO_STUDIOS_2026-10-22.md` distingue validação
  técnica de UI autenticada, esta adiada pelo usuário. Modelos/Craft não homologados.

### Acesso direto à prévia local

- `dev:local` passa a abrir dashboard e módulos sem login, a pedido do usuário,
  reutilizando o contexto de desenvolvimento existente em loopback e dados isolados.
- `CLICKO_LOCAL_REQUIRE_LOGIN=true` permite testar novamente o login. Autenticação
  de produção, permissões, licenças e bloqueios de chamadas pagas preservados.
- Regressão de autenticação cobre recusa de cookies de prévia e cabeçalhos de
  identidade em produção, mesmo com a flag de desenvolvimento habilitada.

### Revisão de conclusão da Etapa 2

- Corrigidos comandos abreviados de cor fora da seleção, duração de uma animação
  que retimava o projeto e palavras de títulos entre aspas interpretadas como estilo.
- Validados metadados de cenas e navegação defensiva para rascunhos legados;
  cenas inexistentes e perguntas informativas não produzem edições globais.
- Escopo da seleção imposto no backend para regras/modelos e reaplicação segura;
  recibos antigos já comprometidos continuam retornando sem nova mutação.
- Planejamento em cancelamento bloqueia nova computação concorrente. Limites de
  IDs e ação de desmarcar o alvo deixam explícita a diferença entre camada/projeto.
- Corrigido timeout silencioso do controle local; três testes cobrem resposta
  demorada, serviço ausente e timeout real. Aceitação de revisão usa pasta própria.
- Nova rodada de testes, duas exportações de 15 s e persistência verificadas.
  Homologação visual autenticada, modelos e Craft continuam pendentes e documentados.

### Etapa 2 · experiência de produção assistida

- Contexto de camada selecionada percorre Studios → conversa KLIC → agente;
  regras de edição por cena/alvo, esclarecimentos e preservação dos outros elementos.
- Revelação de texto palavra por palavra no Canvas, still Pillow e FFmpeg,
  sem desmembrar destrutivamente o texto; fonte regular/negrito e conversão segura
  para o canvas legado. Corrigido alinhamento de palavras com uma linha de base comum.
- Edição de propriedade/quadro/valor/easing dos keyframes, duplicação independente,
  alinhamento/gradiente/sombra, navegação por cenas, biblioteca compartilhada e histórico
  dos agentes acrescentados à interface existente. Importação reutiliza a revisão salva.
- Tarefas apresentam usuário, seleção, eventos, limites e recibo da revisão aplicada;
  retiming também atualiza cenas e intervalos de revelação. Nenhuma migração nova.
- Ensaio determinístico de conversa KLIC com backend e renders reais, duas versões
  de 15 s, seleção restrita e preservação da primeira. Inferência real/Craft e
  homologação visual autenticada permanecem pendentes; sem instalação ou API paga.

- Orquestrador de produção local integra a conversa KLIC aos agentes audiovisual
  e visual, com configuração por papel, tarefas duráveis, delegações auditadas,
  revisão, aplicação idempotente e controle de revisão sobre as tabelas existentes.
- Adaptadores por regras identificados como determinísticos; conexão Ollama
  reutiliza o transporte LLM existente com schema JSON e apenas pesos locais já
  instalados. Nenhuma chave KLIC modificada ou API paga executada.
- Camadas canônicas locais de texto, forma e imagem; PNG com Pillow e integração
  ao FFmpeg canônico para MP4. Rotação por keyframes e easing acrescentados aos
  movimentos existentes; projetos e arquivos anteriores são preservados.
- Studios oferecem edição local de motion/imagem, prévia de edição, propriedades,
  timeline de camadas, importação, undo/redo local, histórico/restauração e exportação.
  Editor de vídeo e editores Craft anteriores continuam acessíveis.
- Auditoria de hardware, teste real de motion de 12 s com duas exportações,
  composição PNG e originais preservados documentados no relatório desta etapa.
  Geração cinematográfica, remoção de fundo, Craft compilado e inferência LLM
  real permanecem dependentes dos runtimes/modelos ausentes.

## Não publicado — 2026-10-21

### Etapa 1 · infraestrutura audiovisual

- Adicionado supervisor local (`dev:local/status/stop`) com dados de QA isolados, portas loopback, recusa de portas ocupadas, checagem de prontidão e encerramento dos processos próprios. As flags pagas ficam desligadas sem editar `.env`.
- UGC/animatic e validações sem voz reutilizam a descoberta central FFmpeg/FFprobe; o encoder H.264 disponível é selecionado, sem exigir libx264 quando há libopenh264.
- Node Gemini/KLIC e Cloud TTS passam pela admissão financeira interna do Studios, com a mesma reserva transacional USD, identidade da sessão, limite por modelo/empresa/membro, claim único, métricas de tokens e retenção de resultados incertos. Não há integração com faturas externas nem chamadas pagas nesta etapa.
- Limites mensais positivos e teto por modelo também exigidos nos caminhos pagos Python. Adaptador Python legado sem escopo/reserva falha fechado. Validação local de mensagem/anexos antecede consumo comercial no chat operacional.
- Recibos financeiros não são executáveis/repetíveis por workers. Tarifas reprificadas, reservas expiradas ou modelos aposentados não autorizam novas submissões. Sora aposentado e Veo Preview próximo da retirada possuem avisos oficiais versionados, sem substituição automática de modelo.
- Corrigidas as 11 ocorrências Ruff de formatação/imports/anotação. Benchmark visual ausente retorna 503 explícito, não 500 nem sucesso fictício.
- Acrescentados preflight Craft sem download, ensaio HTTP de importação/reexportação/reinício e testes gratuitos de ledger, concorrência, autenticação, idempotência, Gemini e TTS.
- Reexportação local real de 16 s e imagem recuperadas após reinício com mesmos checksums; MP4 H.264/AAC reproduzido até o fim no navegador. A montagem determinística não foi apresentada como geração por IA.
- Procedimentos de build Craft e migração futura para Redis/Celery Linux documentados. Docker, Redis e os três motores compilados continuam bloqueados nesta máquina; sem homologação distribuída, deploy ou push.
- Resultado geral: 860 aprovações, 292 falhas e 113 pulos; nenhum novo ID de falha frente à referência. As falhas do animatic e do indicador visual foram resolvidas. Núcleo audiovisual/financeiro: 89 aprovações/18 pulos; regressão financeira final: 21 aprovações. npm: 233 aprovações, mais 7 testes Craft separados. Ruff, tipagem e build aprovados; suíte global permanece não aprovada.

### Validação final e preparação de IA

- Referência publicitária de 18 s produzida por APIs, banco, armazenamento e FFmpeg reais: cortes, camadas, títulos, keyframes, fades, trilha e MP4 H.264/AAC. Não é geração por IA.
- Importação, reprodução e reexportação pela interface comprovadas em projeto local de QA; download final de 18 s em 1920×1080 validado por FFprobe.
- Corrigida recusa de `originalAudioEnabled` no payload da timeline; o renderizador respeita áudio original ligado/desligado, com testes reais de PCM.
- Corrigida estimativa Gemini para incluir tokens de raciocínio uma única vez. Continua estimativa por tarifa, não fatura nem tarifação multimodal completa.
- Vite atualizado de 6.4.3 para 6.4.5 para corrigir advisory Windows, sem trocar a linha principal; npm não aponta altas/críticas, mas permanecem três moderadas na cadeia Mammoth sem solução compatível aplicada.
- TypeScript, build e 229 testes frontend aprovados após atualização. Rodada direcionada backend: 78 aprovados, 18 pulados. Global: 836 aprovados, 279 falhas conhecidas, 112 pulados; snapshot anterior à última correção de áudio, posteriormente verificada na suíte direcionada e navegador.
- Revalidados F01–F21: sete resolvidos, dez parciais, três bloqueados e um pendente. Modelos, preços oficiais, limites e plano de integração registrados no [relatório final](docs/audits/FINAL_MEDIA_VALIDATION_2026-10-21.md).
- Nenhum fornecedor pago ativado. Teto proposto de US$15 para um futuro piloto não foi aplicado nem gasto. Sem deploy, commit ou push.

### Correção estrutural audiovisual

- Recuperada a inicialização local do Studios com origem loopback explícita; prontidão exige dependências reais.
- Unificadas rotas de mídia e proteções HTTP entre FastAPI principal e ponte de sessão Clicko.
- Removidos sucessos simulados das rotas antigas de edição; rota antiga de geração também aposentada para impedir bypass de cotas e orçamento.
- Descoberta central de FFmpeg/FFprobe e detecção de encoder H.264; jobs locais saem da requisição HTTP.
- Reserva/recuperação de jobs, identidade do proprietário da fila e aquisição atômica da execução para reduzir duplicação.
- Crítica de produção aceita artefatos validados dos renderizadores atuais, preservando vínculo de revisão/checksum.
- Proporção/resolução nativas nas imagens Gemini, com validação do arquivo, capacidades por modelo e revisão humana preservada.
- Planejamento estruturado reutilizado pela timeline FFmpeg; conexão/modelo continuam configuráveis, sem geração artificial.
- Flags de vídeo Gemini e limites financeiros de produção aplicados antes da submissão externa; revisão paga implícita removida.
- Identidade financeira da empresa/membro preservada entre clientes; reservas de tarefas antigas contam pelo período da nova admissão. Envelopes de edição com tarifa/identidade escolhidas pelo cliente são recusados na rota genérica.
- Cota comercial de vídeo restrita a cenas geradas por IA, com reserva durável e conciliação idempotente; editor local não consome minutos.
- Métricas reais de processamento, geração e armazenamento; estimativas financeiras explicitamente separadas de faturas de fornecedor.
- Bundles Craft ausentes retornam erro explícito, não HTML; builder informa o requisito Docker ausente.
- Atualizados contratos/testes obsoletos da unificação Studios e da aposentadoria do editor Pillow.

### Limitações

- Craft nativo/WASM não pôde ser compilado neste Windows sem Docker/Rust. Os fontes e sua linhagem foram preservados e verificados.
- PostgreSQL/Redis/workers de produção e modelos externos não foram provisionados nem ativados.
- Rodadas direcionadas e frontend aprovados; suíte completa backend permanece não aprovada, com resultados e comparação à base anterior documentados no relatório.
- Nenhuma chamada paga, migração destrutiva, publicação, deploy ou push foi realizado. Veja evidências e resultados no relatório técnico.
