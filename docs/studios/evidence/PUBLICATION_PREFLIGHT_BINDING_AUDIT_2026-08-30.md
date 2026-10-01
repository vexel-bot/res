# Pré-flight de publicação vinculado — implementação e evidência de 30/08/2026

## Resultado deste corte

O caminho autenticado `/publish/:contentId` não usa mais arte, copy, contagem ou data de
demonstração. Ele carrega a última revisão aprovada do post, valida o `CreativeDocument` corrente e
exibe a mídia fixada. A legenda e os metadados de publicação são selados no snapshot quando a revisão
é solicitada. Assim, arte aprovada e copy modificada não podem compor o mesmo handoff.

Este corte implementa preparação e agendamento **internos**. Não há chamada de rede social,
confirmação de postagem externa ou alteração de conector.

## Fronteira e contratos

- `studio.publication-handoff.v1`: título, plataforma, formato, legenda e hashtags canônicos do Post,
  com SHA-256, fixados dentro do snapshot imutável da revisão.
- `studio.publication-preflight.v1`: revisão/documento/versão/post, mídia, copy, status de agenda e
  checks explícitos (`passed`, `warning`, `failed`).
- `studio.internal-schedule-receipt.v1`: recibo auditável, data futura e
  `externalPublicationConfirmed: false`.
- A comparação criativa continua independente de bookkeeping. O handoff é comparado separadamente
  ao Post vinculado; um PUT de documento não pode forjar aprovação.
- Revisões antigas sem o handoff novo falham fechadas e precisam ser reenviadas para revisão.

## Ações reais

- Preview: PNG do snapshot para visual/carrossel; render vinculado e checksum para vídeo/presenter.
- Copiar: usa `navigator.clipboard.writeText` e só confirma depois do sucesso; falha do navegador é
  mostrada sem alegar cópia.
- Baixar/exportar: ZIP autenticado com os PNGs ou vídeo aprovados, `legenda.txt` e `manifesto.json`.
  Fontes e render são revalidados por checksum. Pacote em memória é limitado a 512 MiB.
- Agendar: exige data futura e binding ainda válido, persiste `Post.status=scheduled`,
  `scheduled_at` e evento `studio.publication.scheduled_internal`. Repetir o mesmo comando é
  idempotente e devolve o mesmo recibo.
- Editar o documento aprovado volta o Post a `draft`, limpa o horário e invalida o pré-flight.
- Editar a copy depois da aprovação bloqueia preview, pacote e agendamento até nova revisão.
- “Publicar agora” permanece desabilitado, com motivo e mensagem de handoff manual.

## Segurança, direitos e isolamento

- Todos os endpoints exigem autenticação e membership no workspace; outro tenant recebe 404.
- Asset `restricted` bloqueia a saída. Asset com direitos `unknown` permanece como warning explícito
  para conferência manual; isso não habilita publicação externa.
- Preview e pacote usam `private, no-store` e `nosniff`.
- Nenhum segredo, path de storage ou URL privada aparece no manifesto.
- O evento de agendamento contém revisão, versão, post, data e digest da publicação, mas declara
  explicitamente que não houve publicação externa.

## Provas executadas

- Backend focado final: `backend/tests/test_studio_publication_preflight.py`,
  `backend/tests/test_studio_review_binding.py` e `backend/tests/test_studio_kernel.py`: **20/20**.
  XML: `artifacts/validation/publication-preflight-regression-20260830.xml`.
- Casos cobertos: ZIP/PNGs/legenda/manifesto reais, acesso anônimo e cross-workspace, agendamento
  futuro, idempotência, evento persistido, data passada, copy alterada, documento obsoleto e
  cancelamento do horário após edição.
- E2E específico: `tests/e2e/publication-preflight.spec.ts`: revisão e dados reais, pixel do snapshot,
  clipboard, download concluído, agenda persistida/reload, erro fail-closed após alteração e ausência
  do conteúdo fictício. Inclui Axe sem violações no escopo da tela, navegação móvel sem overflow e
  sidebar completamente off-canvas depois da transição.
- E2E integral final: **29/29**, `node node_modules/@playwright/test/cli.js test --workers=1`,
  aproximadamente 2,9 minutos.
- Screenshots inspecionados: `artifacts/validation/publication-preflight-{1440,360}.png`.
- `npm run lint`, Ruff focado e `git diff --check`: aprovados.
- `npm run test:cx-contracts`: **6/6**.
- `npm run audit:cx-strict`: 45 rotas, 59 URLs, zero issues/órfãs/conflitos e 372/372 controles
  executáveis no escopo com Action ID.
- Build de produção aprovado; permanece o warning não bloqueante de chunk acima de 500 kB.

## Limitações honestas

- Sem conector externo não existe postagem automática nem confirmação de canal.
- Checks de direitos `unknown` precisam de decisão humana; este corte não inventa licença.
- SQLite prova o comportamento sequencial e a idempotência funcional, não a concorrência integral
  que precisa ser repetida sob PostgreSQL.
- A regra de 512 MiB evita crescimento de memória sem limite, mas pacotes grandes devem migrar para
  streaming/objeto assinado em um corte futuro.
- O redesign Figma não foi alterado nesta etapa; o comportamento implementado deve ser sincronizado
  somente via MCP Figma quando esse instrumento estiver disponível.

## Direção UGC vigente

Nenhuma voz foi acrescentada. O próximo lote UGC continua definido como vídeo com sons naturais e
legendas editoriais sincronizadas, sem clonagem, narração, voz stock, fala incidental ou lip-sync.
Direitos de imagem e de cada som continuam obrigatórios.
