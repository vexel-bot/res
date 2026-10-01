# Video Studio — análise acústica e admissão do mix final

Data: 31/08/2026. Repositório: `C:\Users\edugu\Downloads\res`.
Continua o checkpoint 34 e a vertical UGC com som natural e legenda editorial.

## Resultado

O Studio possui agora uma fronteira provider-neutral para analisar ausência de
fala e música no MP4 exato fixado pela revisão. A análise é um job observável
`acoustic_analysis` no worker `media_cpu`; recebe review, documento, versão, hash
do snapshot, asset do render, SHA-256 e política `no-speech-no-music-v1`.

O provider devolve somente resultados tipados de fala e música. Ele não decide
publicação. O control plane acrescenta IDs de provider/modelo aprovados, digest do
modelo, digest do benchmark e horário do servidor, e grava o registro imutável no
log de domínio. Resultado ou bytes com binding divergente falham fechados.

## Promoção obrigatória

Um job só pode nascer e executar quando todos estes itens coincidem:

- registration `acoustic_analysis` aprovada;
- `benchmarkStatus=passed` e digest SHA-256 do benchmark;
- worker anunciado para a versão exata do provider;
- model registration aprovada, com uso comercial aprovado;
- capacidade `acoustic_analysis`, mesmo digest de benchmark e digest do modelo;
- adapter presente no registry de runtime com nome e versão idênticos.

O registry de produção continua vazio. O YAMNet ONNX/WebRTC VAD de pesquisa não foi
registrado: sua conversão não tem proveniência/paridade de produção e transientes
naturais acionaram o VAD. O teste usa um provider fake injetado somente no processo
de teste; não existe modelo acústico real promovido, download ou ativação na VPS.

## Admissão server-owned

A análise `pass` sozinha não libera entrega. `studio.natural-sound-admission.v1`
só é criada quando o mesmo review, snapshot e SHA-256 reúnem:

- detector qualificado com fala e música em `pass`;
- escuta humana integral em `pass`;
- cada fonte natural com evento real de direitos, declarações iguais, hash igual e
  autorização ainda válida.

A admissão fixa análise, escuta e IDs dos direitos. No preflight, pacote e
agendamento, o servidor relê o MP4 e revalida evidências revogáveis sem repetir
inferência. Modelo/provider revogado bloqueia com
`studio_publication_acoustic_promotion_revoked`; licença expirada ou alterada
bloqueia com `studio_publication_natural_sound_rights_changed`. Ausência ou binding
incompleto mantém `studio_publication_natural_sound_evidence_pending`.

## CX e estados honestos

A Review Room ganhou “Análise automática do MP4”. No estado atual ela informa que
nenhum detector foi aprovado e deixa “Analisar fala e música” desabilitado com a
razão. Quando houver runtime promovido, o mesmo controle cria o job, acompanha
queued/running/retrying e recarrega a revisão após sucesso. Estados pass, fail,
inconclusive e admitted explicam o efeito sem confundir análise com escuta ou
direitos.

O controle tem Action Contract, telemetria e alvo de 44 px. Em 390 × 844, o painel
é uma coluna, não cria overflow e passou Axe A/AA na superfície completa. Evidência:
`artifacts/validation/video-review-acoustic-unavailable-mobile.png`.

## Verificação

- O teste de fronteira recusou ausência de promoção e outro tenant, comprovou
  idempotência, fila `media_cpu`, execução promovida, hashes, análise e admissão.
- Alterar bytes do MP4 depois da análise bloqueou entrega.
- Revogar o modelo depois da admissão bloqueou entrega sem apagar o histórico.
- Regressão focada de análise, direitos, render, revisão e publicação passou
  **18/18**.
- A jornada autenticada com WAV e MP4 reais passou em **47,3 s** após validar o estado
  indisponível, escuta, direitos, preview, dois renders e isolamento.
- TypeScript, build, Ruff e `git diff --check` passaram. O build mantém o aviso
  conhecido de chunk JavaScript acima de 500 kB.
- Audit estrito: **443 controles canônicos executáveis**, zero controles sem Action
  Contract, zero URLs órfãs ou owners conflitantes; contratos 6/6.

As fixtures demonstram mecanismos, não qualificam um detector nem autorizam uma
campanha. Os dez anúncios continuam em **0/10 aprovados para produção**.

## Compatibilidade, limites e rollback

Foram adicionados contratos, port/registry separado, execution profile, serviço,
dois endpoints, projeção no review, gate de publicação, OpenAPI tipado e painel.
Não houve migration, tabela, voz, música, clonagem, biometria, provider real, VPS ou
Figma. Visual, carrossel e documentos sem perfil natural mantêm o comportamento.

O digest de benchmark é exigido no control plane, mas a cadeia de promoção ainda
precisa de um bundle assinado e verificador de bytes antes de aceitar um detector
real. O job não mede sincronismo perceptual entre foley e ação; isso permanece na
escuta humana e no futuro QC temporal. Rollback remove endpoint/painel/executor e
mantém eventos históricos inertes; não se deve converter registros antigos em
aprovação genérica.

## Próximo corte seguro

Definir corpus Clicko autorizado com fala PT-BR, música, silêncio e foley difícil;
fixar política de falso negativo/positivo; produzir bundle assinado e comparar
candidatos cuja licença e pesos permitam SaaS comercial. Só após promoção real o
botão poderá executar fora de testes. Voz, Voicebox, música e clonagem permanecem
adiados.

## Supersessão

O checkpoint 36 substituiu as flags soltas por recibo assinado e verificador de
bytes. Ver `VIDEO_ACOUSTIC_DETECTOR_QUALIFICATION_CHAIN_AUDIT_2026-08-31.md`.
