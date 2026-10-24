import type { KlicSource, KlicRecommendation } from '../../src/klic/contracts';

/** Facts and correlations only. Missing values never become zero or causal explanations. */
export function recommend(sources: KlicSource[], now = Date.now()): KlicRecommendation[] {
  const result: KlicRecommendation[] = [];
  const calendar = sources.find(s => s.domain === 'calendar' && s.status === 'available');
  const approvals = sources.find(s => s.domain === 'approvals' && s.status === 'available');
  const analytics = sources.find(s => s.domain === 'analytics' && s.status === 'available');
  if (approvals) {
    const pending = approvals.records.filter(r => ['pending_approval', 'in_review'].includes(String(r.stage)));
    if (pending.length) result.push({ id: 'pending-approvals', kind: 'observation', text: pending.length + ' conteúdo(s) aguardam aprovação. Revise a fila antes do próximo agendamento.', evidence: ['approvals:service'], destination: 'approvals' });
  }
  if (calendar) {
    const late = calendar.records.filter(r => typeof r.scheduledAt === 'string' && Date.parse(r.scheduledAt) < now && !['published', 'rejected'].includes(String(r.status)));
    if (late.length) result.push({ id: 'overdue-calendar', kind: 'recommendation', text: late.length + ' item(ns) do calendário têm data passada e não constam como publicados. Confira o estado da publicação.', evidence: ['calendar:' + calendar.provenance], destination: 'calendar' });
  }
  for (const row of analytics?.records || []) {
    if (!['reach', 'impressions', 'engagements', 'clicks'].includes(String(row.metric))) continue;
    if (typeof row.current !== 'number' || typeof row.previous !== 'number' || row.previous <= 0 || row.current < 0 || row.currentDays !== row.previousDays || Number(row.currentDays) < 2) continue;
    const change = (row.current - row.previous) / row.previous * 100;
    const label = ({ reach: 'Alcance', impressions: 'Impressões', engagements: 'Engajamentos', clicks: 'Cliques' } as Record<string, string>)[String(row.metric)];
    const evidence = ['analytics:' + analytics!.provenance];
    let text = label + (Math.abs(change) < .05 ? ' está estável' : (change > 0 ? ' cresceu ' : ' caiu ') + Math.abs(change).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%') + ' entre os períodos informados.';
    const count = (start: unknown, end: unknown) => calendar?.records.filter(r => r.status === 'published' && typeof r.scheduledAt === 'string' && r.scheduledAt.slice(0, 10) >= String(start) && r.scheduledAt.slice(0, 10) <= String(end)).length;
    if (calendar && row.start && row.end && row.previousStart && row.previousEnd) {
      const currentCount = count(row.start, row.end)!;
      const previousCount = count(row.previousStart, row.previousEnd)!;
      if (previousCount > 0 && currentCount < previousCount && change < 0) {
        text += ' O calendário também registra menos publicações (' + currentCount + ' contra ' + previousCount + '). É uma associação a investigar, não uma causa comprovada.';
        evidence.push('calendar:' + calendar.provenance);
      }
    }
    if (analytics!.provenance !== 'service') text += ' Base: dados disponíveis neste navegador.';
    result.push({ id: 'metric-' + row.metric, kind: 'observation', text, evidence, destination: 'analytics' });
  }
  const radar = sources.find(s => s.domain === 'radar' && s.status === 'available');
  const opportunity = radar?.records.find(r => Number(r.brandRelevance) >= 50 && r.confidence !== 'low' && Array.isArray(r.evidence) && r.evidence.length);
  if (opportunity) result.push({ id: 'trend-' + opportunity.id, kind: 'recommendation', text: 'O Radar encontrou “' + opportunity.title + '” com aderência ao contexto da marca. Revise as fontes antes de incorporar ao planejamento.', evidence: ['radar:service', 'brand:browser-local'], destination: 'ai-chat' });
  return result.slice(0, 4);
}
