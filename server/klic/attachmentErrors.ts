// Only application-authored validation messages may cross the parser/provider boundary.
const publicMessages = new Set([
  'Formato de arquivo não suportado.',
  'Envie arquivos não vazios de até 6 MB.',
  'O tipo do arquivo não corresponde ao formato informado.',
  'Arquivo de texto inválido.',
  'Documento descompactado excede o limite seguro.',
  'Envie no máximo 4 anexos.',
  'Anexo inválido.',
  'Conteúdo do anexo inválido.',
  'Os anexos devem somar no máximo 6 MB.',
  'O arquivo está corrompido ou não corresponde ao formato informado.',
  'Divida o PDF em documentos de até 80 páginas.',
  'O PDF não contém texto legível. Envie uma versão com OCR.',
  'Envie planilhas com no máximo 20 abas.',
  'Divida a planilha em partes de até 20 mil linhas e 200 colunas.',
  'A planilha excede o limite de 120 mil células.',
  'Documento vazio ou muito extenso. Divida-o em partes menores.',
  'Aguarde um momento para processar os anexos.',
  'O arquivo demorou demais para ser processado. Divida-o em partes menores.',
  'Não foi possível processar o arquivo com segurança.',
  'O arquivo excedeu os recursos disponíveis para processamento.',
  'Os anexos desta conversa excedem 24 MB. Inicie uma nova conversa.',
  'Não foi possível transcrever o áudio.',
]);

export function publicAttachmentError(error: unknown): string | undefined {
  return error instanceof Error && publicMessages.has(error.message) ? error.message : undefined;
}
