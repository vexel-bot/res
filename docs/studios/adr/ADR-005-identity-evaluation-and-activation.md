# ADR-005 — Avaliação e ativação governada de rosto e voz

**Status:** aceito para o domínio; providers biométricos ainda bloqueados  
**Data:** 2026-08-24

## Contexto

Consentimento por si só não prova que uma cápsula de identidade tem qualidade, que o preview foi revisado ou que a versão certa pode ser usada. Ativar automaticamente o resultado de um provider permitiria identity drift, voz ruim, artefatos e uso de consentimento expirado. O Studio precisa separar geração técnica, avaliação e decisão humana.

## Decisão

Versões de identidade e voz seguem o fluxo:

```text
draft → avaliação(s) failed/passed → revisão humana → active
   └──────────────────────────────────────────────→ rejected
active → superseded | revoked | deleting
```

Uma aprovação exige:

- versão ainda em `draft`;
- última avaliação com status `passed`;
- pelo menos um preview privado armazenado como `LibraryAsset` (URL externa não basta);
- checks sem falha e métricas normalizadas quando fornecidas;
- provider e modelo aprovados no registry para avaliação `automated` ou `combined`;
- consent grant ativo e com scopes correspondentes;
- membro `Owner` ou `Admin` fazendo decisão humana com comentário auditável.

Ativar uma nova versão marca a anterior como `superseded`. Rejeição é terminal para a versão; uma nova tentativa cria nova versão imutável.

## Uso por jobs

Um job que referencia rosto ou voz precisa usar versão `active`, carregar o mesmo `consentGrantId` e, quando rosto e voz são combinados, apontar para a mesma identidade. O consentimento é reavaliado no enqueue; expiração/revogação bloqueia a execução mesmo que a versão permaneça materialmente armazenada.

## Evidência e auditoria

`StudioIdentityEvaluation` preserva target/version, checks, métricas, previews, evaluator kind, provider/model registration, autor e timestamps. A revisão persiste reviewer, comentário e data na versão. Eventos de avaliação, ativação/rejeição e consentimento permanecem no audit trail.

## Segurança

- membros comuns podem consultar versões/evidências do próprio workspace, mas não homologar;
- preview continua atrás do endpoint autenticado; S3 usa URL assinada curta;
- nenhum resultado de provider altera diretamente o status da versão;
- aprovação de identidade não equivale a autorização de publicação: `publish.synthetic` e review do conteúdo continuam gates separados;
- não há publicação automática de mídia sintética.

## Deletion plan

Migration `0017` adiciona um pedido idempotente de exclusão. Ao planejar exclusão de uma identidade, o domínio bloqueia perfil/versões, inclui vozes vinculadas, cancela ou solicita cancelamento dos jobs e cria um snapshot das amostras, previews e derivados afetados. Amostras de origem não são marcadas para remoção por padrão.

O plano permanece em `planned` enquanto `IDENTITY_DELETION_EXECUTION_ENABLED=false`. A migration `0020` e a ADR-008 implementam legal hold, referências compartilhadas, tombstones, receipts e o executor idempotente, sem ativá-lo em nenhum ambiente externo.

## Gates restantes

- rollout do executor em storage/control worker de produção, com runbook, observabilidade e aprovação de retenção/legal hold;
- autenticação de callbacks internos de workers;
- thresholds por capability e benchmark PT-BR aprovados;
- detecção de spoof/liveness e revisão jurídica;
- disclosure/C2PA no output;
- interface visual da cápsula e comparação lado a lado.

Até esses gates passarem, nenhum adapter de Chatterbox, MuseTalk, LivePortrait ou similar é tratado como capacidade comercial entregue.
