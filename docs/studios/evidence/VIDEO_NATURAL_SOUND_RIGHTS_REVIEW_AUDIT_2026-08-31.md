# Video Studio — revisão de direitos do som natural

Data: 31/08/2026. Repositório: `C:\Users\edugu\Downloads\res`.
Continua o checkpoint 33 e a vertical UGC sem voz e sem música do plano mestre.

## Resultado

A aba Sons agora permite que Owner ou Admin registre uma decisão de direitos sobre
o arquivo natural já importado. O registro não confia em um selo enviado pelo
cliente: o servidor relê os bytes privados, confirma o SHA-256, captura as
declarações de origem e licença do documento e grava uma evidência imutável no log
de domínio. Uma decisão verificada declara escopo `commercial-saas` e exige base,
referência de origem, referência de licença ou autorização e validade explícita.

O fluxo cobre `verified` e `restricted`. Restrição continua aplicada ao mesmo
asset e hash mesmo que alguém edite posteriormente o texto de origem. Verificação
só é projetada enquanto bytes e declarações capturadas permanecem idênticos e a
autorização não expirou. Criar, substituir ou restaurar um documento passa pela
mesma projeção server-owned, portanto `rightsStatus=verified` ou um review ID
inventado no JSON não libera o som.

## Integridade e autorização

`StudioAssetRightsReviewRecordV1` fixa:

- review, workspace, documento, revisão, asset e SHA-256;
- decisão, base e escopo de publicação;
- declarações de origem e licença capturadas do documento canônico;
- referências verificáveis, validade, notas, revisor e horário do servidor.

O endpoint exige autenticação, isolamento de tenant, Owner/Admin e
`Idempotency-Key`. O documento é bloqueado durante a operação; bytes divergentes,
revisão concorrente ou reutilização da chave com outro corpo falham fechado. A
decisão e a nova revisão do documento são gravadas na mesma transação. O documento
volta a rascunho e render, revisão e post ligados são invalidados, porque a prova
anterior não descreve mais a revisão corrente.

Editor recebe 403 honesto; usuário de outro workspace recebe 404. Replay idêntico
reutiliza o registro sem incrementar a revisão. O log existente evitou migration e
nova tabela. A serialização é forte por documento; uma futura consolidação de
direitos compartilhados entre documentos ainda deve ter restrição única no banco.

## UX

O painel apresenta estado verificado, restrito ou não verificado e explica que a
ação está limitada a Owner/Admin. A pessoa escolhe decisão e base, informa as duas
referências e confirma uma data de expiração ou ausência de expiração. A decisão
restrita fica disponível sem simular uma autorização inexistente. Salvar gera uma
nova chave idempotente apenas quando o rascunho muda.

Os controles têm Action Contracts próprios, alvos de 44 px e feedback para sucesso,
403 e conflito. O teste em 390 × 844 valida ausência de overflow e Axe A/AA no
formulário aberto. Evidência visual:
`artifacts/validation/video-natural-sound-rights-mobile.png`.

## Limite acústico preservado

O preflight opcional existente foi auditado e não foi promovido à API nem ao media
worker. Seu YAMNet ONNX de terceiro declara
`conversionProvenanceVerified=false` e `productionReady=false`, sem model card ou
paridade suficiente com o modelo oficial. O WebRTC VAD também classificou
transientes naturais como possível fala. Esses resultados continuam úteis como
challenger de pesquisa, mas não podem aprovar um anúncio.

Direitos verificados também não abrem publicação. Ainda faltam detectores
qualificados de fala e música sobre o MP4 final e uma admissão server-owned que
reúna direitos das fontes e escuta humana no mesmo hash do mix. O gate continua
retornando `studio_publication_natural_sound_evidence_pending`.

## Verificação

- **17/17** testes backend de direitos, render, revisão e publicação passaram.
- O backend recusou selo forjado pelo PUT genérico, Editor, outro tenant, validade
  passada e bytes alterados; comprovou replay, mudança/restauração de declaração e
  persistência da restrição.
- E2E autenticado com WAV e MP4 reais passou, cobrindo registro pela UI, persistência,
  telemetria sem referências sensíveis, reedição, render e isolamento.
- TypeScript, build de produção, Ruff, `git diff --check`, audit estrito e contratos
  foram executados no fechamento deste checkpoint.
- Audit estrito: **442 controles canônicos executáveis**, zero Action Contracts
  ausentes, URLs órfãs ou owners conflitantes; contratos 6/6.

As referências preenchidas no E2E são uma fixture técnica que diz explicitamente
que não autoriza produção. Elas provam o mecanismo, não a titularidade de uma
campanha. Os dez anúncios continuam em **0/10 aprovados para produção**.

## Compatibilidade e rollback

Foram adicionados contratos provider-neutral, serviço de revisão de direitos,
projeção no kernel, endpoint, OpenAPI tipado, cliente e painel. Não houve voz,
música, clonagem, modelo, provider, migration, VPS ou Figma. Documentos sem som
natural e outras superfícies mantêm o comportamento anterior.

Rollback pode retirar endpoint e painel e deixar os novos eventos como histórico
inerte; eles não devem ser apagados. Remover a projeção sem remover os campos do
cliente seria inseguro, pois reabriria a possibilidade de selo forjado.

## Próximo corte seguro

Qualificar detectores sobre um corpus Clicko autorizado e executar o preflight no
MP4 final, vinculando seus resultados ao mesmo SHA-256 da escuta humana. Depois,
uma admissão server-owned poderá reunir as três provas sem transformar heurística
ou declaração em autorização. Voz, Voicebox, música e clonagem permanecem adiados.
