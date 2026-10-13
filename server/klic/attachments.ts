import { randomUUID } from 'node:crypto';
import { Readable } from 'node:stream';
import { PDFParse } from 'pdf-parse';
import ExcelJS from 'exceljs';
import mammoth from 'mammoth';
import { unzipSync } from 'fflate';
import { ATTACHMENT_LIMITS, validateFile, type ChatFile } from '../../src/klic/conversation';

const MAX_EXTRACTED = 500000;
function utf8(buffer: Buffer) {
  const value = new TextDecoder('utf-8', { fatal: true }).decode(buffer);
  if (value.includes('\0')) throw new Error('Arquivo de texto inválido.');
  return value;
}
function checkZip(buffer: Buffer) {
  let total = 0; let entries = 0;
  unzipSync(buffer, { filter: entry => {
    total += entry.originalSize; entries++;
    if (total > 24 * 1024 * 1024 || entries > 2000) throw new Error('Documento descompactado excede o limite seguro.');
    return false;
  } });
}
export async function prepareFiles(input: unknown): Promise<ChatFile[]> {
  if (!Array.isArray(input) || input.length > ATTACHMENT_LIMITS.count) throw new Error('Envie no máximo 4 anexos.');
  let total = 0;
  const result: ChatFile[] = [];
  for (const raw of input) {
    if (!raw || typeof raw.name !== 'string' || raw.name.length > 200 || typeof raw.dataUrl !== 'string') throw new Error('Anexo inválido.');
    const { extension, mime } = validateFile(raw);
    const match = raw.dataUrl.match(/^data:([^;,]+);base64,([A-Za-z0-9+/]+={0,2})$/);
    if (!match || match[2].length > 8 * 1024 * 1024) throw new Error('Conteúdo do anexo inválido.');
    const bytes = Buffer.from(match[2], 'base64'); total += bytes.length;
    if (bytes.length !== raw.size || total > ATTACHMENT_LIMITS.bytes || bytes.toString('base64') !== match[2]) throw new Error('Os anexos devem somar no máximo 6 MB.');
    validateFile({ ...raw, type: match[1] });
    const header = bytes.subarray(0, 16);
    const matches = extension === 'png' ? header.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))
      : ['jpg','jpeg'].includes(extension) ? header[0] === 255 && header[1] === 216 && bytes.at(-2) === 255 && bytes.at(-1) === 217
      : extension === 'webp' ? header.toString('ascii',0,4) === 'RIFF' && header.toString('ascii',8,12) === 'WEBP'
      : extension === 'pdf' ? header.toString('ascii',0,5) === '%PDF-'
      : ['xlsx','docx'].includes(extension) ? header.toString('ascii',0,2) === 'PK'
      : extension === 'wav' ? header.toString('ascii',0,4) === 'RIFF' && header.toString('ascii',8,12) === 'WAVE'
      : extension === 'mp3' ? header.toString('ascii',0,3) === 'ID3' || (header[0] === 255 && (header[1] & 224) === 224)
      : extension === 'ogg' ? header.toString('ascii',0,4) === 'OggS'
      : extension === 'webm' ? header.subarray(0,4).equals(Buffer.from([26,69,223,163])) : true;
    if (!matches) throw new Error('O arquivo está corrompido ou não corresponde ao formato informado.');
    let text: string | undefined;
    if (['xlsx','docx'].includes(extension)) checkZip(bytes);
    if (extension === 'txt') text = utf8(bytes);
    if (extension === 'docx') text = (await mammoth.extractRawText({ buffer: bytes })).value;
    if (extension === 'pdf') {
      const parser = new PDFParse({ data: new Uint8Array(bytes) });
      try {
        const info = await parser.getInfo();
        if (info.total > 80) throw new Error('Divida o PDF em documentos de até 80 páginas.');
        const parsed = await parser.getText();
        text = parsed.pages.map(page => page.text).join('\n\n');
        if (!text.trim()) throw new Error('O PDF não contém texto legível. Envie uma versão com OCR.');
      } finally { await parser.destroy(); }
    }
    if (extension === 'xlsx' || extension === 'csv') {
      const book = new ExcelJS.Workbook();
      if (extension === 'xlsx') await book.xlsx.load(bytes as any);
      else {
        const value = utf8(bytes); const first = value.split(/\r?\n/)[0];
        const delimiter = [';', ',', '\t'].sort((a,b) => first.split(b).length - first.split(a).length)[0];
        await book.csv.read(Readable.from([value]), { parserOptions: { delimiter } });
      }
      if (book.worksheets.length > 20) throw new Error('Envie planilhas com no máximo 20 abas.');
      let cells = 0;
      const sheets: string[] = [];
      book.eachSheet(sheet => {
        if (sheet.rowCount > 20000 || sheet.columnCount > 200) throw new Error('Divida a planilha em partes de até 20 mil linhas e 200 colunas.');
        const lines: string[] = []; const stats = new Map<number, { count: number; sum: number; min: number; max: number }>();
        sheet.eachRow((row, index) => {
          const values: string[] = [];
          row.eachCell({ includeEmpty: true }, (cell, column) => {
            if (++cells > 120000) throw new Error('A planilha excede o limite de 120 mil células.');
            values.push(cell.text.slice(0, 2000));
            const number = typeof cell.value === 'number' ? cell.value : cell.type === ExcelJS.ValueType.Formula && typeof cell.result === 'number' ? cell.result : null;
            if (number !== null && Number.isFinite(number)) {
              const s = stats.get(column) || { count: 0, sum: 0, min: Infinity, max: -Infinity };
              s.count++; s.sum += number; s.min = Math.min(s.min,number); s.max = Math.max(s.max,number); stats.set(column,s);
            }
          });
          lines.push(`Linha ${index}: ${JSON.stringify(values)}`);
        });
        sheets.push(`Aba ${sheet.name}; ${sheet.rowCount} linhas; ${sheet.columnCount} colunas.\nEstatísticas numéricas (células com valor numérico, incluindo resultados de fórmulas já salvos; fórmulas não são recalculadas): ${JSON.stringify([...stats])}\n${lines.join('\n')}`);
      });
      text = sheets.join('\n\n');
    }
    if (text !== undefined && (!text.trim() || text.length > MAX_EXTRACTED)) throw new Error('Documento vazio ou muito extenso. Divida-o em partes menores.');
    result.push({ id: randomUUID(), name: raw.name, type: mime, size: bytes.length, ...(text !== undefined ? { text } : {}), dataUrl: `data:${mime};base64,${bytes.toString('base64')}` });
  }
  return result;
}

export function selectExcerpts(text: string, query: string, budget = 16000) {
  if (text.length <= budget) return text;
  const terms: string[] = query.toLocaleLowerCase('pt-BR').match(/[\p{L}\p{N}]{3,}/gu) || [];
  const chunks: Array<{ text: string; index: number; score: number }> = [];
  for (let i = 0; i < text.length; i += 1600) {
    const part = text.slice(i, i + 1800);
    chunks.push({ text: part, index: i, score: terms.reduce((score, term) => score + Number(part.toLocaleLowerCase('pt-BR').includes(term)), 0) });
  }
  const chosen = [chunks[0], ...chunks.slice(1).sort((a,b) => b.score-a.score || b.index-a.index).slice(0, Math.floor(budget/1800)-1)].sort((a,b) => a.index-b.index);
  return '[Trechos selecionados; não representam todo o documento.]\n' + chosen.map(c => `[posição ${c.index}] ${c.text}`).join('\n');
}
