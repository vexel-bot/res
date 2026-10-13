# Auditoria técnica da Clicko — 13/09/2026

## Escopo e regra de segurança

Esta auditoria cobriu o frontend, o backend Express, autenticação e governança, KLIC, Analytics, Radar, automações, calendário, integrações e infraestrutura de build/testes. Os módulos **Imagem** e **Vídeo** foram tratados como protegidos: nenhum arquivo, fluxo, componente, estilo, provider, prompt, API ou integração específico dessas áreas foi alterado.

O repositório já continha um working tree extensamente modificado antes desta execução. Para não confundir trabalho anterior do usuário com esta auditoria, foi criada uma cópia de recuperação do estado de código imediatamente anterior à limpeza em:

`C:\Users\pedro\AppData\Local\Temp\clicko-cleanup-a381a93856fc4642a393813112e31bd3\source-before-cleanup.zip`

Nenhum commit, push, merge, migração, alteração de banco ou publicação foi realizado.

## Mapeamento técnico resumido

- Frontend: React 19, TypeScript, Vite e CSS global/por módulo.
- Entrada e navegação: `src/main.tsx` e `src/App.tsx`.
- Estado global: Auth, Theme, Governance, Operations, Offer e AIChat contexts.
- Backend: Express em `server.ts`, com routers separados para governança, integrações, voz e KLIC.
- Persistência: repositórios JSON atômicos para governança/KLIC; preferências e parte do estado operacional no navegador; tokens OAuth atualmente em memória do processo.
- KLIC: runtime, conversa persistente, anexos, streaming NDJSON, memória, ferramentas, voz, retry e classificação segura de falhas de provider.
- Analytics/Radar: normalização e agregação em módulos dedicados, com testes de períodos, dados ausentes e separação entre redes.
- Testes: runner local com testes de autenticação, autorização, persistência atômica, KLIC, voz, retry, Analytics, automações, calendário, acesso, CSV e tema.

Inventário observado: 86 arquivos em `src`, 35 em `server` e 6 em `scripts`; 107 arquivos TypeScript/TSX nessas três áreas.

## Correções realizadas

### Limpeza comprovadamente segura

- Removido o export `navigationLabel`, sem referências no projeto.
- Removidas referências internas que só recebiam valores e nunca eram lidas em `useKlicVoice`, além de limpezas duplicadas de recursos já cobertos pelo fluxo ativo.
- Removida uma declaração duplicada de `vite` no `package.json`; o lockfile foi regenerado offline, sem troca deliberada de versões.
- Removidos 169 seletores CSS sem qualquer referência no código-fonte. O script de poda validou que todas as regras restantes foram preservadas.
- Resultado aproximado da limpeza: 775 linhas e 23,5 kB de fonte/configuração removidos, sem alterar a interface ativa.

### Tipagem e arquitetura

- Eliminado o único ciclo de imports detectado (`useConversations` ↔ `AIChatContext`) movendo o contrato mínimo de anexo para o domínio local de conversa.
- O parser de eventos da KLIC passou a tratar JSON como `unknown` e a validar o evento antes de estreitar seu tipo.
- Respostas JSON da KLIC passaram a aceitar tipo genérico em vez de retornar `any` implicitamente.
- O parser de sugestões de automação valida objeto, lista de etapas, tipos e duração antes de usar conteúdo gerado por IA.
- O validador de escopo do store da KLIC passou de `any` para `unknown` com guarda explícita de objeto.
- Nova varredura do grafo de imports: **0 ciclos**.

### Observabilidade e estabilidade da KLIC

- A transcrição direta de áudio agora recebe um `requestId` UUID, alinhado ao restante do pipeline de voz e aos logs seguros do provider.
- O teste de integração foi ampliado para comprovar que todos os pedidos de transcrição recebem UUID válido.
- Permaneceram preservados streaming, cancelamento, deduplicação, retry, voz masculina/feminina, anexos, persistência e isolamento por usuário/workspace/cliente.

### Performance mensurável

- O bundle CSS de produção caiu de aproximadamente 319,08 kB para 300,14 kB (redução de 18,94 kB, cerca de 5,9%).
- Não foram adicionadas dependências.
- O JavaScript principal continua grande (943,14 kB, 266,48 kB gzip) e o Vite ainda emite o aviso de chunk acima de 500 kB. A correção adequada exige code splitting planejado e foi deixada para uma mudança separada, com testes de navegação.

## Validação final

| Verificação | Resultado |
| --- | --- |
| Typecheck / lint (`npm run lint`, atualmente `tsc --noEmit`) | Aprovado, 0 erros |
| Testes (`npm test`) | Aprovado, 75/75 |
| Build (`npm run build`) | Aprovado |
| `git diff --check` | Aprovado; apenas avisos preexistentes de normalização LF/CRLF |
| Dependências instaladas (`npm ls --depth=0`) | Árvore íntegra |
| Auditoria de produção (`npm audit --omit=dev`) | 0 vulnerabilidades conhecidas |
| Busca de chaves privadas/API keys fora de arquivos de ambiente | 0 ocorrências |
| Grafo de imports TypeScript | 0 ciclos |
| KLIC no navegador | Acessível, histórico renderizado |
| Imagem no navegador | Renderizada, 0 erros/warnings de console |
| Vídeo no navegador | Renderizado, 0 erros/warnings de console |

Os testes de governança confirmaram isolamento de workspace, recusa de identidade ausente/cruzada, proteção de rotas privadas, login/cadastro/verificação/recuperação/logout, limites de convite e persistência antes da resposta HTTP. Os testes da KLIC confirmaram isolamento de contexto, ausência de vazamento de erro do provider, deadlines, cancelamento, no máximo três tentativas transitórias e persistência de conversa.

Não foi realizada uma chamada externa real durante esta auditoria, pois isso não era necessário para validar as mudanças locais e dependeria da disponibilidade dos providers. Nenhuma credencial ou valor de `.env` foi lido, impresso, copiado ou alterado.

## Pontos importantes não alterados

Os itens abaixo possuem risco médio/alto ou exigem uma decisão arquitetural. Foram documentados, não executados.

### Prioridade alta

1. **Proteção desigual dos endpoints legados de IA.** Somente `/api/ai/chat` declara autenticação no próprio endpoint. Radar, campanha, calendário, copy, análise de métricas, matriz criativa e briefing não apresentam a mesma proteção explícita. Os endpoints de Imagem e Vídeo também pertencem a esse conjunto legado, mas não foram tocados por serem módulos protegidos. Recomendação: inventariar consumidores e aplicar autenticação/autorização por módulo em uma entrega isolada, com testes negativos por rota e sem mudar contratos.
2. **Tokens e estados OAuth apenas em memória.** `pendingAuthorizations` e `workspaceTokens` são `Map`s do processo; reiniciar o servidor perde conexões e uma implantação com múltiplas instâncias não compartilha estado. Recomendação: armazenamento durável criptografado, rotação/revogação e isolamento transacional por workspace.
3. **Erros brutos em rotas legadas.** Alguns `console.error` recebem o objeto completo do erro do provider. Dependendo do SDK, metadados sensíveis podem aparecer nos logs. Recomendação: usar o mesmo sanitizador estruturado da KLIC, registrando somente requestId, provider, modelo, status, código e razão allowlisted.

### Prioridade média

1. **Concorrência na revalidação de sessão.** Timer e evento de foco podem iniciar verificações sobrepostas em `AuthContext`; uma resposta antiga pode, em teoria, sobrescrever uma resposta mais nova. Por envolver autenticação, a correção deve usar geração/cancelamento de request e testes específicos antes de ser aplicada.
2. **Timeout/cancelamento em integrações sociais.** Troca de token, leitura de recursos e alguns carregamentos do cliente usam `fetch` sem deadline explícito. Uma falha de rede pode manter estados ocupados por tempo excessivo. Recomendação: AbortController compartilhado, erro público estável e teste de desmontagem/troca de workspace.
3. **Razão OAuth transportada na URL de retorno.** Mensagens do provider chegam como query string e são exibidas pela interface. Recomenda-se mapear razões externas para códigos públicos allowlisted e impedir dados arbitrários em URL/telemetria.
4. **Persistências diferentes para fontes de verdade.** Operações, automações e preferências ainda possuem partes em `localStorage`, enquanto governança e KLIC são server-side. É necessário documentar claramente quais dados são apenas preferências locais e quais exigem consistência multi-dispositivo.
5. **Componentes extensos.** `useKlicVoice`, OperationsContext, AIChatView, Calendar, ConnectedAccounts e algumas áreas de Analytics concentram muitas responsabilidades. Extrações futuras devem ocorrer por comportamento coeso, com testes antes da movimentação; não foi feita refatoração cosmética.

### Observação dos módulos protegidos

- A área Vídeo mostra atualmente o fallback visual “Não foi possível abrir a mídia” para o preview existente. Não houve erro de console na abertura da página. Por regra do escopo, a causa não foi investigada nem corrigida.
- Possíveis melhorias internas, casts e integrações de Imagem/Vídeo foram apenas observados e permaneceram intactos.

## Confirmação explícita sobre Imagem e Vídeo

- A opção **Imagem não foi modificada** nesta execução.
- A opção **Vídeo não foi modificada** nesta execução.
- Nenhuma funcionalidade dessas áreas foi alterada.
- Nenhum redesign foi realizado nessas áreas.
- Nenhuma integração, provider, prompt ou API específica dessas áreas foi substituída.
- `ImageStudioView.tsx`, `VideoEditorView.tsx` e `CreationStudioView.tsx` permanecem byte a byte idênticos ao backup anterior à auditoria (SHA-256 comparado).
- A limpeza compartilhada removeu somente seletores com zero referências no código. As duas rotas foram abertas após as mudanças, renderizaram seus controles e não produziram erros de console.
- Nenhuma mudança indireta desta auditoria comprometeu Imagem ou Vídeo nas validações disponíveis.

## Recomendações para a próxima sessão

1. Criar uma suíte de contrato para todos os endpoints legados de IA e, só então, uniformizar autenticação/autorização.
2. Planejar a persistência OAuth criptografada e multi-instância.
3. Aplicar sanitização estruturada e requestId aos erros restantes do backend.
4. Introduzir timeouts/cancelamento nas integrações sociais com testes de troca de workspace.
5. Planejar code splitting por rota, medindo carregamento inicial e sem alterar visual ou estado.
6. Tratar qualquer problema de Imagem/Vídeo somente em uma sessão explicitamente autorizada para esses módulos.

## Conclusão

A base terminou a auditoria compilando, com todos os testes aprovados, sem vulnerabilidades conhecidas no audit de produção, sem ciclos de import e com menos código/CSS morto. As mudanças executadas foram pequenas, isoladas e verificáveis; alterações de autenticação, OAuth e endpoints legados com potencial de regressão foram corretamente retidas para uma etapa dedicada.
