# Clicko · modo desenvolvedor local

Verificação: **23/10/2026**, checkout `C:\Users\pedro\Downloads\res`.

## Parecer

O modo DEV está implementado e operacional nos testes técnicos, sem login
comercial, cliente contratado ou assinatura paga. A identidade reservada é
reconhecida na governança e na ponte assinada dos Studios. Criação, edição,
exportação e recuperação produziram documentos e arquivos reais.

**Não declarar homologação integral da interface:** Motion e Imagem foram
exercitados pelo navegador nesta implementação; o teste visual restante de
Vídeo e KLIC ficou bloqueado porque a ferramenta passou a informar
`Local browser use is disabled in Work settings`. Após a confirmação do usuário,
a nova consulta retornou o mesmo bloqueio. Esses dois fluxos foram concluídos
tecnicamente pela sessão DEV real e pelos mesmos endpoints usados pela interface,
não por uma identidade de fixture. A habilitação do navegador pelo usuário é a
única pendência para fechar também essa conferência visual. Não houve simulação
de resultados ou contorno da configuração do Work.

## Estrutura entregue

- `CLICKO_DEV_MODE=true`, configurado explicitamente pelo supervisor local,
  somente com `NODE_ENV=development` e execução a partir das fontes.
- **Clicko Developer**, Administrador de desenvolvimento, workspace **Clicko DEV**,
  **Cliente DEV**, plano **Desenvolvimento**, sem cobrança.
- IDs Node reservados: `usr-dev-clicko`, `ws-dev-clicko`, `client-ws-dev-clicko`.
- Workspace Studios derivado pela ponte existente:
  `e8614463-28cd-5e73-83ce-9f438bca5c7a`. Não foi removida a verificação do cliente.
- Permissões administrativas de teste e módulos existentes liberados pelo plano
  DEV, conservando as verificações de governança/RBAC/escopo.
- Provisionamento idempotente; dados recuperados no reinício, sem novas cópias
  dos registros reservados. Pasta privada: `.codex-runtime/clicko-dev`.
- Sessão opaca do servidor, token aleatório armazenado somente como hash em
  memória, 8 horas, cookie HttpOnly/SameSite Strict. Reiniciar invalida a sessão,
  mas a interface obtém uma nova sessão local; os documentos não são apagados.
- Indicador discreto **Ambiente de Desenvolvimento**, serviços, ponte, modelos
  configurados versus não homologados e bloqueios de custo.
- `dev:local`, `dev:status`, `dev:stop` e limpeza recuperável `dev:reset`.

O armazenamento histórico `.codex-runtime/stage1-local` e os dados comerciais
não foram migrados, apagados ou usados como identidade DEV. Os materiais de QA
importados são arquivos sintéticos próprios de testes anteriores.

## Segurança e custos

O servidor exige listener loopback e verifica os endereços reais local/remoto
do socket, além de Host/porta, Origin e Fetch Metadata. Rejeita cabeçalhos de
proxy/encaminhamento e não confia em `x-user-id` para autenticar o runtime.
Solicitações sem sessão ou com cookie inventado não obtêm autoridade DEV.

A configuração falha em produção/bundle, listener público, URL remota,
armazenamento fora da pasta privada, redirecionamento por symlink/junction nos
caminhos verificados ou tentativa de ativar o bypass legado. `CLICKO_DEV_MODE=false`
rejeita inclusive um cookie DEV recém-emitido e válido; as regras comerciais
continuam sendo testadas pela suíte de autenticação existente.

O bundle real foi executado com `NODE_ENV=production` e `CLICKO_DEV_MODE=true`:
encerrou com código **1 / DEV_FORBIDDEN_IN_PRODUCTION**, antes de disponibilizar
o servidor. Arquivos `.env`, governança DEV e chave privada retornaram **403**
nas sondagens HTTP ao Vite; nenhum conteúdo privado foi impresso.

Chamadas pagas Node/TTS/Python, pagamentos e mutações de integrações externas
continuam bloqueados. A admissão financeira recusa DEV antes do transporte;
testes instrumentados registraram **zero chamadas ao transporte de provedor**.
Os jobs locais e o planejamento por regras registraram custo externo zero.
Configuração de modelo presente não é prova de inferência operacional.
Nenhuma chave existente da KLIC foi alterada.

Não expor esse ambiente por túnel, proxy ou encaminhamento TCP. As proteções não
são uma autorização para publicá-lo, nem uma sandbox contra um operador local
que modifique o servidor ou publique deliberadamente seus sockets.

## Provas funcionais

| Área | Prova concluída | Limite da evidência |
| --- | --- | --- |
| Motion | Navegador: criar, plano de 3 cenas, aplicar, editar texto/cor/rotação, salvar e exportar MP4 de 15 s | Exportação da revisão 3; edição contextual posterior salva na revisão 4 |
| Imagem | Navegador: criar, aplicar plano, importar PNG, recortar, redimensionar, salvar e baixar PNG | Composição local, não geração por IA |
| Vídeo | Sessão DEV real/API: importar MP4, sondar, criar projeto, cortar fonte, editar opacidade, salvar, renderizar e baixar | Interface carregada após correção HMR; sequência visual de edição/exportação ainda pendente |
| KLIC | Sessão DEV real/API: criar conversa, selecionar projeto/camada, preparar plano, aplicar e reaplicar sem duplicação | Regras locais, sem inferência; conferência visual da conversa ainda pendente |
| Reinício | Novo PID de servidor, nova sessão, 3 documentos e 3 entregas recuperados com hashes iguais | Não homologa produção distribuída ou autenticação comercial |

O teste KLIC mudou **somente** `scene-1-title` do Motion para tangerina
`#F28500`; as demais camadas permaneceram iguais. A repetição do recibo não
incrementou a revisão novamente. A gravação da timeline também foi idempotente.
O MP4 original importado foi novamente baixado e manteve o SHA-256.

Documentos de teste preservados:

- Motion: `ac55721f-2ee9-4ea1-bd6e-60f42a4b187d`, revisão 4.
- Imagem: `c6c22b4d-91d3-4574-9c76-46308c27bbd0`, revisão 4.
- Vídeo: `c79b21d4-b4d4-4b96-b5ef-4f0df56a58bb`, revisão 2.

Entregas baixadas pela ponte autenticada e decodificadas integralmente:

| Arquivo privado | Formato real | SHA-256 |
| --- | --- | --- |
| `ui-motion.mp4` | H.264/AAC, 1280×720, 24 fps, 15 s | `780aab7ea1db0fa6737847126daf2e7b126e5795245d74fb7b5abb7cf7a7833b` |
| `technical-video.mp4` | H.264/AAC, 1920×1080, 30 fps, 3 s | `f56228ee4ca09409875373135902004ed1b3063f7fad36c2783eaa09699646cf` |
| `ui-image.png` | PNG, 1080×1080, validado por Pillow | `7c59186448ec60b86c75958f320a802eab9da7788d136b3433b35118b85f8996` |

Não foi usado um MP4 antigo como resultado de uma nova renderização. Os dois
MP4s acima foram efetivamente gerados e baixados durante esta implementação.

## Testes e verificação

| Comando / escopo | Resultado |
| --- | --- |
| `npm test` | **243 + 2 = 245 aprovados**, zero falhas/skips |
| `node --test scripts/dev-local-control.test.mjs scripts/dev-reset.test.mjs` | **4 aprovados** |
| `node --import tsx --test server/devMode.test.ts` | **2 aprovados**, reexecução da segurança já incluída no escopo npm; não somar novamente |
| pytest: ponte Clicko, finanças, agentes locais, Etapa 2, conclusão e homologação/compartilhamento Etapa 3 | **51 aprovados**, zero falhas/erros/skips, XML final |
| `npm run lint` | TypeScript `tsc --noEmit` aprovado |
| `npm run build` | Vite + bundles Express/attachment worker aprovados |
| Execução do bundle com DEV em produção | Rejeição esperada, exit 1 |
| `scripts/dev-acceptance.ts --verify` após reinício | 3 documentos + 3 entregas iguais |
| `git diff --check` | Sem erros de whitespace; avisos existentes de conversão LF/CRLF |

Não é uma nova rodada da suíte Python inteira; os resultados globais históricos
continuam nos relatórios anteriores. A rodada direcionada levou aproximadamente
305 s neste host com pouca memória livre, sem transformar lentidão em sucesso
presumido: foi aguardado o exit 0 e lido o XML final. Permanecem avisos existentes
Pydantic sobre o campo `copy`, sem falha nos testes selecionados.

Evidências privadas em `.codex-runtime`:

- `dev-mode-node-final.log`, `dev-mode-types-final.log`, `dev-mode-build-final.log`.
- `dev-mode-security-final.log`, `dev-mode-control-final.log`.
- `dev-mode-python-final.log` / `.xml`.
- `dev-mode-production-rejection.log`, `dev-mode-route-access.log`.
- `dev-mode-media.log`, `dev-mode-persistence.log`.
- `clicko-dev/live-acceptance.json`, exports, `dev-motion-ui.png`, `dev-image-ui.png`.

Uma primeira coleta do ensaio técnico tentou baixar o PNG pela rota exclusiva
de vídeo e recebeu 404. Corrigiu-se **o script de teste** para a rota de assets;
a recuperação foi somente de leitura, sem repetir upload, edição ou render.
Isso não foi ocultado como falha da aplicação nem “corrigido” afrouxando o backend.

## Arquivos desta implementação

- `server/devMode.ts`, `.test.ts`: fronteira local, sessão, configuração e testes.
- `server/governance.ts`, `src/types.ts`, `src/development/contracts.ts`:
  plano/identidade/cliente reservados e metadados DEV.
- `server/developmentRouter.ts`, `server.ts`, `server/production.ts`:
  status, prontidão assinada, integração e recusa em produção.
- `server/finance/admission.ts`, `server/integrations/http.ts`: bloqueios externos.
- `scripts/dev-local.mjs`, `scripts/dev-reset.mjs`, `.test.mjs`, `package.json`:
  ciclo local e arquivamento confirmado.
- `src/context/AuthContext.tsx`, `OperationsContext.tsx`, `src/components/Header.tsx`,
  `src/development/DevEnvironmentBadge.tsx` e `development.css`: sessão/contexto e indicador.
- `src/studios/local/localModel.ts`, `.test.ts`, `LocalProductionStudio.tsx`:
  impedir que histórico atrasado rebaixe tarefa já concluída/aplicada.
- `src/context/ProductDataContext.tsx`, `stableStudioContext.ts`, `.test.ts`:
  contexto único no HMR/lazy, sem cache global na versão de produção.
- `scripts/dev-acceptance.ts`: prova por sessão DEV real e recuperação após reinício.
- README, CHANGELOG, este relatório e duas orientações de operação atualizadas.

O checkout já tinha muitas alterações de etapas anteriores. Esta lista não
atribui à presente tarefa todos os arquivos exibidos por `git status`.

## Operação e pendências

Inicie com `npm run dev:local`, aguarde `npm run dev:status` mostrar `ready: true`,
abra `http://127.0.0.1:3018/dashboard`. O ambiente foi deixado executando em
loopback. Use `npm run dev:stop` para encerrar os processos próprios sem matar
outros serviços. README documenta ativação/desativação, pastas, recuperação e
arquivamento confirmado. A limpeza do perfil real não foi executada.

O ensaio `node --import tsx scripts/dev-acceptance.ts` depende dos projetos e
materiais de QA indicados no próprio script. Recusa repetição se já há evidência;
`--recover-final` apenas coleta uma execução concluída interrompida na coleta.
Depois de reiniciar, `--verify` confere o novo PID, revisões, conversas e hashes,
sem criar projetos. Os ensaios antigos das Etapas 1/2/3 continuam no perfil
histórico, não devem ser apontados silenciosamente para o novo banco DEV.

Pendências reais, não substituídas por botões ou processamento fictício:

1. Reabilitar o navegador no Work e fechar a conferência visual de Vídeo/KLIC.
2. Inferência de modelos generativos/voz externa e modelos locais: dependem de
   runtime, pesos, tier/orçamento e homologação específicos. Não necessários
   para a composição/renderização local validada.
3. PhotoCraft/FilmCraft/EffectCraft: binários/WASM e infraestrutura ainda não
   homologados neste host; fontes e caminhos operacionais existentes preservados.
4. Publicação social, pagamentos, automações com execução externa e recursos
   marcados como planejados continuam dependentes da implementação/integração real.

Não houve deploy, push, instalação pesada, alteração de credenciais comerciais
ou execução autorizada de geração paga. A habilidade de navegação foi usada nas
provas de interface e determinou a interrupção da automação visual quando o
acesso foi desativado; não foi substituída por automação de navegador externa.
