import type { AnalyticsPoint } from '../analytics/analyticsModel';
import { metricValue } from '../analytics/analyticsWorkbench';
import type { KlicRecord } from './contracts';

/** Uses the same metric semantics as Analytics and never fills gaps with zeros. */
export function analyticsContext(workspaceId: string, current: AnalyticsPoint[], previous: AnalyticsPoint[], start: string, end: string): KlicRecord[] {
  return (['reach', 'impressions', 'engagements', 'clicks'] as const).flatMap(metric => {
    const currentDays = current.filter(p => typeof p[metric] === 'number' && Number.isFinite(p[metric])).length;
    const previousDays = previous.filter(p => typeof p[metric] === 'number' && Number.isFinite(p[metric])).length;
    const value = metricValue(current, metric), prior = metricValue(previous, metric);
    if (value === null || prior === null || currentDays !== current.length || previousDays !== previous.length || currentDays !== previousDays || currentDays < 2) return [];
    return [{ workspaceId, clientId: null, metric, current: value, previous: prior, currentDays, previousDays, start, end, previousStart: previous[0]?.date, previousEnd: previous.at(-1)?.date, dataStatus: 'available' }];
  });
}
