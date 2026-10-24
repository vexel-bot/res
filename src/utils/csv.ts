/** Keeps untrusted text from being evaluated as a spreadsheet formula. */
export function csvCell(value: unknown): string {
  const text = String(value ?? '');
  const safe = typeof value !== 'number' && /^\s*[=+@\-\t\r\n]/.test(text) ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
}
