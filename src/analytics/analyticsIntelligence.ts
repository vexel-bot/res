import type { AnalyticsContent } from './analyticsModel';

export interface ContentAnomaly {
  content: AnalyticsContent;
  direction: 'positive' | 'negative';
  deviation: number;
  benchmark: number;
  explanation: string;
}

const valid = (value: number | null | undefined): value is number => typeof value === 'number' && Number.isFinite(value);
const average = (values: Array<number | null | undefined>) => {
  const rows = values.filter(valid);
  return rows.length ? rows.reduce((total, value) => total + value, 0) / rows.length : null;
};

export function detectContentAnomalies(contents: AnalyticsContent[]): ContentAnomaly[] {
  const withReach = contents.filter((content): content is AnalyticsContent & { reach: number } => valid(content.reach));
  if (withReach.length < 4) return [];
  const benchmark = average(withReach.map((content) => content.reach));
  if (!benchmark) return [];
  const variance = average(withReach.map((content) => (content.reach - benchmark) ** 2)) || 0;
  const deviation = Math.sqrt(variance);
  if (!deviation) return [];
  return withReach
    .map((content) => ({ content, z: (content.reach - benchmark) / deviation }))
    .filter(({ z }) => Math.abs(z) >= 1.25)
    .sort((a, b) => Math.abs(b.z) - Math.abs(a.z))
    .map(({ content, z }) => ({
      content,
      direction: z > 0 ? 'positive' : 'negative',
      deviation: z,
      benchmark,
      explanation: `Alcance ${Math.abs(z).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} desvios-padrão ${z > 0 ? 'acima' : 'abaixo'} da média de ${Math.round(benchmark).toLocaleString('pt-BR')}.`,
    }));
}
