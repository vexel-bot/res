import test from 'node:test';
import assert from 'node:assert/strict';
import type { Post } from '../types';
import { dashboardGreeting, dashboardReachChart, dashboardUpcoming, dashboardWeek } from './dashboardOperationalModel';

const post = (id: string, scheduledAt: string, extra: Partial<Post> = {}) => ({ id, workspaceId: 'workspace-a', scheduledAt, status: 'scheduled', ...extra } as Post);

test('Dashboard greeting follows the user local access time boundaries', () => {
  assert.equal(dashboardGreeting(new Date(2026, 9, 3, 4, 59)), 'Boa noite');
  assert.equal(dashboardGreeting(new Date(2026, 9, 3, 5, 0)), 'Bom dia');
  assert.equal(dashboardGreeting(new Date(2026, 9, 3, 11, 59)), 'Bom dia');
  assert.equal(dashboardGreeting(new Date(2026, 9, 3, 12, 0)), 'Boa tarde');
  assert.equal(dashboardGreeting(new Date(2026, 9, 3, 17, 59)), 'Boa tarde');
  assert.equal(dashboardGreeting(new Date(2026, 9, 3, 18, 0)), 'Boa noite');
});

test('Dashboard week starts on Monday, covers Sunday and respects local date boundaries', () => {
  const now = new Date(2026, 8, 27, 12); // Sunday
  const days = dashboardWeek([
    post('monday', new Date(2026, 8, 21, 0).toISOString()),
    post('sunday', new Date(2026, 8, 27, 23, 59).toISOString()),
    post('next-week', new Date(2026, 8, 28, 0).toISOString()),
  ], 'workspace-a', now);
  assert.equal(days.length, 7);
  assert.equal(days[0].date.getDay(), 1);
  assert.equal(days[6].date.getDay(), 0);
  assert.deepEqual(days.flatMap(day => day.posts.map(item => item.id)), ['monday', 'sunday']);
  assert.equal(days.filter(day => day.today).length, 1);
  assert.equal(days[6].today, true);
});

test('Dashboard previews isolate workspaces, reject invalid dates and retain all events for day counts', () => {
  const now = new Date(2026, 8, 28, 9);
  const posts = [post('later', new Date(2026, 8, 28, 18).toISOString()), post('earlier', new Date(2026, 8, 28, 10).toISOString(), { status: 'approved' }),
    post('third', new Date(2026, 8, 28, 20).toISOString()), post('fourth', new Date(2026, 8, 28, 21).toISOString()),
    post('foreign', now.toISOString(), { workspaceId: 'workspace-b' }), post('draft', now.toISOString(), { status: 'draft' }), post('invalid', 'not-a-date')];
  const before = [...posts];
  assert.deepEqual(dashboardWeek(posts, 'workspace-a', now)[0].posts.map(item => item.id), ['earlier', 'later', 'third', 'fourth']);
  assert.deepEqual(dashboardUpcoming(posts, 'workspace-a', now).map(item => item.id), ['earlier', 'later', 'third']);
  assert.deepEqual(posts, before);
});

test('Dashboard week and next-content handle year rollover and genuinely empty schedules', () => {
  const now = new Date(2027, 0, 1, 12);
  const days = dashboardWeek([post('past', new Date(2026, 11, 31, 10).toISOString())], 'workspace-a', now);
  assert.equal(days[0].key, '2026-12-28');
  assert.equal(days[6].key, '2027-01-03');
  assert.deepEqual(dashboardUpcoming([post('past', new Date(2026, 11, 31, 10).toISOString())], 'workspace-a', now), []);
  assert.ok(dashboardWeek([], 'workspace-a', now).every(day => day.posts.length === 0));
});

test('Dashboard chart preserves missing days and real zero values without connecting gaps', () => {
  const chart = dashboardReachChart([{ date: '2026-09-26', reach: 0 }, { date: '2026-09-27', reach: null }, { date: '2026-09-28', reach: 20 }]);
  assert.equal(chart.length, 3);
  assert.equal(chart[0]?.value, 0);
  assert.equal(chart[1], null);
  assert.equal(chart[2]?.x, 772);
  assert.equal(chart[2]?.value, 20);
  assert.ok(chart.filter(point => point !== null).every(point => Number.isFinite(point.x) && Number.isFinite(point.y)));
});

test('Dashboard chart does not invent an evolution when reach is unavailable or has a single sample', () => {
  assert.deepEqual(dashboardReachChart([{ date: '2026-09-27', reach: null }, { date: '2026-09-28', reach: 20 }]), []);
  assert.deepEqual(dashboardReachChart([{ date: '2026-09-27', reach: NaN }, { date: '2026-09-28', reach: Infinity }]), []);
  assert.equal(dashboardReachChart([{ date: '2026-09-27', reach: 0 }, { date: '2026-09-28', reach: 0 }])[0]?.y, 142);
});

test('Dashboard chart bounds its preview to the latest fourteen real records', () => {
  const points = Array.from({ length: 20 }, (_, index) => ({ date: String(index), reach: index }));
  const chart = dashboardReachChart(points);
  assert.equal(chart.length, 14);
  assert.equal(chart[0]?.date, '6');
  assert.equal(chart[13]?.date, '19');
  assert.equal(points.length, 20);
});
