# Substituição dos Studios por Craft

Estado em 12 de outubro de 2026: implementação no checkout de integração,
com fontes completos e builds reais dos três motores. O aceite final ainda
depende das verificações de servidor descritas abaixo.

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
| API real dos três motores | Criação, migração, edição, histórico, conflito, reabertura e exportação passaram na rodada anterior |
| Áudio real em FilmCraft | Importação, mix e MP4 com áudio não silencioso passaram |
| Contratos de backend | 19 testes passaram; teste adicional de impossibilidade de reativar os motores antigos também passou |
| Transporte Rust compartilhado | 6 testes passaram, incluindo frames e schemas de parâmetros |
| Runner isolado | 3 testes passaram |
| Estado e rotas TypeScript | 7 testes passaram |
| Interface Playwright | 7 testes passaram: edição, autosave, páginas, IA/undo, cancelamento, conflitos e recuperação |
| Compilação editorial de documentos | 27 testes passaram |
| Publicação e áudio | 8 testes passaram; binding a export nativo, pacote, revisão, agendamento e isolamento |
| TypeScript e build de produção | Passaram; build inclui os três bundles WASM e workers |
| Coleção da suíte de backend | Sem erros de importação após arquivar testes exclusivos dos renderizadores retirados |

Os testes de contrato usam doubles somente nas fronteiras de processo/provider.
Eles não comprovam fidelidade visual nem uma chamada a um provedor pago de IA.
As verificações de pixels descritas na tabela executaram os motores reais.
A suíte completa de regressão do sistema e as suítes completas upstream ainda
não foram qualificadas. As interfaces desktop upstream não foram recompiladas;
os seus fontes completos estão preservados.

## Pendências para o aceite final

1. Recuperar o engine Linux do Docker Desktop. Ele não inicia devido ao socket
   `sailor-ingest.sock`; a tentativa de limpeza manual foi bloqueada pela revisão
   automática de execução. Reinícios oficiais não resolveram. A preferência
   temporária de downloads de atualização foi restaurada ao valor original.
2. Repetir a aceitação HTTP nos builds finais e a comparação da prévia da
   interface com a exportação. Atualizar os bundles Photo/Film após as últimas
   alterações de migração e schemas, e repetir a paridade de operações completas.
3. Concluir o teste de ligação EffectCraft → FilmCraft com WebM transparente,
   atualização da mesma composição na timeline, manutenção do áudio e bundle
   editável. O teste existe; sua rodada anterior parou no schema de `edit.clear`,
   corrigido e já validado no WASM. O caminho completo de servidor ainda precisa
   ser repetido.
4. Construir e atestar a imagem `workers/media-cpu/Dockerfile`, conferir suas
   versões reais, digest OCI, SBOM e execução de jobs. O Dockerfile e manifesto
   foram substituídos, mas essa imagem ainda não foi construída.
5. Qualificar migrações de documentos reais com efeitos/receitas avançadas,
   concorrência, arquivos grandes, recuperação e cancelamento de exportações
   demoradas. Pendências de conversão preservam os originais e exigem revisão.
6. Qualificar a IA com o provedor configurado, builds de referência upstream e
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
node scripts/validation/craft-browser-parity.mjs
node scripts/validation/craft-wasm-reference.mjs
node scripts/validation/craft-wasm-effects.mjs
```

Os dois últimos testes podem usar as referências nativas já salvas, mesmo com
Docker indisponível. Logs, projetos, PNGs, exports e credenciais de QA ficam em
`.codex-runtime/craft`, ignorados pelo Git. Essas verificações não substituem os
testes pendentes de exportação no servidor.
