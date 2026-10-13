# KLIC como inteligência central da Clicko

## Fluxo operacional

Toda solicitação passa pelo plano estruturado `ENTENDER → ANALISAR → CRIAR → ORGANIZAR → EXECUTAR → MEDIR → APRENDER`.
O plano registra o estado de cada etapa (`completed`, `ready`, `awaiting_confirmation`, `blocked` ou `skipped`), as fontes consultadas e as ações propostas. Uma resposta textual nunca é prova de execução.

## Camadas

- **Context Engine:** sessão resolvida no backend, workspace, cliente, módulo, contexto efêmero da página e fontes allowlisted.
- **Permission Layer:** autorização de módulo, papel, permissão e escopo de cliente validada no backend.
- **Tool/Action Layer:** leituras registradas no catálogo do `KlicCore`; rascunhos reversíveis passam por `/api/klic/actions/prepare`; ações externas e críticas permanecem nos serviços responsáveis.
- **Orchestrator:** classifica intenção, coleta evidências, produz o plano de sete etapas e determina risco e confirmação.
- **Analytics/Reasoning Layer:** recomendações baseadas nas fontes disponíveis, distinguindo fato, correlação, hipótese e ausência de dados.
- **Memory Layer:** preferências, objetivos explícitos, planos preparados e eventos isolados por usuário, workspace e cliente.
- **Automation Layer:** gera configurações inativas para revisão; ativação não é inferida de uma conversa.
- **Audit Layer:** cada ferramenta, etapa, objetivo e ação preparada produz rastreio escopado.
- **Presentation Layer:** conversa completa, balão contextual e Dashboard usam o mesmo núcleo, sem substituir os módulos tradicionais.

## Segurança de ações

- Leituras: executadas quando autorizadas.
- Rascunhos reversíveis: preparados por API interna idempotente e retornam `executed: false`.
- Publicação, agendamento externo, envio para aprovação e ativação de automação: exigem confirmação no módulo responsável.
- Exclusão, desconexão, assinatura, permissões, membros e titularidade: sempre críticas; um campo `confirmed: true` enviado pelo frontend não concede autoridade.
- Resultados usam estados explícitos. A KLIC não informa conclusão quando o backend só preparou ou planejou a operação.

## Operações em vários clientes

Pedidos agregados mudam para escopo de workspace e descartam snapshots locais de um cliente. Somente serviços autorizados contribuem evidência. Qualquer ação em massa retorna um plano para revisão antes de executar.

## Imagem e Vídeo

Os módulos existentes permanecem intactos. A KLIC pode preparar um handoff estruturado, mas geração, edição e interface continuam pertencendo aos módulos atuais.
