# Clicko — limpeza segura de código

Data: 03/10/2026. Projeto: `C:\Users\pedro\Downloads\res`.

## Escopo e preservação

Limpeza conservadora, sem redesenho, mudanças de regras de negócio ou substituição de integrações. O checkout já continha muitas alterações e arquivos não rastreados antes desta execução; o diff contra HEAD não representa somente esta limpeza. As exclusões de componentes e alterações em Imagem/Vídeo que já apareciam no status do Git não foram realizadas por esta tarefa.

Foram rastreados imports/exports por AST e resolução de módulos TypeScript, entradas de frontend/backend, testes, scripts, worker, bootstrap de tema, referências textuais e seletores dinâmicos. Os 190 arquivos de código analisados estavam alcançáveis pelas entradas identificadas. Não houve exclusão de arquivos completos.

## Alterações realizadas nesta execução

| Arquivo | Limpeza ou ajuste |
| --- | --- |
| `src/components/DashboardExperience.css` | Removidas 102 regras órfãs dos layouts antigos de resumo, galeria, acesso e conteúdo complementar. Preservadas as alternativas ativas de seletores compartilhados. |
| `src/components/SubscriptionView.css` | Removidas 20 regras da antiga grade de consumo (`cb-usage`, `cb-metric*`), sem remover os estilos da tela atual de consumo. |
| `src/components/CreativeWorkspace.css` | Removida uma regra para o seletor abandonado `.cd-chapter`. |
| `src/data/mockData.ts` | Removido somente o export sem consumidores `AI_SUGGESTIONS`, com três sugestões fictícias; import restante convertido para `import type`. Dados iniciais ainda utilizados foram preservados. |
| `src/types.ts` | Removida somente a interface `AIActionSuggestion`, cujo único consumidor era o mock removido. Nenhum contrato persistido foi alterado. |
| `scripts/run-audit-tests.cjs` | Substituída a lista manual de arquivos por descoberta de testes `.test.ts` em `src` e `server`; preservada a compilação isolada e sua limpeza temporária. |
| `scripts/profile-avatar-test-server.ts` | Atualizada apenas a preparação do servidor isolado de teste: checkout de teste e recebimento do corpo bruto para validar a assinatura do webhook. Não carrega `.env` nem usa os dados reais da aplicação. |
| `tests/avatar/profile-avatar.spec.ts` | Ativa uma assinatura exclusivamente de teste pelo fluxo de webhook assinado antes de validar o avatar. Mantidas todas as verificações anteriores. Não realiza pagamento real. |
| `.gitignore` | Ignorados `test-results/` e `playwright-report/`, saídas geradas pelos testes; nenhum resultado foi apagado. |

Total: **123 regras CSS removidas** e cinco seletores combinados simplificados, sem aumentar ou diminuir a especificidade das alternativas ativas. Nenhuma consolidação arquitetural ou refatoração de componentes foi necessária.

### Redução no build

| Artefato | Antes | Depois |
| --- | ---: | ---: |
| CSS minificado | 468,36 kB | 458,59 kB |
| CSS gzip | 76,70 kB | 75,19 kB |
| JavaScript minificado | 1.125,47 kB | 1.125,47 kB |
| JavaScript gzip | 319,81 kB | 319,81 kB |

Economia de aproximadamente 9,77 kB no CSS de produção. Tamanhos conforme saída do Vite, não uma medição de tempo de carregamento.

## Dependências e candidatos mantidos

- Nenhuma dependência removida: todas tiveram utilização identificada em runtime, build, tipos, scripts, testes ou configuração. `package.json` e lockfiles não foram alterados nesta limpeza.
- Mantidos `INITIAL_WORKSPACES` e `INITIAL_POSTS`: possuem consumidores, apesar do nome `mockData.ts`.
- Mantidos seletores construídos dinamicamente, incluindo estados do plasma, marca e símbolos de planos; ausência de uma string literal completa não prova desuso.
- Mantidos estilos globais antigos sem evidência suficiente de equivalência para remoção, migrações/compatibilidade de dados, scripts operacionais, documentação, assets e o lockfile do Bun.
- Mantidos logs operacionais e de falha necessários a diagnóstico/auditoria. Não houve remoção indiscriminada de logs.
- Não foram lidos ou modificados valores de credenciais, `.env`, configurações reais de providers ou dados de usuários.
- A busca final de exports candidatos sem consumidores retornou uma lista vazia dentro da análise estática utilizada. Isso não constitui prova formal de ausência de todo código morto possível.

## Problemas encontrados e resolvidos na validação

1. A lista manual de testes omitia três arquivos: `dashboardOperationalModel.test.ts`, `plasmaState.test.ts` e `plasmaVisibility.test.ts`. A descoberta automática incorporou seus dez testes: a suíte passou de 108 para 118, sem excluir ou enfraquecer testes.
2. O teste de avatar criava uma conta sem plano e esperava acesso direto às configurações. A proteção atual de assinatura redirecionava corretamente para a escolha de plano. Foi corrigida a preparação do teste, não a proteção de produção.
3. A primeira rodada de navegador encontrou o servidor local desligado (`ERR_CONNECTION_REFUSED`). Após executar `npm run dev`, a rodada completa passou.

## Validação final

- `npm test`: **118 aprovados, zero falhas, zero ignorados**, em 27 arquivos de teste.
- `npx playwright test tests/creative-workspace.spec.ts tests/client-journeys.spec.ts tests/clicko-dual-theme.spec.ts`: **13 aprovados**. Inclui navegação, temas, responsividade, clientes/jornadas e preservação do shell original de Imagem/Vídeo.
- `npx playwright test --config playwright.avatar.config.ts`: **1 aprovado**. Preview, envio, persistência após reload, logout/login, novo contexto de navegador e rejeição de arquivos inválidos/grandes.
- Total da rodada final: **132 testes aprovados**. As repetições intermediárias não foram somadas a esse total.
- `npm run lint`: aprovado; o script existente executa `tsc --noEmit`, portanto esta é também a verificação de tipos. O projeto não define uma etapa ESLint separada.
- `npm run build`: aprovado para frontend, servidor e worker de anexos.
- `git diff --check`: aprovado. O Git emitiu avisos de normalização LF/CRLF já presentes no checkout, sem erros de whitespace.
- Comparação adicional dos estilos calculados contra cópias anteriores à limpeza: **36 cenários aprovados, zero diferenças**. Larguras de 1365, 768 e 390 px, temas claro/escuro, Dashboard normal e expandido, Assinatura normal e com plano selecionado, Imagem e Vídeo. Foram comparados elementos e pseudoelementos no mesmo DOM, com movimentos congelados apenas no teste para evitar diferenças de fase; cores de scrollbar serializadas em sRGB/Oklab foram normalizadas aos pixels RGBA correspondentes. É uma comparação de estilos calculados, não um teste pixel a pixel de capturas.

## Limitações e pendências preservadas

- O build mantém o aviso preexistente de chunk JavaScript acima de 500 kB. Não foi mascarado nem alterada a estratégia de carregamento, pois isso ampliaria o risco e o escopo.
- As verificações não executaram pagamentos reais, publicação em redes sociais, OAuth externo ou geração cobrada de mídia/IA. Os testes de backend usam seus ambientes controlados; não representam homologação dos provedores externos.
- Nenhum teste oferece garantia absoluta sobre todos os estados possíveis. As conclusões se restringem à análise de referências e às validações registradas.

## Imagem e Vídeo: áreas protegidas

- A opção Imagem não foi modificada nesta execução.
- A opção Vídeo não foi modificada nesta execução.
- Nenhuma funcionalidade dessas áreas foi alterada.
- Nenhum redesign foi realizado nessas áreas.
- Nenhuma integração dessas áreas foi substituída.
- As verificações executadas não identificaram comprometimento indireto dessas áreas pela limpeza; seus componentes, fluxos e providers não foram editados.

## Recuperabilidade

Cópias anteriores dos nove arquivos alterados estão preservadas fora do repositório, em `C:\Users\pedro\Documents\Codex\2026-08-15\fa-a-git-pull-no-projeto\cleanup-review\2026-10-03\baseline`. Os scripts auxiliares de análise também ficaram fora do código da aplicação. Não houve exclusão de dados, históricos, credenciais ou arquivos de usuários.

## Conclusão

Limpeza concluída dentro do escopo conservador autorizado: aplicação compilando, testes relevantes aprovados e nenhuma evidência de regressão causada por estas alterações nas validações executadas. Candidatos sem comprovação segura foram preservados.
