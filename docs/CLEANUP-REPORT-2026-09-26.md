# Limpeza segura da Clicko — 26/09/2026

## Resultado e escopo

Limpeza incremental de código comprovadamente redundante ou inalcançável, sem redesenho e sem alteração dos contratos de backend. O repositório já continha numerosas mudanças antes desta execução; o diff contra o Git inclui trabalhos anteriores e não representa somente esta limpeza.

A auditoria examinou o inventário de fontes, imports e referências TypeScript, funções duplicadas, dependências, entradas de build, scripts, workers, testes e pontos de integração. Não foi identificado outro arquivo inteiro ou pacote cuja remoção pudesse ser feita com segurança. A análise de referências foi complementada pela inspeção dos consumidores e caminhos de execução; ausência de import estático, isoladamente, não foi considerada prova de inutilidade.

## Arquivos alterados nesta limpeza

| Arquivo | Alteração |
| --- | --- |
| `src/components/AIChatView.tsx` | Reutilização do leitor de anexos; remoção de argumentos ignorados do wrapper de envio e de um recorte de mensagens equivalente a `slice(0)`. |
| `src/components/FloatingAIAssistant.tsx` | Reutilização do mesmo leitor de anexos, sem alterar seleção, validação ou envio. |
| `src/hooks/useKlicVoice.ts` | Remoção de `toggleVoice`, função sem consumidores; controles efetivamente usados foram preservados. |
| `src/components/SettingsView.tsx` | Remoção dos renderizadores inacessíveis de Plataforma e KLIC, já ausentes da navegação; remoção de helper, imports e estados exclusivos desses renderizadores; eliminação de classes duplicadas. |
| `tsconfig.json` | Exclusão explícita de `dist` e `node_modules` da descoberta de entradas do compilador. Os fontes e testes continuam incluídos; nenhum diagnóstico foi desativado. |

Arquivos adicionados: `src/klic/attachmentInput.ts`, com o leitor idêntico antes duplicado nos dois chats, e este relatório.

Arquivos inteiros removidos: **nenhum**. Dependências removidas: **nenhuma**. Nenhum endpoint, variável de ambiente, provider ou migração foi removido. Nenhuma credencial foi lida ou alterada.

Os renderizadores removidos de Configurações não tinham acesso pela lista de seções, grupos, seletor ou estado inicial. A busca de capabilities foi mantida, pois Preferências ainda usa a disponibilidade de e-mail. Os campos persistidos de aparência e personalização da IA também foram mantidos para compatibilidade com dados e consumidores antigos.

## Preservado por segurança

- Caminhos legados de `AIChatContext` e preferências `personalAI`: existem consumidores ligados aos módulos protegidos de mídia.
- Migrações e recuperação de estado em `OperationsContext`: necessárias para dados salvos anteriormente.
- Parsers semelhantes de cookies em autenticação/governança e integrações: não unificados durante uma limpeza por envolverem fronteiras de segurança.
- Implementações de revogação Meta e Threads: providers independentes, com seus próprios contratos e destinos.
- Scripts OAuth, callbacks, webhooks, worker de anexos, bootstrap e entradas de testes: uso indireto ou operacional legítimo.
- Dependências de documentos, planilhas, PDF, avatar, Google, PostgreSQL, ícones, build e testes: referências e usos encontrados.
- Assets, estilos globais e arquivos de lock existentes: não excluídos com base apenas em buscas textuais, dada a possibilidade de referências dinâmicas e outros fluxos de instalação.

## Verificações executadas

- `npm test`: **93 testes aprovados, zero falhas**, antes e depois da limpeza; repetição final também aprovada.
- `npm run lint`: **aprovado**. Neste projeto o comando executa `tsc --noEmit`; não há um lint ESLint separado nesse script.
- TypeScript com `noUnusedLocals` e `noUnusedParameters`: **aprovado**, sem adicionar `any`, supressões ou desativar regras.
- `npm run build`: **aprovado**, incluindo frontend, servidor e worker de anexos.
- Comparação das entradas do compilador: a exclusão de `dist` retirou apenas quatro arquivos gerados, mantendo os fontes e testes.
- Conferência de hashes realizada durante a execução: as mudanças de fonte ficaram nos cinco arquivos listados e no novo helper. Backend, integrações, contextos compartilhados, CSS de fonte e fontes dos módulos Imagem/Vídeo permaneceram iguais ao início desta limpeza.
- Verificações visuais de Minha Conta, Preferências e mini chat nos dois temas, sem erros de JavaScript. As capturas de mini chat e das seções verificadas no modo claro foram idênticas; capturas longas no modo escuro tiveram diferenças de posição/hover/animação, sendo complementadas por inspeção da renderização normal. Não se trata de uma certificação pixel a pixel de todas as telas.
- Smoke test final no Chrome: Configurações, KLIC, Conexões e Dashboard abriram sem erros de JavaScript. Selecionar e remover um anexo funcionou nos dois chats; o painel de configurações de voz abriu corretamente. O arquivo de teste não foi enviado.
- Comunicação real frontend/backend no smoke test: HTTP 200 para sessão de autenticação, sessão de governança, workspace, usuários, planos, assinatura, aprovações, auditoria, capabilities, conexões, lista de conversas e eventos da KLIC.

A suíte cobre, entre outros pontos, cadastro/login/logout/sessão, isolamento de workspaces, persistência e avatar, OAuth e seleção de recursos, refresh/revogação e webhooks, contexto/streaming/anexos/cancelamento da KLIC, autorização de voz, calendário, automações, Analytics e inicialização de temas.

## Resultado mensurável do build

O JavaScript principal passou de **1.002,73 kB para 991,66 kB** minificado; gzip de **283,20 kB para 280,56 kB**. O CSS gerado passou de **323,36 kB para 322,82 kB** pela retirada automática de utilitários que só apareciam nos renderizadores mortos. Nenhuma folha de estilo de fonte foi editada.

Permanece o aviso já existente de chunk acima de 500 kB. Não foi feita divisão global do bundle, pois isso alteraria a estratégia de carregamento e poderia alcançar áreas protegidas.

## Proteção de Imagem e Vídeo

- A opção Imagem não foi modificada nesta limpeza.
- A opção Vídeo não foi modificada nesta limpeza.
- Nenhuma funcionalidade dessas áreas foi alterada.
- Nenhum redesign foi realizado nessas áreas.
- Nenhuma integração dessas áreas foi substituída.
- Não foi identificada mudança indireta que comprometa Imagem ou Vídeo: seus fontes e dependências de runtime compartilhadas foram preservados, e typecheck/build passaram. As alterações anteriores desses arquivos que aparecem no Git não pertencem a esta execução.

## Limites e revisão futura

Testes automatizados de integração não equivalem a nova homologação em produção de todas as redes sociais. Não foram executadas publicações reais, reautorizações de cada provider, uma nova geração paga da Gemini ou uma sessão com microfone físico nesta limpeza. Portanto, não se declara disponibilidade externa de todos esses serviços com base apenas nos testes.

Possíveis próximos trabalhos, mediante escopo próprio: divisão do bundle; revisão específica dos fluxos legados de mídia; homologação OAuth com contas reais por provider; auditoria visual mais ampla em diferentes dispositivos. Esses itens não justificam remoções especulativas nesta tarefa.
