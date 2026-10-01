# Clicko Studios — fronteira e ownership

**Status:** aprovado para migração incremental  
**Data:** 2026-08-23

## Decisão

Studios será um bounded context dentro do monorepo e do monólito modular atual. A fronteira começa em contratos, serviços e routers próprios; não começa por um segundo repositório, autenticação ou shell.

```text
Sistema principal                                Studios
workspace + brand + campaign + opportunity       brief + creative document
approval + publishing + analytics          →     composition + version + render
                                            ←     artifact + lineage + review request
                 contratos v1 + referências estáveis
```

## Matriz de ownership

| Capacidade/dado | Owner | Acesso pelos Studios |
| --- | --- | --- |
| Conta, autenticação e usuário | sistema principal | usuário autenticado e autoria por contrato/contexto. |
| Workspace, membership, papel e entitlement | sistema principal | referência `workspaceId`; autorização delegada ao guard compartilhado. |
| Memória e versões da marca | sistema principal | `BrandMemoryVersionRef`, sem cópia mutável. |
| Radar, fontes, scoring e oportunidade | sistema principal | `OpportunityEvidenceRef`, com fonte, confiança e temporalidade. |
| Campanha e calendário | sistema principal | `CampaignContextRef`; Studio não cria uma campanha paralela. |
| Aprovação, comentários e publicação | sistema principal | Studio solicita revisão e devolve `ArtifactReference`. |
| `CreativeBrief` aplicado à peça | Studios | pode referenciar contexto externo, mas pertence ao ciclo criativo. |
| `CreativeDocument`, versões e lineage | Studios | fonte de verdade do artefato editável. |
| Composição visual/carrossel/vídeo | Studios | provider-neutral; adapters traduzem para engines. |
| `GenerationJob`, progresso e artefatos intermediários | Studios/infra compartilhada | estado persistente, isolado por workspace e correlation. |
| Providers de IA/mídia | adapters dos Studios | nenhuma UI ou entidade de domínio chama SDK específico. |
| Assets binários | storage compartilhado | Studio usa `AssetReference`; metadados de direitos/proveniência são obrigatórios. |
| Performance e aprendizado publicado | sistema principal | Studio recebe `PerformanceFeedback`, sem cruzar tenants. |
| Consentimento de rosto/voz | identidade/Studios com governança principal | contrato explícito; bloqueia provider e publicação quando inválido. |

## Módulos alvo no estágio atual

```text
backend/app/
  domain/studios/        # modelos de domínio e eventos sem FastAPI/SQLAlchemy/provider
  services/studios/      # casos de uso e ports
  providers/studios/     # adapters substituíveis
  routers/studios.py     # API v1 do bounded context
  workers/               # execução de jobs fora da requisição web

src/studios/
  shared/                # contratos e adapters de UI
  direction/
  visual/
  carousel/
  video/
  presenter/
  factory/
  review/
```

A estrutura é uma direção de dependência. A migração deve extrair por slice e manter os componentes aprovados onde estão enquanto adapters conectam o Kernel.

## Contratos de entrada e saída

O sistema principal abre um Studio com:

- `schemaVersion`;
- `workspaceContext`;
- `brandMemoryVersionRef`;
- `campaignContextRef` opcional;
- `opportunityEvidenceRef` opcional;
- `postRef` opcional;
- `assetReferences` autorizadas;
- autoria e correlation ID.

O Studio devolve:

- `CreativeDocumentRef` + versão;
- `ArtifactReference` exportado;
- lineage de assets/provider/modelo/parâmetros;
- status e resultado do job;
- `ReviewRequest` para o sistema principal.

## Regras de dependência

1. `domain/studios` não importa FastAPI, SQLAlchemy, Celery, PIL, SDK de IA ou componentes React.
2. Providers implementam ports definidos pelo domínio/aplicação; domínio nunca conhece Vane, OpenVoice, FFmpeg, Fabric, Konva ou Remotion.
3. Routers validam autenticação/workspace e chamam casos de uso; não concentram regra de geração.
4. Persistência armazena o documento canônico. Payload interno de engine pode existir apenas como cache/adaptation metadata descartável.
5. Marca, campanha, oportunidade, aprovação e publicação são referenciadas por ID + versão, nunca duplicadas.
6. Toda leitura/escrita inclui workspace e retorna 404 para outro tenant.
7. Jobs pesados nunca executam dentro da requisição web.
8. Rotas atuais permanecem; adapters fazem a transição até a nova API possuir paridade.

## Anti-corruption layer atual

| Origem atual | Adapter necessário | Contrato destino |
| --- | --- | --- |
| `Campaign.brief/strategy` JSON | campaign-to-brief | `CreativeBriefV1` |
| `Opportunity` + `ExternalSignal` | opportunity-to-evidence | `OpportunityEvidenceRefV1` |
| `BrandProfile.versions` | brand-to-ref | `BrandMemoryVersionRefV1` |
| `CreativeCanvas creative-v1` | canvas-v1 adapter | composição do `CreativeDocumentV1` |
| `CreativeDocument` ORM existente | repository adapter | aggregate/document version do Kernel |
| `LibraryAsset` | asset adapter | `AssetReferenceV1` |
| `ApprovalEvent`/post status | review adapter | `ReviewRequest`/`ApprovalDecisionRef` |
| `JobAudit` Radar | compatibility adapter | `GenerationJobV1` apenas onde semântica for compatível |
| `workspace_resources.presenter_session` | presenter compatibility | sessão legada; consentimento futuro é entidade separada. |

## Não objetivos desta fronteira

- redesenhar shell, navegação, Home ou as 37 telas;
- mover Radar, marca, campanha, approval ou publishing ao Studio;
- criar microserviço/repositório agora;
- adotar engine canvas antes de spike;
- integrar avatar/voz antes dos gates jurídico, consentimento e benchmark;
- remover superfícies legadas sem feature parity e telemetria.

## Critérios de enforcement

- testes arquiteturais/import checks impedem domínio de importar providers/frameworks;
- contract tests validam payload v1 e round-trip JSON;
- integration tests exercitam autorização e referências cruzadas de workspace;
- provider fake demonstra substituição sem alterar domínio;
- E2E autentica e percorre contexto principal → Studio → review/export → retorno.
