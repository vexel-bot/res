# Clicko Studios — riscos e rollback

**Data:** 2026-08-23  
**Política:** toda mudança material mantém leitura compatível, evidência pós-migração e um caminho de retorno sem apagar dados.

## Registro de riscos

| ID | Risco | Prob. | Impacto | Sinal de detecção | Mitigação/gate |
| --- | --- | --- | --- | --- | --- |
| R-01 | UI aprovada continuar demonstrativa em produção autenticada | alta | crítico | salvar/reabrir perde alteração ou usa primeiro post do snapshot | E2E autenticado com IDs criados durante o teste; proibir fallback demo em status `ready`. |
| R-02 | Novo contrato tornar documentos `creative-v1` ilegíveis | média | crítico | erro de upcast, preview/export divergente | upcaster determinístico, fixtures legadas, dual-read e backup lógico. |
| R-03 | Duplicação de marca/campanha/workspace no domínio Studio | média | crítico | campos divergentes ou dados entre tenants | apenas refs estáveis/versionadas; constraints e authorization tests. |
| R-04 | Aprovação apontar para versão diferente da revisada | alta | crítico | edição após review altera artefato aprovado | pin de `documentId + version`; decisão concorrente e audit event. |
| R-05 | Idempotency key global colidir entre tenants/tipos | baixa | alto | duplicate retorna job de outro contexto | escopo/constraint composto e validação workspace/type/payload hash. |
| R-06 | Cancelamento nominal não interromper execução/render | média | alto | job `cancelled` produz output publicável | cooperative cancellation, discard de resultado tardio e testes de race. |
| R-07 | Render pesado permanecer na requisição web | alta | alto | timeout/worker web bloqueado | provider + job; manter Pillow sync apenas como compatibilidade de curto prazo. |
| R-08 | Provider/modelo vazar para o formato canônico | média | alto | campos obrigatórios específicos de SDK | ports, conformance tests e payload do provider isolado em lineage/adaptation metadata. |
| R-09 | Asset sem direitos/hash/proveniência | alta | alto | export sem origem comprovável | `AssetReferenceV1`, hash e rights status antes do slice comercial. |
| R-10 | Refactor de `CanonicalProduct.tsx` conflitar com UX em evolução | alta | alto | diff amplo em shell/CSS | extrair apenas slice tocado; não mudar shell/tokens; screenshots nos dois viewports. |
| R-11 | Feature legada desaparecer por não existir em frame | média | alto | rota/endpoint/ação some | inventário e smoke das 57 referências + lista explícita de capacidades legadas. |
| R-12 | Fallback Express ser tratado como geração real | média | alto | sucesso sem provider/model/lineage | estado `unavailable` ou provider trace obrigatório; sem fallback silencioso em Studio. |
| R-13 | Duix/HeyGem/OpenVoice introduzir risco jurídico/biométrico | média | crítico | execução sem consent grant válido | gate jurídico, finalidade/expiração/revogação/exclusão, amostra privada e revisão humana. |
| R-14 | Licença de FFmpeg/codec mudar conforme build | média | alto | binário usa componente GPL/nonfree não registrado | armazenar `ffmpeg -buildconf`, origem do binário e lista de codecs; revisão antes de adoção. |
| R-15 | Dados de uma marca aparecerem em outra | baixa | crítico | GET/worker retorna artefato externo | workspace em toda entidade/job/ref, queries escopadas e testes adversariais. |
| R-16 | E2E guest gerar falsa confiança | alta | alto | 14/14 passa sem uma mutation real | separar smoke visual de E2E funcional autenticado e marcar cobertura. |
| R-17 | Troca de storage tornar assets legados inacessíveis ou expor bucket | média | crítico | 404 após rollout ou URL pública sem autorização | backend persistido por asset, endpoint autenticado, URL assinada curta, migration inventory e rollback sem apagar objetos. |
| R-18 | Licença do código mascarar restrição dos pesos/auxiliares | alta | crítico | registry marca Apache/MIT enquanto modelo é OpenRAIL ou não comercial | registry por componente/digest, policy gate; MuseTalk/LatentSync rejeitados sob a regra atual. |
| R-19 | Benchmark incompleto ser divulgado como qualidade comprovada | média | crítico | score ausente vira zero/pass ou policy muda depois do resultado | policy congelada antes do run, digest obrigatório e decisão `incomplete` para qualquer evidência ausente. |
| R-20 | Ativar fila isolada sem worker compatível | média | alto | jobs acumulam em `queued` sem heartbeat/consumo | flag desligada por padrão; capacity/health/broker smoke antes da ativação; drenar e reverter flag. |
| R-21 | Provider ou membro ativar clone sem revisão válida | média | crítico | versão `active` sem preview/evaluation/reviewer | registry aprovado para automação, preview privado, última avaliação passed, decisão Owner/Admin e auditoria; publicação permanece separada. |
| R-22 | Exclusão biométrica parcial, cross-tenant ou falsamente concluída | baixa | crítico | objeto some sem receipt, referência viva quebra ou request fica `completed` com falha | feature flag off, preflight fail-closed, workspace check, legal hold, shared-reference scan, tombstone por objeto, retry idempotente e migration test. |

## Estratégia de rollback por fase

### Fase 0 — documentação

- Não altera comportamento.
- Rollback: remover somente `docs/studios/`; nenhum dado é afetado.

### Contratos e Kernel

- Novos módulos entram sem substituir os routers atuais.
- Schemas novos têm `schemaVersion` e upcasters; nunca reescrevem documentos antigos in-place sem cópia/version.
- Migração adiciona estruturas/colunas; downgrade só é autorizado enquanto nenhum dado exclusivo novo for necessário.
- Feature flag prevista: integração do Kernel pode ser desligada por ambiente/workspace enquanto o adapter antigo permanece.
- Verificação: contract tests, migration upgrade/downgrade/upgrade, OpenAPI e backend regression.

### Visual/Carrossel

- UI e rota continuam iguais.
- O componente funcional legado permanece até E2E autenticado e paridade visual.
- Dual-write temporário, se necessário, grava o canvas compatível e o envelope v1 na mesma transação.
- Rollback operacional: definir `VITE_STUDIO_KERNEL_ENABLED=false`, reconstruir o frontend e manter as mesmas rotas usando estado local; não apagar envelope/versões novas.
- Rollback de leitura: o caminho legado continua lendo `creative_documents.document` como `creative-v1`; documentos novos mantêm essa projeção da primeira página.
- Reativação: remover a variável ou defini-la como `true`; o adapter lista o documento por workspace/post e reabre o envelope preservado.

### Jobs/render

- Pillow atual permanece um `VisualRenderProvider` de compatibilidade.
- Job novo só substitui export síncrono depois de smoke de worker e idempotência.
- Rollback: bloquear novas filas, drenar/cancelar jobs seguros e reativar export sync para formatos suportados.
- Outputs produzidos depois de cancelamento são marcados inválidos e não entram em review/publicação.

### Providers externos

- Nenhum provider é migração de dados canônica.
- Desligar adapter não invalida `CreativeDocument`; apenas impede novas execuções daquela capability.
- Cada adapter exige estratégia de exportação/remoção de dados e revogação de credenciais.

### Exclusão física de identidade

- `IDENTITY_DELETION_EXECUTION_ENABLED=false` interrompe novos enqueues sem alterar planos ou tombstones existentes.
- O preflight bloqueia toda a tentativa antes do primeiro delete quando existe legal hold, referência externa ou asset de outro workspace.
- Cada objeto removido recebe tombstone e receipt em commit próprio; uma falha intermediária fica `failed` e o replay continua somente os objetos restantes.
- Downgrade de `0020` só é seguro antes de ativar a flag ou após preservar os receipts necessários. Desligar a flag não restaura bytes já apagados; recuperação exigiria backup autorizado e política jurídica específica.

## Checklist obrigatório antes de cada migração

1. Estado anterior e contagem de registros conhecidos.
2. Backup lógico ou versão preservada.
3. Upgrade e downgrade exercitados em banco efêmero.
4. Leitura de registros antigos pela versão nova.
5. Escrita nova legível pelo caminho de compatibilidade quando aplicável.
6. Tenant isolation e constraints.
7. Métrica/log para detectar erro e correlation ID.
8. Critério explícito de abortar rollout.
9. Procedimento e responsável pelo rollback.
10. Comparação funcional e visual com o baseline.

## Gates externos conhecidos

- HeyGem: URL confirmada (`Caladog/HeyGem`), mas a licença comunitária não atende ao critério “somente open source”; não adotar.
- Avatar/voz: revisão jurídica e de consentimento obrigatória.
- Exclusão física: domínio e migration estão comprovados localmente; ativação comercial exige storage compartilhado validado, control worker, monitoramento/alerta, runbook e aprovação de retenção/legal hold.
- Voz: policy congelada; Chatterbox/Kokoro/OpenVoice aguardam aprovação, corpus PT-BR consentido e worker externo.
- Lip-sync: MuseTalk e LatentSync rejeitados pela cadeia de pesos; nenhum provider aprovado.
- Motion: LivePortrait aguarda detector/landmarks permissivo e benchmark de paridade.
- Duix: licença comunitária e termos de modelo não atendem ao critério “somente open source”; não adotar.
- VPS: chave privada localizada, mas host/IP e usuário SSH ainda não foram registrados; nenhum segredo entra no repositório.
- FFmpeg: origem/build/licença do binário não auditadas.
- GPU/volume/custo/codecs: decisões de produto/infra não fornecidas.
- Essas pendências não bloqueiam contratos, Kernel, provider fake, Visual/Carrossel e testes seguros.

## Atualização de risco após o primeiro slice

- R-04 foi mitigado no slice Visual/Carrossel por `StudioReviewRequest.snapshot`; editar o documento depois do pedido não muda o material decidido.
- A corrida de dupla criação observada no E2E foi mitigada por `studio_creation_key` única; rollback desliga o adapter via `VITE_STUDIO_KERNEL_ENABLED=false` sem apagar documentos.
- Export multipágina é síncrono e permanece limitado a PNG ZIP. O gatilho de mover render a worker é volume/latência medidos, não antecipação arquitetural.
- Radar V2 não substitui o baseline: `RADAR_CONTEXTUAL_V2_SHADOW_MODE=false` interrompe novas avaliações e `RADAR_CONTEXTUAL_V2_ENABLED=false` oculta a consulta de auditoria; registros existentes permanecem legíveis.
