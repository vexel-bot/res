# Limpeza técnica — Clicko Studios — 19/10/2026

Revisão final consolidada em 20/10/2026.

## Estado e preservação

Repositório: `https://github.com/vexel-bot/res.git`.
Branch: `codex/klic-atualizacao-20260823`.
HEAD inicial: `5cab414dd942c721f8e6fdf65dcd82b4ade28722`.
O fetch inicial confirmou zero commits de diferença para a branch remota.

Havia 97 arquivos com trabalho anterior, incluindo arquivos não rastreados e uma exclusão. Foram registrados hashes SHA-256 antes da limpeza e comparados após as alterações: todos permaneceram intactos. O índice Git estava vazio. As modificações desta tarefa usam somente arquivos inicialmente limpos e três novos testes, além deste relatório. Nenhum dado persistido, credencial, variável de ambiente permanente, contrato de API ou módulo visual foi alterado.

## Alterações realizadas

| Arquivo | Alteração e evidência |
| --- | --- |
| `src/api.ts` | Remove o export `authToken` e sua constante de armazenamento local. Não havia consumidor no código ou nos testes, inclusive em HEAD. As requisições continuam com `credentials: 'same-origin'` e a sessão HTTP-only existente. Os antigos scripts de validação que preenchem a chave diretamente foram preservados. |
| `src/studios/latestResourceRead.ts` | Remove um auxiliar isolado, sem importações ou referências no projeto e em HEAD. Não havia efeito executado na carga do módulo. |
| `bun.lock` | Remove o lockfile abandonado: ainda declarava `docx`, `motion` e `autoprefixer`, ausentes do manifesto atual. Scripts e Docker utilizam npm e `package-lock.json`. Os dois arquivos excluídos são recuperáveis pelo Git. |
| `server/integrations/http.ts` | Trata JSON nulo/primitivo retornado por provedores sem lançar `TypeError` antes da classificação do erro. Preserva formatos de sucesso, códigos públicos, limites de retry e a proibição de repetir escritas implicitamente. |
| `server/klic/providerErrors.ts` | Substitui `any` e casts permissivos por validação de valores desconhecidos. Mantém a lista permitida de diagnósticos, impedindo que payloads arbitrários sejam retornados nos erros públicos. Não muda modelos, credenciais, conversa, voz ou visual da KLIC. |
| `vite.config.ts` | Amplia a política existente para negar `.secrets`, chaves `.key` e nomes usuais de credenciais JSON. Ignora o diretório de segredos no observador de arquivos. |
| `.dockerignore` | Exclui também diretórios privados aninhados, ambientes Python, caches, bancos locais e relatórios de teste do contexto de build. Preserva exemplos de configuração. |
| `.gitignore` | Exclui `backend/data/`, armazenamento local padrão de uploads do FastAPI, também protegido no contexto Docker. Testes existentes escreviam fixtures nessa pasta sem isolamento; arquivos de dados não devem entrar no Git. |
| `backend/tests/conftest.py` | Define `STORAGE_PATH` dentro da pasta temporária própria da execução, assim como o banco de testes, impedindo que uploads de fixtures utilizem o diretório local do desenvolvedor. Mantém a limpeza já existente da pasta temporária. |
| `package.json` | Inclui a verificação real da política Vite no comando `npm test` e eleva o mínimo do Sharp à correção `0.35.5`. |
| `package-lock.json` | Atualiza pontualmente dependências com correções de segurança compatíveis, sem atualização geral do SDK, React, Vite ou bibliotecas gráficas. |
| `scripts/private-files.test.mjs` | Dois testes usando a configuração real e `isFileLoadingAllowed` do Vite. Verificam caminhos privados, armazenamento personalizado e preservação dos arquivos da aplicação, sem ler segredos ou iniciar serviços. |
| `server/integrations/http.test.ts` | Três testes para respostas inválidas, preservação do formato de sucesso e retry de leituras. |
| `server/klic/providerErrors.test.ts` | Dois testes para diagnóstico tipado, erros malformados e ausência de vazamento de payloads. |

## Dependências

Todas as dependências diretas de produção têm uso identificado na aplicação ou na configuração de build. Não foram removidas bibliotecas usadas por extração de anexos, OAuth, voz, Studios ou armazenamento.

Atualizações pontuais:

- `sharp`: 0.35.4 → 0.35.5, com os binários correspondentes e libvips 1.3.4.
- `@grpc/grpc-js`: 1.14.4 → 1.14.6.
- `proxy-addr`: 2.0.7 → 2.0.8.
- `brace-expansion`: 1.1.18 → 1.1.21 e 2.1.4 → 2.1.7, mantendo as linhas compatíveis de cada consumidor.
- `source-map-js`: 1.2.1 → 1.2.2.

O `npm audit` passou de 8 alertas (1 crítico, 4 altos, 3 moderados) para 3 moderados, sem alertas críticos ou altos. O problema do Sharp e sua versão corrigida foram conferidos no [aviso oficial do mantenedor](https://github.com/lovell/sharp/security/advisories/GHSA-wq5f-xc86-pv6w); o de proxy-addr consta no [aviso GHSA-jqcg-44mw-7w3h](https://github.com/advisories/GHSA-jqcg-44mw-7w3h).

Os três alertas restantes correspondem à cadeia `mammoth → argparse → sprintf-js`, originada no [aviso de precisão não limitada do sprintf-js](https://github.com/advisories/GHSA-hp3w-g68c-fv3c). A versão publicada consultada, 1.1.3, ainda está afetada. O npm sugere um downgrade incompatível do Mammoth para 0.3.29; ele não foi aplicado. No pacote instalado, argparse é usado pelo executável CLI; a entrada de biblioteca utilizada pela KLIC não o carrega. Isso reduz a exposição no fluxo atual, mas não elimina o alerta da árvore instalada. A extração de anexos continua isolada em worker, com limite de memória, concorrência, cancelamento e prazo existentes.

O npm informou que uma cópia antiga da DLL de libvips não pôde ser removida porque estava em uso no Windows. Ela está somente em `node_modules`, ignorada pelo Git. Novos processos carregaram Sharp 0.35.5 e passaram pelos testes reais de processamento de avatar; nenhum processo do usuário foi encerrado para apagar a DLL.

## Cobertura da revisão

- Análise das entradas React, servidor Express e worker de anexos, com rastreamento de importações TypeScript e revisão das referências antes de excluir código.
- TypeScript já aplica `noUnusedLocals` e `noUnusedParameters`; nenhum erro de import ou variável sem uso foi ocultado.
- Ruff em `backend/app` não identificou imports/variáveis indefinidos ou sem uso das categorias F401, F841, F821 e F811.
- Revisão dos limites de cookies HTTP-only, permissões, contexto pessoal/corporativo, criptografia de tokens OAuth, tratamento de erros e arquivos privados, apoiada nos testes existentes.
- Varredura de padrões conhecidos de credenciais em 955 arquivos textuais rastreados, sem candidatos encontrados. Não é garantia de inexistência de todo tipo de segredo; não foram impressos conteúdos de credenciais.
- Componentes sem entrada atual, mas vinculados a testes, trabalho anterior ou recursos de Studios, foram preservados: placeholders de módulos, painéis de auditoria visual, catálogo de avatares, webhook, worker e implementações anteriores da KLIC. Ausência no grafo da tela não foi tratada como prova suficiente para apagá-los.

## Validações

| Verificação | Resultado |
| --- | --- |
| Baseline `npm run lint` | Aprovado; é `tsc --noEmit`, sem ESLint separado no projeto. |
| Baseline `npm test` | 218/218 aprovados. |
| Baseline `npm run build` | Aprovado. |
| Após atualização de dependências | Tipagem, 218 testes e build aprovados novamente. |
| Após limpeza de código e configuração | Tipagem, 223 testes Node + 2 testes Vite e build aprovados. |
| Artefatos frontend de produção | Os 76 arquivos de assets listados pelo build mantiveram os mesmos nomes/hash e tamanhos do baseline. |
| API local `/api/health` | HTTP 200, status `ok`. |
| Compilação Python `compileall -q app` | Aprovada. |
| Python: autenticação e API (`test_api.py`) | 9/9 aprovados. |
| Python: recorte API, workspaces, campanhas, aprovações, bridge, imagem, vídeo, timeline e conexões LLM | 55 aprovados; 2 falhas preexistentes em testes de derivação legada de imagem. |
| `tests/unit/craftState.test.ts` | 6 aprovados; 1 falha preexistente de expectativa de estrutura do App. |
| Ruff completo em `backend/app` | 80 ocorrências preexistentes, idênticas antes/depois: 67 E501, 11 I001, 1 UP037, 1 B905. Nenhuma regra desativada. |
| Suíte Python completa antes de alterar seu isolamento | 818 aprovados, 283 falhas, 112 skips existentes; 642,24 s. |
| Suíte Python completa após isolar uploads | 818 aprovados, 283 falhas, 112 skips existentes; 575,17 s. Os 283 identificadores dos testes com falha são exatamente os mesmos do baseline; nenhuma falha nova. |
| `git diff --check` | Aprovado. |

Para executar os testes locais, foram instalados somente no `.venv` os pacotes já declarados: Ruff 0.14.14, NumPy 2.4.4 e webrtcvad-wheels 2.0.14. A primeira coleta Python falhava por falta de NumPy. O recorte de mídia utilizou o FFmpeg já existente no diretório local de ferramentas, por ajuste temporário do PATH apenas no processo de teste. Os testes Python usam o banco SQLite temporário definido pelo conftest; bancos de desenvolvimento e produção não foram apagados ou migrados.

Quatro PNGs criados pelos testes antes da correção de isolamento foram movidos, por caminhos exatos verificados, para `.codex-runtime/cleanup-test-uploads/`. Continuam recuperáveis localmente e fora do Git. Nenhum upload preexistente foi removido. O conftest passou individualmente pelo Ruff após a alteração. Ao final da segunda suíte, `backend/data/uploads/` permaneceu sem arquivos: as novas fixtures foram isoladas e limpas na pasta temporária da execução.

Docker não está disponível neste ambiente, portanto não foi realizada uma construção da imagem. Não houve teste visual no navegador nem uso real de credenciais OAuth, geração paga ou gravação de microfone nesta tarefa.

## Bloqueios anteriores à limpeza

1. A suíte Python depende de arquivos de evidência que não estão no checkout. No baseline, 245 registros de erro são `FileNotFoundError`, incluindo políticas em `benchmarks/studios`, manifests/artefatos de workers e evidências históricas. Exemplo reproduzido: `artifacts/validation/video-creative-pilot/advanced-capabilities-20260901-v1/audit.json`, exigido por `test_advanced_video_capability_audit.py`. O Git não rastreia arquivos sob `artifacts/validation` neste HEAD. As evidências não foram inventadas nem os testes desativados.
2. `test_image_derivation.py` espera a derivação antiga de imagens. A rota existente já devolve HTTP 410 com `image_editor_replaced_by_photocraft` desde o commit 5cab414. Reativar o editor antigo alteraria o produto e contrariaria a preservação do Studios.
3. O teste de integração estrutural em `tests/unit/craftState.test.ts:69` ainda procura `<ClickoStudioView module="create-image"` diretamente em `App.tsx`. O trabalho local anterior moveu essa organização para Studios. Ambos os arquivos já estavam modificados antes desta tarefa e foram preservados.
4. O Ruff geral já apresentava 80 ocorrências. Muitas estão em arquivos do trabalho local anterior; nenhuma alteração prévia foi incluída nesta limpeza para zerar artificialmente o resultado.

## Git e envio

A publicação está retida pela condição do pedido: executar commits e push somente com as verificações aprovadas. As verificações gerais acima continuam reprovadas por condições preexistentes. Não houve commit, push, force-push, reset, stash, merge, exclusão de dados ou incorporação dos 97 arquivos de trabalho anterior.

O fetch final em 20/10/2026 confirmou novamente `0 ahead / 0 behind` para `origin/codex/klic-atualizacao-20260823`, no remoto indicado no início deste relatório. Não há conflito ou divergência remota a resolver; o impedimento é a validação geral reprovada. O índice foi mantido vazio e não há artefatos de teste, build ou credenciais preparados para envio.

As alterações desta tarefa estão identificadas na tabela de arquivos e prontas para revisão. Após resolver os bloqueios, os grupos sugeridos são `fix: harden provider errors and private development files` e `refactor: remove unused helpers and obsolete lockfile`, com os testes respectivos. A branch e a sincronização devem ser verificadas novamente antes do envio. Nenhum hash de commit novo existe para informar.

Para liberar o envio nas condições solicitadas: restaurar as evidências, políticas e manifests autênticos ausentes; alinhar os testes legados à migração real de Studios sem reativar módulos substituídos; resolver as ocorrências de lint do backend respeitando o trabalho local pendente; e repetir as verificações gerais. Os três alertas moderados restantes da árvore Mammoth também precisam permanecer registrados até existir uma correção compatível. Não foram geradas evidências fictícias nem eliminadas verificações para satisfazer o critério de publicação.
