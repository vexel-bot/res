# Integridade dos bytes das licenças fornecidas

A regressão editorial retornou `editorial_font_pack_checksum_conflict`. Cinco TTFs conferem com o manifesto; Inter, Fraunces e Permanent Marker têm licenças esperadas em LF, mas checkout em CRLF. Archivo Narrow e IBM Plex Mono já têm CRLF e conferem; seus blobs Git foram normalizados em LF. O pacote fornecido pelo usuário fixa os bytes originais, com endings mistos.

Correção prevista: `.gitattributes` para desativar conversão de texto apenas nas licenças em `backend/app/resources/editorial_fonts/*.txt`; restaurar cada licença ao ending cujo SHA-256 é exatamente o registrado. Não alterar texto/conteúdo, TTFs, manifesto, versões, algoritmo de checksum ou gate de importação. Verificador aceita somente o arquivo atual, conversão CRLF→LF ou LF→CRLF cuja hash corresponda ao manifesto, e rejeita qualquer outra divergência. Paths ficam restritos ao diretório do pack.

Leitores: Git checkout, import_pack, store_resource e recibos de licença. Compatibilidade: mesmo pack v1, mesmos checksums e bytes fornecidos; leitura continua estrita. Teste existente API/import/deduplicação/recibo deve passar novamente e confirmar o texto armazenado pela hash original. A falha inicial permanece no XML, sem ser apagada da história.

## Verificação de whitespace

A regra das licenças também declara `cr-at-eol`, mantendo as verificações usuais de espaços/tabulações. Assim o diff reconhece CRLF como final de linha nos originais que o exigem, sem modificar bytes vinculados ao manifesto nem desabilitar whitespace no resto do projeto.

`git diff --check` ainda aponta um espaço final original na linha 21 de Archivo Narrow e IBM Plex Mono. Esse byte foi preservado porque pertence ao conteúdo vinculado pelo checksum; não foi removido nem ocultado por uma exceção geral de lint. O diff dos arquivos de código desta capacidade passou separadamente.
