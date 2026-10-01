# Review fiel ao snapshot — correção e evidência de 30/08/2026

## Falha reproduzida

O teste novo solicitou revisão, editou o título do documento e aprovou o snapshot anterior.
Antes da correção, a API respondeu 200/approved e promovia o documento atual. O teste anterior
`test_review_pins_immutable_document_version_and_updates_linked_post` aceitava esse comportamento:
preservar o JSON do snapshot não provava aprovação da versão correta.

A tela autenticada também mostrava arte de demonstração, seis slides fixos, comentários e nomes
fictícios e “Contraste aprovado” sem medição. A auditoria anterior era insuficiente nesse corte.

## Correções implementadas

- Decisão exige a revisão corrente e igualdade do conteúdo criativo fixado, incluindo versão,
  composição, brief, referências, assets e lineage. Mudanças de bookkeeping, como exportação,
  não contam como alteração criativa. Conflito retorna `studio_review_snapshot_stale` sem decidir.
- Edição não transporta aprovação para conteúdo modificado. Nova versão/restauração voltam a
  rascunho. Estado de aprovação vindo de PUT é ignorado em favor do estado controlado pelo servidor.
- Post vinculado aprovado/em revisão volta a rascunho quando o conteúdo é alterado por esses fluxos.
- Solicitar revisão novamente após edição gera um novo snapshot; repetição sem alteração continua
  idempotente. Documento e decisão usam row locks nos caminhos alterados; não é prova de concorrência
  integral sob PostgreSQL, pois a regressão executada usa SQLite.
- Preview PNG somente do snapshot, com autenticação e isolamento por workspace; `private, no-store`.
  Usa o mesmo compositor do export. Imagem referenciada exige fonte ativa e checksum fixado, validado
  contra os bytes. Sem placeholder quando a fonte não pode ser verificada.
- Vídeo no componente de Review usa o render vinculado, verifica checksum e aguarda decodificação.
  O teste de Review desta rodada prova PNG/carrossel; playback de vídeo nesse novo componente ainda
  precisa de um caso dedicado. O E2E de Video Studio existente prova upload/render/review, não isso.
- Tela autenticada usa quantidade/páginas reais, observação registrada e estado real. Preview,
  loading, falha, conflito e decisão em andamento não resultam em aprovação fictícia.
- Mobile passou de painel fixo sobreposto para sequência rolável. Editar e comentar continuam
  alcançáveis. Comparação sem duas versões carregadas fica desabilitada com razão e direção ao Studio.
- Aprovar segue para `/publish/:contentId`, como exige o contrato, sem publicar ou agendar.

## Prova executada

- Pytest: **17/17** em `backend/tests/test_studio_review_binding.py` e `test_studio_kernel.py`.
  XML: `artifacts/validation/review-binding-verified-20260830.xml`.
- Inclui snapshot obsoleto, recuperação por nova revisão, aprovação sem adulteração, PUT forjado,
  edição/versão/restauração, comentário obrigatório, export sem invalidar conteúdo, PNG fixado,
  duas páginas com pixels distintos, acesso anônimo/outro workspace e fonte adulterada.
- E2E integral: **28/28**, `node node_modules/@playwright/test/cli.js test --workers=1`, cerca de 2 min.
- E2E novo: página real, pixels/legenda por slide, 360/768/1024/1440, comentário alcançável no mobile,
  edição concorrente, conflito sem promoção, nova revisão e handoff correto ao preflight.
- Tentativa anterior com dois workers: 2/3 passaram; Review excedeu 7 s aguardando a mídia durante
  execução concorrente com vídeo. Não foi contabilizada como sucesso nem como benchmark de latência.
  O cenário isolado e a suíte integral com um worker passaram sem alterar o limite de espera.
- `npm run lint`, Ruff focado e `git diff --check`: aprovados.
- `npm run test:cx-contracts`: **6/6** após alinhar o comportamento ao handoff previsto no contrato.
- `npm run audit:cx-strict`: 362/362 controles executáveis no escopo; sem órfãs/conflitos.
- Build passou com warning preexistente de chunk acima de 500 kB. A alteração posterior de destino
  de navegação foi coberta por TypeScript/E2E; não foi tratada como novo build de produção.
- Screenshots: `artifacts/validation/review-snapshot-{360,768,1024,1440}.png`. Houve inspeção visual
  do mobile antes/depois. Não afirmar regressão visual pixel-perfect ou auditoria assistiva completa.

## Handoff seguinte corrigido

A pendência encontrada neste documento foi corrigida no corte subsequente. O owner real de
`/publish/:contentId` agora usa a revisão aprovada, legenda fixada, mídia verificável, clipboard,
pacote ZIP e agendamento interno persistido. Copy/documento alterados falham fechados e a publicação
externa continua bloqueada. Evidência, limitações e testes estão em
`PUBLICATION_PREFLIGHT_BINDING_AUDIT_2026-08-30.md`.

## Direção mais recente do usuário

Próximo UGC: **sem voz**, com sons naturais e legendas. Nenhuma clonagem, narração, voz stock ou
lip-sync nesta entrega. O perfil está no plano UGC e no plano mestre; os lotes históricos permanecem
congelados. Isso não dispensa direitos de imagem, fonte dos sons, revisão ou validação com usuários.

Sem mudanças na VPS, sem publicação, sem modelo biométrico ativado, sem commit. Worktree anterior
preservado. A meta permanece ativa; este checkpoint não declara CX-0 ou o produto inteiro concluídos.
