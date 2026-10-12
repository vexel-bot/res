# Substituição dos Studios por Craft

Estado em 12 de outubro de 2026: implementação no checkout de integração,
com fontes completos, builds reais dos três motores e exportação/cancelamento
pela fila de servidor validados. O aceite final ainda depende da qualificação
de projetos reais e dos fluxos descritos abaixo.

Checkout: `C:/Users/edugu/Downloads/res-craft-integration`, branch
`codex/craft-studios`. O projeto original em `C:/Users/edugu/Downloads/res`
permanece preservado. O commit de base da integração registra as mudanças
locais do projeto antes das importações.

## Fontes e procedência

| Fonte | Revisão fixada | Arquivos upstream conferidos |
|---|---|---:|
| PhotoCraft | `a7f26522ff84cd427c8a5d54b0e8ded7b56fb296` | 1.569 |
| FilmCraft | `0800a8b0aa4a703ba42172f415b45a61f8d8a5e1` | 1.236 |
| EffectCraft | `67434e90388b6dca4417555346fa6850b6f96033` | 1.016 |
| craft-libs | `5c874d51eeb3de70e735c8ce87a59a7dedd47675` | 41 |
| craft-fonts | `abb83316d96aa59c1cf64784289e378fe9fa5695` | 25 |
| FilmCraft exigido pelo EffectCraft | `2c5ba7a72619935f0481f99d59409e0d1844b234` | 951 |

Os três editores foram importados por subtree, com seus históricos. Os seis
inventários somam 4.838 arquivos e foram comparados aos blobs Git das revisões
fixadas. As interfaces originais, documentação, testes e recursos upstream
permanecem nos fontes. As adaptações Clicko ficam fora desses diretórios.

Os mirrors completos e bundles verificados ficam em
`.codex-runtime/craft/upstream`; preservam refs, branches, tags e histórico.
O script `scripts/craft/mirror.py --bundle` reproduz esse material. O manifesto
`workers/craft/sources.lock.json` fixa árvores, blobs e checksums dos inventários.
Cada adaptador tem seu próprio `Cargo.lock`. O EffectCraft mantém a dependência
FilmCraft antiga, independentemente da montagem com o FilmCraft mais recente.

Os builds próprios incluem licenças, atribuições e checksums. As marcas e logos
upstream ficam nos fontes de referência; o frontend e executáveis distribuídos
pela integração usam Clicko. Bundles WASM incluem os avisos e licenças das fontes
e recursos, inclusive fontes tipográficas, em seus diretórios `licenses`.

## Implementação disponível

- Studio de Imagens com PhotoCraft; Studio de Vídeos com FilmCraft e área de
  composição e efeitos com EffectCraft. As entradas de edição, inclusive da
  biblioteca, chegam ao novo frontend React.
- Adaptadores Rust reais e previews WASM em Web Workers dedicados. Os modelos,
  comandos, renderizadores e formatos nativos pertencem aos projetos Craft.
- `NativeEditorStateV1`, projetos `.pcraft`, `.fcproj` e `.ecproj`, checksum de
  assets/fontes, páginas de carrossel, fontes originais e dependências vinculadas.
- Comandos manuais e por IA com o mesmo contrato, revisão esperada, idempotência,
  histórico, undo/redo, autosave e recuperação. A IA usa os provedores e controles
  de orçamento já existentes.
- Uploads por streaming, salvamento com conflito explícito, snapshots imutáveis
  de render, progresso/cancelamento, exportação, revisão e publicação vinculadas
  ao artefato e à versão aprovados.
- Migração para os modelos nativos com arquivo dos originais e pendências
  explícitas para operações que não podem ser convertidas com fidelidade.
- Recuperação das camadas visuais e motion graphs arquivados em composições
  EffectCraft editáveis, sem duplicar footage/áudio/legendas da montagem.
  A interface abre a composição e oferece seu retorno ao FilmCraft. Composições
  pendentes precisam ser vinculadas antes da exportação. Reabrir uma composição
  já recuperada mantém a revisão e as aprovações da montagem.
- Componentes, timelines, hooks e renderizadores exclusivos dos editores antigos
  retirados da execução. Os workers anteriores e testes específicos desses
  motores estão arquivados em `docs/studios/archive`, fora dos builds e imports.
  Flags de ambiente antigas não reativam esses motores. FFmpeg permanece como
  utilitário de mídia.

O frontend oferece operações conforme as capacidades reais dos builds. Fontes
externas e mídias acima dos limites locais usam o mesmo motor nativo no servidor
para a prévia. Nenhum editor antigo serve de alternativa.

## Evidência obtida

| Verificação | Resultado e limite |
|---|---|
| Integridade dos seis inventários upstream | Passou: 4.838 arquivos |
| Mirrors/bundles Git | `fsck` e verificação dos bundles passaram |
| Builds nativos Photo/Film/Effect | Concluídos; imagem `clicko-craft-runtime:local` gerada |
| WASM Photo/Film/Effect | Bundles gerados; execução real dos três em workers validada |
| Arquivo nativo → WASM → salvar/reabrir → PNG | Passou nos três motores; SHA-256 igual à referência nativa |
| EffectCraft: tempo de entrada/saída, alpha e reabertura | Passou no WASM real; canto transparente e centro vermelho verificados |
| API real dos três motores | Criação, migração, edição, histórico, conflito, reabertura e exportação passaram novamente nos builds finais |
| Áudio real em FilmCraft | Importação, mix e MP4 com áudio não silencioso passaram |
| EffectCraft → FilmCraft | WebM transparente, atualização da mesma composição, áudio preservado e bundle com `.ecproj`/WAV passaram |
| Prévia do frontend → exportação nativa | PNG do worker real da interface conferido por SHA-256 nos três motores |
| Imagem media CPU | Build concluído; usuário 10001, root somente leitura, sem rede na atestação e sete ferramentas verificadas |
| Inventário CycloneDX | 825 componentes instalados/registrados nos locks, com versões, imagem e checksums registrados |
| Fila HTTP/Redis/Celery real | Exportação MP4 e checksum passaram no worker atestado e isolado |
| Cancelamento nativo em execução | Passou novamente na imagem atualizada durante exportação real; nenhum artefato parcial publicado |
| Contratos de backend | 23 testes passaram, incluindo falha de commit, recuperação de efeitos, snapshots adulterados, rejeição de carrossel inválido e impossibilidade de reativar motores antigos |
| Criação com carrossel inválido | Rejeitada com `422` antes da persistência; nenhum documento criado. O caso antes retornava `500` |
| Regressões dos adaptadores Rust | Photo 2, Film 3 e Effect 9 testes passaram; transparência total/parcial e reabertura verificadas |
| Recuperação real de camadas | Animação de opacity, fundo transparente, replay, CAS e composição vinculada passaram nos motores reais |
| Recuperação no frontend | Navegação para a composição, worker WASM, paridade de pixels e revisão da montagem preservada passaram |
| Referências CLI upstream PhotoCraft e FilmCraft | Compilaram integralmente; CLI EffectCraft e interfaces desktop ainda não qualificados |
| `.pcraft` Clicko → CLI PhotoCraft original → PNG | Abriu e converteu; pixels RGBA idênticos ao adaptador, com codificação PNG diferente |
| `.fcproj` Clicko → CLI FilmCraft original → PNG | Abriu e renderizou; pixels RGBA idênticos ao adaptador em 320 × 320 |
| Concorrência HTTP com motor real | Duas edições na mesma revisão: uma salva e uma `409`; revisão única, replay estável e undo restaurando os bytes originais |
| Testes unitários upstream `photocraft-engine` | 1.285 passaram, 12 ignorados e um falhou: `destructive_levels_dont_clip_in_32_bit`; suíte não aprovada |
| Integração upstream `photocraft-engine` | 45 executáveis concluídos: 129 testes passaram, cinco ignorados e nenhuma falha |
| Transporte Rust compartilhado | 6 testes passaram, incluindo frames e schemas de parâmetros |
| Runner isolado | 3 testes passaram |
| Estado e rotas TypeScript | 7 testes passaram |
| Interface Playwright | 7 testes passaram: edição, autosave, páginas, IA/undo, cancelamento, conflitos e recuperação |
| Compilação editorial de documentos | 27 testes passaram |
| Publicação e áudio | 8 testes passaram; binding a export nativo, pacote, revisão, agendamento e isolamento |
| Avatar, biblioteca, API, aprovações e workspace | 32 testes de regressão passaram |
| Ensaio do banco existente | 31 vídeos convertidos para arquivos FilmCraft válidos e reabertos; originais/versões arquivados e checksums conferidos numa cópia privada |
| Recuperação dos documentos existentes | 31 montagens nativas reabertas; 29 composições EffectCraft criadas e reabertas; dois vídeos sem camadas visuais. Ensaio somente em cópias privadas |
| Fidelidade desse ensaio | 30 dos 31 vídeos exigem revisão. Os 1.267 avisos da montagem e 1.572 da composição preservam propriedades não representadas, hierarquia/pivôs, máscaras e receitas avançadas. A reabertura não comprova fidelidade |
| TypeScript e build de produção | Passaram; build repetido com os três bundles WASM finais e workers |
| Coleção da suíte de backend | Sem erros de importação após arquivar testes exclusivos dos renderizadores retirados |
| Regressão ampla do backend | Não qualificada: execução interrompida após falhas no primeiro bloco; amostras diagnosticadas exigem fixture local de auditoria ausente e esperam acesso ao renderer Alight retirado |

Os testes de contrato usam doubles somente nas fronteiras de processo/provider.
Eles não comprovam fidelidade visual nem uma chamada a um provedor pago de IA.
As verificações de pixels descritas na tabela executaram os motores reais.
A suíte completa de regressão do sistema e as suítes completas upstream ainda
não foram qualificadas. As interfaces desktop upstream não foram recompiladas;
os seus fontes completos estão preservados.

Na revisão PhotoCraft fixada, o teste de níveis de 32 bits espera preto em zero,
mas obteve `-0.0796427`. O comentário do próprio teste descreve extrapolação em
32 bits; ainda é necessário resolver a divergência entre expectativa e resultado
antes de qualificar essa operação HDR. O fonte e o teste upstream permanecem
intactos. A falha está em `upstream-photo-engine-tests-retry.log` e não foi
contabilizada como sucesso dos testes Clicko.
Os testes de integração foram executados separadamente com `--test '*'`, pois
o Cargo encerrou a primeira execução após a falha unitária. O consolidado
`upstream-photo-tests-results.json` preserva os dois resultados, sem declarar
a suíte upstream aprovada.

O Docker Desktop foi atualizado para 4.94.0 (241994), com Engine 29.8.2. O
problema anterior de inicialização deixou de bloquear os builds e jobs. Houve
uma interrupção posterior do daemon durante a qualificação upstream; o serviço
foi reiniciado e o último documento do ensaio foi repetido com sucesso em outra
cópia privada. A interrupção não foi contabilizada como aprovação dos testes.
Imagem media CPU validada nesta rodada:
`sha256:a7b4d7eafc7e4b843a6dacf338337fdcbb4e22a245b80991c035aeb97434d4d7`.
Esse identificador corresponde à imagem local; não houve publicação em registry.
Evidências estão em `media-worker-attestation.json`, `media-worker-sbom.cdx.json`
e `queue-acceptance-results.json`, no diretório de QA ignorado.

O teste de fila usa cópia do banco em volume Linux descartável. A primeira
tentativa identificou erro de I/O ao compartilhar SQLite simultaneamente entre
Windows e Linux por NTFS. A infraestrutura de QA foi corrigida, e o worker agora
recupera a transação antes de registrar uma falha SQLAlchemy. Projetos e banco
originais não foram usados para escrita nesse teste.

O ensaio de recuperação está registrado em
`migration-qa-567b7cd1d286/results.json`; o último documento, interrompido pelo
daemon, foi concluído em `migration-qa-9e51a24f9da7/results.json`. Ambos ficam em
`.codex-runtime/craft`, fora do Git, pois contêm informações de projetos locais.
O consolidado `existing-recovery-summary.json` registra os checksums das duas
evidências e a substituição do resultado interrompido pelo resultado repetido.
O script de ensaio aceita `--document-id` para repetir somente uma pendência,
sempre copiando o banco de origem em modo somente leitura; falhas retornam
código de saída não zero. As composições recuperadas continuam pendentes de
revisão e vínculo na montagem, sem promover a migração no banco original.

## Pendências para o aceite final

1. Qualificar migrações de documentos reais com efeitos/receitas avançadas,
   concorrência, arquivos grandes, recuperação e cancelamento de exportações
   maiores. O cancelamento durante um fixture de 60 segundos já passou; faltam
   os casos reais de carga. Pendências de conversão preservam os originais.
2. Qualificar a IA com o provedor configurado, builds de referência upstream e
   regressões dos fluxos de geração, avatar, revisão e publicação. Não houve
   promoção de produção nem implantação na VPS.

## Retomada reproduzível

Execute no checkout de integração. Use banco e storage isolados para QA.

```powershell
python scripts/craft/provenance.py
python scripts/craft/build.py
python scripts/craft/build.py --wasm
docker build --file workers/media-cpu/Dockerfile --tag clicko-media-cpu:craft .
npm run lint
npm run test:craft
npm run build
$env:PYTHONPATH = 'backend'
python -m pytest backend/tests/test_craft*.py backend/tests/test_worker_runtime.py backend/tests/test_creatives.py
npx playwright test --config=playwright.craft.config.ts
```

Com API de QA em `8018` e frontend em `3018`:

```powershell
python scripts/craft/acceptance.py
python scripts/craft/media_acceptance.py
python scripts/craft/recovery_acceptance.py
python scripts/craft/concurrency_acceptance.py
python scripts/craft/worker_acceptance.py
docker pull redis:8.2.1-alpine
python scripts/craft/queue_acceptance.py
node scripts/validation/craft-browser-parity.mjs
node scripts/validation/craft-recovery-browser.mjs
node scripts/validation/craft-wasm-reference.mjs
node scripts/validation/craft-wasm-effects.mjs
```

Os dois últimos testes podem usar as referências nativas já salvas, mesmo com
Docker indisponível. Logs, projetos, PNGs, exports e credenciais de QA ficam em
`.codex-runtime/craft`, ignorados pelo Git. Essas verificações não substituem as
qualificações dos projetos reais e da implantação.
