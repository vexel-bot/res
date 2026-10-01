# UGC sem voz — contrato, corpus e auditoria

Data: 30/08/2026. Escopo: dez planos locais; sem geração ou publicação de mídia.

## Resultado

- 10/10 casos passaram nas checagens mecânicas do plano.
- 0/10 casos estão prontos para produção.
- Nenhuma voz, fala incidental, música, TTS, clonagem ou lip-sync foi executada.
- Nenhum take/avatar, arquivo de som natural ou licença foi simulado.
- Nenhuma publicação externa foi executada.

O corpus vigente é
`benchmarks/studios/ugc/ugc-no-voice-natural-caption-casebook.v1.json`, suite
`clicko.ugc-no-voice-natural-caption.pt-br.v1`.

- digest canônico do conteúdo:
  `624a1cffa264175170746a42defcad356fc601c36b9f25e3599d0ec10a908008`;
- SHA-256 do arquivo:
  `754217d06b0dedc053f7d72a6ff5ab6ac81179a4aa783673f564ae911a1df785`;
- SHA-256 de `audit.json`:
  `8a6c81eb20aa7063327634771224e933e2a8652ea87c125e1dcedb5e45fd9605`;
- SHA-256 de `review.md`:
  `ac03f4aba71b4a0511c3de2c709083dbeb0331c8293c29ed58b766adc02aae16`.

Os artefatos canônicos estão em `artifacts/validation/ugc-no-voice/audit-20260830-v3/` e incluem cópias
do corpus, contrato e evaluator usados na avaliação. A auditoria pode ser repetida com:

```powershell
$env:PYTHONPATH='backend'
python backend/scripts/audit_ugc_no_voice_plan.py --output-dir <diretorio-novo>
```

## O que o contrato garante

- áudio `natural-foley-only`;
- voz, conversa captada e música `prohibited`;
- legenda editorial queimada, uma ou duas linhas, até 42 caracteres por linha;
- timeline sem sobreposição, com hook, demonstração e CTA;
- fatos permitidos e alegações proibidas por caso;
- arquivo, SHA-256, origem/licença, detector rastreável e escuta humana por cue sonoro;
- MP4 real 1080×1920/H.264 com stream de áudio, legenda queimada, direitos do take e relatório do mix;
- revisão humana de copy, legenda, sincronismo e segurança vinculada ao digest exato do caso;
- publicação externa bloqueada pelo próprio perfil.

## Limite da prova

O passe do plano mede estrutura, legibilidade inicial, timeline, segurança lexical e fronteiras de
direitos. Não mede persuasão, física do vídeo, qualidade do avatar, correspondência real entre ação
e som ou ausência de fala no mix final. Esses itens dependem dos arquivos de produção e de revisão
humana. Um JSON dizendo `pass` não abre o gate: os bytes e relatórios correspondentes precisam estar
dentro da raiz permitida e ter checksum válido.

## Próxima execução

1. Escolher os primeiros casos de baixo risco e obter take/avatar com direitos verificáveis.
2. Gravar ou licenciar cada foley/ambiência e registrar fonte, licença, checksum e relatório.
3. Renderizar legenda sobre vídeo UGC real; não usar cards estáticos como substituto.
4. Verificar H.264, 1080×1920, duração/FPS, stream de áudio e decodificação.
5. Executar detector de fala/música e escuta humana no mix final.
6. Revisar copy, leitura, sincronismo, continuidade física e segurança sobre o digest exato.
7. Levar a versão aprovada ao fluxo autenticado de Review; este benchmark continua sem publicar.

Voicebox permanece fora deste corte. O corpus falado v1 e seus resultados históricos não foram
alterados ou reclassificados.

## Regressão

- `backend/tests/test_ugc_no_voice.py` + `backend/tests/test_ugc_ad_acceptance.py`: 16/16 aprovados;
- relatório JUnit: `artifacts/validation/ugc-no-voice-regression-final-20260830.xml`;
- Ruff dos quatro arquivos novos: aprovado;
- `git diff --check` do corte: aprovado antes da evidência final, sem erro de whitespace;
- dois warnings preexistentes do Pydantic sobre o campo `copy` permanecem fora deste corte.
