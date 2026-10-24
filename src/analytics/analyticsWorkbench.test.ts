import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mergePointSlices, customPeriodPoints, previousCustomPeriodPoints, groupPoints } from './analyticsWorkbench';
import { aggregatePoints, type AnalyticsPoint, type NetworkAnalytics } from './analyticsModel';

const point = (day: string, reach: number | null, followers = 100): AnalyticsPoint => ({ date: `${day}T12:00:00`, followers, gained: null, lost: null, reach, impressions: null, engagements: null, likes: null, comments: null, shares: null, saves: null, clicks: null, views: null, posts: 0 });
const network = (points: AnalyticsPoint[]): NetworkAnalytics => ({ accountId: 'test-only', accountLabel: 'Test fixture', source: 'connected', connected: true, network: 'instagram', points, contents: [], formats: [] });

test('une redes por data, sem deslocar métricas quando faltam dias', () => {
  const rows = mergePointSlices([[point('2026-08-01', 10), point('2026-08-03', 30)], [point('2026-08-02', 20), point('2026-08-03', 40)]]);
  assert.deepEqual(rows.map(row => row.reach), [10, 20, 70]);
  assert.deepEqual(rows.map(row => row.date.slice(0,10)), ['2026-08-01','2026-08-02','2026-08-03']);
});
test('mantém indisponível diferente de zero e usa o último saldo de seguidores por conta', () => {
  const first = point('2026-08-01', null, 100);
  const second = { ...point('2026-08-01', null, 120), date: '2026-08-01T18:00:00' };
  const [row] = mergePointSlices([[first, second]]);
  assert.equal(row.followers, 120);
  assert.equal(row.reach, null);
  assert.equal(mergePointSlices([[point('2026-08-01',0)]])[0].reach, 0);
});
test('filtros incluem todo o último dia e comparam a janela imediatamente anterior', () => {
  const source = network([point('2026-08-01', 10),point('2026-08-02',20),point('2026-08-03',30),{ ...point('2026-08-04',40),date:'2026-08-04T23:59:59.999' }]);
  assert.equal(aggregatePoints(customPeriodPoints([source],'2026-08-03','2026-08-04')).reach, 70);
  assert.equal(aggregatePoints(previousCustomPeriodPoints([source],'2026-08-03','2026-08-04')).reach, 30);
  assert.deepEqual(customPeriodPoints([source],'2026-09-01','2026-09-05'), []);
});
test('agrupa semanas e meses do calendário sem somar saldos de seguidores', () => {
  const points = [point('2026-08-30',10,100),point('2026-08-31',20,110),point('2026-09-01',30,120)];
  assert.deepEqual(groupPoints(points,'monthly').map(row => row.reach),[30,30]);
  assert.deepEqual(groupPoints(points,'monthly').map(row => row.followers),[110,120]);
  assert.deepEqual(groupPoints(points,'weekly').map(row => row.reach),[10,50]);
});
