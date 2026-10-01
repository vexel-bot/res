# Implementação — controle editorial do piloto UGC/avatar

Data: 05/09/2026. Workspace: `C:\Users\edugu\Downloads\res`.

Atualização posterior: o [incremento de interface no Video Studio](CLICKO_EDITORIAL_UI_IMPLEMENTATION_2026-09-05.md) implementou a aba Revisão e o cliente TypeScript. A descrição abaixo registra o estado da entrega original do backend; os itens sobre ausência de interface são históricos, não o estado atual.

## Entrega desta etapa

Primeiro incremento técnico da reconstrução: plano editorial e revisões humanas vinculados ao documento, à sua revisão e aos assets reais. Implementação de backend; não é a conclusão do novo anúncio, do casting ou da composição avançada.

- Contratos tipados para beats, plano, revisão e prontidão.
- Eventos persistidos na tabela existente `studio_domain_events`, sem nova migration.
- Sete decisões independentes: prova, roteiro, storyboard, animatic, voz, rosto e cenário.
- Autor da revisão e data definidos pelo servidor; o cliente não pode fornecer uma identidade de revisor arbitrária.
- Aprovação exige evidência do documento, com verificação do arquivo e checksum, limitada a 100 MiB por evidência.
- Novo plano não herda aprovações anteriores. Rejeições e revisões antigas ficam preservadas.
- Alteração de revisão, conteúdo, checksum, disponibilidade ou metadados de origem invalida a elegibilidade.
- Verificação antes de enfileirar e novamente no worker; um job antigo não pode usar a aprovação de um plano novo.
- Pré-produção aprovada libera somente tentativa de render privado, sujeita aos demais gates. Publicação do fluxo inscrito permanece bloqueada nesta etapa, até existir revisão final de montagem/vídeo integrada.

## Limite de ativação

O fluxo é inscrito explicitamente por `POST /editorial-plans`. Não é uma mudança automática de todos os documentos existentes. Depois da inscrição, apagar flags no JSON do documento não remove o controle: a inscrição reside no servidor.

Documentos legados continuam com os gates anteriores. Não houve migração automática do Caio, importação dos arquivos privados para a biblioteca, nova aprovação, alteração da rejeição ou cadastro de uma identidade como aprovada. A inscrição do projeto real depende de um documento canônico com assets válidos e plano concreto; não foram inventados IDs.

## API implementada

Prefixo comum: `/api/v1/studios/v1/documents/{document_id}`.

| Método / rota | Finalidade | Permissão |
|---|---|---|
| `GET /editorial-readiness` | Consultar plano vigente, últimas decisões e bloqueios | Membro do workspace |
| `POST /editorial-plans` | Registrar plano para a revisão atual | Owner/admin |
| `POST /editorial-reviews` | Aprovar/rejeitar um eixo do plano vigente | Owner/admin |

POSTs exigem `Idempotency-Key`. Repetir a mesma chave e payload retorna o registro original; payload diferente conflita. Repetir uma aprovação antiga depois de uma rejeição não altera a decisão vigente.

Exemplo estrutural de plano — substituir os placeholders por IDs reais; este exemplo não foi submetido:

```json
{
  "expectedDocumentRevision": 1,
  "workflow": "ugc-avatar",
  "objective": "Demonstrar uma operação verificada do Clicko para agências",
  "cta": "Solicitar acesso ao piloto",
  "beats": [
    {
      "id": "demonstracao",
      "message": "Explicar a consequência de uma revisão",
      "visualAction": "Mostrar estado anterior, operação e estado revisado",
      "editReason": "O corte revela a diferença relevante",
      "evidenceAssetIds": ["ID_REAL_DA_EVIDENCIA"]
    }
  ]
}
```

Exemplo estrutural de revisão — não constitui aprovação real:

```json
{
  "planId": "ID_REAL_DO_PLANO",
  "axis": "voice",
  "decision": "rejected",
  "evidenceAssetIds": ["ID_REAL_DA_AMOSTRA"],
  "notes": "Registrar aqui os timestamps e problemas realmente ouvidos."
}
```

`fullRenderEligible` não certifica naturalidade, direitos ou eficácia comercial; representa a presença das decisões exigidas e validade das vinculações. `publicationAuthorized` permanece falso. Sem inscrição, a resposta identifica `managed=false`, não uma aprovação implícita.

## O que não foi afrouxado

- Uma fonte Sora não passa a ser `user-upload` para contornar o renderer.
- Narração não passa a ser som natural para contornar o contrato de áudio.
- QC técnico não conta como aprovação estética.
- Registro de revisão não concede consentimento ou licença.
- Nenhum provider foi ativado e nenhuma API paga foi chamada.
- Não há geração de rosto, clonagem vocal nova ou anúncio novo nesta entrega. Os testes de mídia usam fixtures técnicas, não o Caio.

## Validação

- Dez testes novos de controle editorial: inscrição, sete decisões, fila, rejeição, replay, mudança de revisão/origem, indisponibilidade, substituição de plano, tenant, permissão, revisor forjado, evidência desconhecida, bytes alterados, plano antigo/ausente no worker e bloqueio de publicação.
- Sete testes existentes de publicação passaram junto aos dez novos: **17 passed**.
- Rodada de regressão de render, FFmpeg e áudio: **27 testes passaram**, incluindo os sete testes editoriais existentes no momento daquela coleta; os três novos restantes foram cobertos pela rodada final de 17.
- Total de cenários únicos cobertos entre as rodadas: **37**. Não é a suíte inteira do produto.
- Ruff passou nos seis arquivos Python novos/alterados. Os avisos Pydantic sobre o nome `copy` nos schemas antigos continuam existentes.
- Testes executados a partir de diretórios temporários novos. O `nexus-test.db` relativo criado pelo conftest ficou nesses diretórios, não no banco do workspace.

Não houve deploy nem teste visual de interface: as rotas estão disponíveis no código do backend, sem novo painel no Video Studio ou regeneração do cliente TypeScript nesta etapa. A concorrência foi protegida com lock do documento no caminho transacional; testes de concorrência em PostgreSQL continuam pendentes.

## Próximo incremento, ainda não implementado

1. Fluxo de casting local com amostras comparáveis e tela de revisão humana.
2. Admissão fiel de narração local e fontes sintéticas, com direitos e proveniência verificáveis, sem contornar os contratos existentes.
3. Composição do apresentador com a demonstração e motion funcional, validada no pipeline real.
4. Revisão final de vídeo/montagem vinculada ao render, permitindo remover o bloqueio de publicação apenas após validação específica.

O [diagnóstico criativo](../research/ugc-motion-caio-2026-09-04/report-source.md) continua sendo a referência para essas etapas. O projeto OneDrive e alterações anteriores foram preservados.

## Código

- [Contratos](../../../backend/app/domain/studios/editorial_review.py)
- [Serviço e eventos](../../../backend/app/services/studios/editorial_review.py)
- [Render](../../../backend/app/services/studios/video_render.py)
- [Publicação](../../../backend/app/services/studios/publication.py)
- [Rotas](../../../backend/app/routers/studios.py)
- [Testes](../../../backend/tests/test_editorial_review.py)
