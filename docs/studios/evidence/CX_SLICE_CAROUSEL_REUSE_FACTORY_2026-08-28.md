# Evidência — Carrossel, Reuse e Fábrica

Data: 2026-08-28

Status: slice implementado e validado; a meta maior de Studios permanece aberta.

## Resultado executável

- O registro canônico contém a rota `/factory/:roundId`, os quatro novos contratos de tela e oito ações explícitas de Carrossel, Reuse e Fábrica.
- O Carrossel possui preview contínuo real, seleção do slide, duplicação, exclusão, reordenação, autosave da ordem/funções narrativas, versionamento, exportação e envio para revisão.
- O Reuse cria filhos independentes pela API, sem copiar métricas, e grava `clicko.content-lineage.v1` com origem, hipótese, itens preservados e itens adaptados.
- O handoff Reuse → Fábrica transporta a origem e os IDs dos derivados na rota.
- A Fábrica cria ou reutiliza um `CreativeDocument` por derivado, fixa uma versão, enfileira um job idempotente `document_snapshot` e persiste a rodada como `factory_round` do workspace.
- Cada célula preserva `postId`, `documentId`, `versionNumber`, `jobId`, estado e gate humano. Nenhuma publicação é feita automaticamente.
- Views e ações contratuais emitem o evento neutro `clicko:experience`; nenhum fornecedor de analytics foi acoplado ao núcleo.

## Estados honestos e recuperação

- Sem derivados, a Fábrica permanece em pré-flight e explica o handoff necessário.
- Falhas parciais preservam as células já criadas e persistem a célula bloqueada com o erro observado.
- O botão de revisão em lote só é habilitado quando existe uma versão fixa.
- O preview do Carrossel é um diálogo acessível, fecha por botão ou `Escape` e permite voltar ao slide selecionado.
- Face e voz não participam deste slice; nenhum gate biométrico foi contornado.

## Validações executadas

- `npm run lint`: passou.
- `npm run build`: passou.
- `npm run audit:cx`: passou com 43 rotas, 59 URLs conhecidas, zero órfãs e zero conflitos.
- `npm run test:cx-contracts`: 6/6 passaram.
- `npm run test:e2e`: 21/21 passaram, incluindo Reuse → Fábrica autenticado e telemetria do preview.
- `python -m ruff check` nos arquivos alterados: passou.
- Testes selecionados de histórico e recursos do workspace: passaram.
- A suíte Python completa chegou a 100% e encontrou uma falha no comportamento eager do Celery. `task_eager_propagates` foi corrigido para produzir um `EagerResult` falho auditável; o teste antes falho passou isoladamente. A suíte Python completa ainda não foi repetida após essa correção.

## Rollback e compatibilidade

- Não há migração de banco neste slice; `factory_round` reutiliza `WorkspaceResource`.
- O job usa o provider determinístico existente `builtin.snapshot` e as fronteiras atuais de documento/versão/job.
- O fluxo anterior de demonstração continua disponível para usuários guest.
- Remover o novo `kind`, a leitura de `factoryRounds` e a rota dinâmica restaura a superfície anterior sem tocar em posts, documentos ou jobs já existentes.

## Próxima passagem

Implementar o slice de Vídeo assistido sobre `CreativeDocument`, ingest/proxy/waveform, decisões não destrutivas, render observável e gates físicos/visuais, preservando a mesma identidade de documento e sem introduzir acoplamento direto a OpenCut ou a um provider de IA.
