# ADR-002 — Creative Document canônico e provider-neutral

**Status:** aceito  
**Data:** 2026-08-23  
**Relacionada:** `docs/adr/0004-editor-autosave.md` permanece válida para autosave; esta ADR amplia o formato de domínio.

## Contexto

O backend armazena `CreativeCanvas` v1 com dimensões, tokens e camadas. Esse formato já é independente de Fabric/Konva, mas representa apenas canvas único e não inclui estratégia, páginas/cenas, assets com direitos, lineage, review e export.

## Decisão

Introduzir `CreativeDocumentV1` como envelope canônico, JSON serializável e versionado. Ele contém:

- identidade/status/workspace/autoria/timestamps;
- referências a campanha, post, oportunidade e versão da marca;
- `CreativeBriefV1`;
- composição provider-neutral com páginas/cenas/camadas e timing opcional;
- `AssetReferenceV1` com origem, direitos, hash e proveniência;
- lineage de gerações e adaptações;
- review/export refs;
- version/correlation/schema version.

O `CreativeCanvas creative-v1` atual será adaptado como composição visual de uma página. Documentos antigos serão upcast em leitura e permanecerão legíveis. Formatos de Fabric, Konva, Remotion ou provider podem existir somente como cache/metadado de adapter não canônico.

## Invariantes

1. `workspaceId` é obrigatório e não muda.
2. Referências cruzadas devem pertencer ao mesmo workspace.
3. `schemaVersion` desconhecida falha explicitamente.
4. Documento/version publicado para review é imutável; edição cria nova versão.
5. Assets precisam de origem/rights status antes de export publicável.
6. Provider/modelo/parâmetros ficam no lineage, nunca controlam a estrutura.
7. Serialização e upcast são determinísticos.

## Alternativas rejeitadas

- Salvar JSON de Fabric/Konva: acopla persistência à engine.
- Manter apenas `CreativeCanvas`: não cobre carrossel, vídeo, brief ou lineage.
- Novo documento sem adapter: quebra registros e editores existentes.
- Binários embutidos no JSON: inviabiliza storage, dedupe e autorização.

## Migração

- manter coluna/documento atual;
- adicionar envelope/metadata/version records de forma aditiva;
- upcast de `creative-v1` para uma página visual;
- dual-write temporário somente quando necessário;
- fixtures de documentos atuais e rollback documentado.

## Verificação

- contract tests de JSON e invariantes;
- upcast/round-trip de fixtures atuais;
- provider fake duplo;
- render atual produz saída equivalente;
- migration upgrade/downgrade/upgrade;
- E2E reabre e revisa a mesma versão.
