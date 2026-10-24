import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { RadarHistoryStore } from './history';
import { collectPinterestKeywords } from './pinterest';
import { getRadarSnapshot } from '../radar';
import type { RadarTrend } from '../radar';

const exampleTrend = (id: string) => ({ id, title: id, updatedAt: new Date().toISOString() }) as RadarTrend;

test('Radar history persists saved trends alongside score samples and isolates scopes', async () => {
  const directory = mkdtempSync(path.join(tmpdir(), 'clicko-radar-test-'));
  try {
    const filename = path.join(directory, 'history.json');
    const first = new RadarHistoryStore(filename);
    await first.setSaved('workspace-a:user-a:client-a', [exampleTrend('one')]);
    await first.append([{ scope: 'workspace-a:user-a:client-a', region: 'BR', trendId: 'one', score: 54, observedAt: new Date().toISOString(), observedValue: 120, metricKind: 'traffic' }]);
    const reloaded = new RadarHistoryStore(filename);
    assert.deepEqual((await reloaded.saved('workspace-a:user-a:client-a')).map(item => item.id), ['one']);
    assert.deepEqual(await reloaded.saved('workspace-b:user-a:client-a'), []);
    assert.equal((await reloaded.list('workspace-a:user-a:client-a', 'BR')).length, 1);
    assert.deepEqual(await reloaded.list('workspace-a:user-b:client-a', 'BR'), []);
    assert.deepEqual(await reloaded.list('workspace-a:user-a:client-a', 'GLOBAL'), []);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('Pinterest normalizes only valid official results and caches per authorization', async () => {
  const original = process.env.RADAR_PINTEREST_ACCESS_TOKEN;
  process.env.RADAR_PINTEREST_ACCESS_TOKEN = 'radar-unit-normalize';
  let calls = 0;
  const fetcher = (async (url: string) => {
    calls++;
    assert.match(url, /\/v5\/trends\/keywords\/BR\/top\/growing/);
    return new Response(JSON.stringify({ trends: [
      { keyword: 'summer nails', pct_growth_wow: 30, time_series: { '2026-09-01': 71, invalid: 4 } },
      { keyword: '', pct_growth_wow: 50 },
      { keyword: 'another topic', pct_growth_wow: 'not-a-number' },
    ] }), { status: 200, headers: { 'content-type': 'application/json' } });
  }) as typeof fetch;
  try {
    const first = await collectPinterestKeywords('BR', fetcher);
    const second = await collectPinterestKeywords('BR', fetcher);
    assert.equal(calls, 1);
    assert.deepEqual(first?.map(item => item.keyword), ['summer nails', 'another topic']);
    assert.deepEqual(first?.[0].time_series, { '2026-09-01': 71 });
    assert.equal(first?.[1].pct_growth_wow, undefined);
    assert.deepEqual(second, first);
  } finally { if (original === undefined) delete process.env.RADAR_PINTEREST_ACCESS_TOKEN; else process.env.RADAR_PINTEREST_ACCESS_TOKEN = original; }
});

test('Pinterest retries transient 503 only, at most three attempts', async () => {
  const original = process.env.RADAR_PINTEREST_ACCESS_TOKEN;
  process.env.RADAR_PINTEREST_ACCESS_TOKEN = 'radar-unit-retry';
  let calls = 0;
  const fetcher = (async () => {
    calls++;
    return calls < 3 ? new Response('', { status: 503 }) : new Response(JSON.stringify({ trends: [{ keyword: 'verified' }] }), { status: 200 });
  }) as typeof fetch;
  try {
    assert.deepEqual((await collectPinterestKeywords('GLOBAL', fetcher))?.map(item => item.keyword), ['verified']);
    assert.equal(calls, 3);
  } finally { if (original === undefined) delete process.env.RADAR_PINTEREST_ACCESS_TOKEN; else process.env.RADAR_PINTEREST_ACCESS_TOKEN = original; }
});

test('Pinterest does not retry permanent permission failures', async () => {
  const original = process.env.RADAR_PINTEREST_ACCESS_TOKEN;
  process.env.RADAR_PINTEREST_ACCESS_TOKEN = 'radar-unit-permission';
  let calls = 0;
  const fetcher = (async () => { calls++; return new Response('', { status: 403 }); }) as typeof fetch;
  try {
    await assert.rejects(collectPinterestKeywords('BR', fetcher), /PINTEREST_HTTP_403/);
    assert.equal(calls, 1);
  } finally { if (original === undefined) delete process.env.RADAR_PINTEREST_ACCESS_TOKEN; else process.env.RADAR_PINTEREST_ACCESS_TOKEN = original; }
});

test('Pinterest circuit isolates one authorization from another', async () => {
  const original = process.env.RADAR_PINTEREST_ACCESS_TOKEN;
  process.env.RADAR_PINTEREST_ACCESS_TOKEN = 'radar-unit-circuit-a';
  let calls = 0;
  const denied = (async () => { calls++; return new Response('', { status: 403 }); }) as typeof fetch;
  try {
    for (let index = 0; index < 3; index++) await assert.rejects(collectPinterestKeywords('BR', denied), /PINTEREST_HTTP_403/);
    await assert.rejects(collectPinterestKeywords('BR', denied), /PINTEREST_CIRCUIT_OPEN/);
    assert.equal(calls, 3);
    process.env.RADAR_PINTEREST_ACCESS_TOKEN = 'radar-unit-circuit-b';
    const authorized = (async () => new Response(JSON.stringify({ trends: [{ keyword: 'safe result' }] }), { status: 200 })) as typeof fetch;
    assert.equal((await collectPinterestKeywords('BR', authorized))?.[0].keyword, 'safe result');
  } finally { if (original === undefined) delete process.env.RADAR_PINTEREST_ACCESS_TOKEN; else process.env.RADAR_PINTEREST_ACCESS_TOKEN = original; }
});

test('Radar deduplicates verified feed items, survives a failed source and caches feeds across scopes', async () => {
  const directory = mkdtempSync(path.join(tmpdir(), 'clicko-radar-snapshot-'));
  const previousDirectory = process.cwd();
  const originalFetch = globalThis.fetch;
  const originalPinterest = process.env.RADAR_PINTEREST_ACCESS_TOKEN;
  const originalYouTube = process.env.YOUTUBE_API_KEY;
  const originalGoogle = process.env.GOOGLE_API_KEY;
  let trendsCalls = 0;
  let newsCalls = 0;
  process.chdir(directory);
  delete process.env.RADAR_PINTEREST_ACCESS_TOKEN;
  delete process.env.YOUTUBE_API_KEY;
  delete process.env.GOOGLE_API_KEY;
  globalThis.fetch = (async (url: string) => {
    if (url.startsWith('https://trends.google.com/')) {
      trendsCalls++;
      if (url.includes('geo=BR')) return new Response('<rss><item><title>serie c</title><ht:approx_traffic>10K+</ht:approx_traffic></item></rss>', { status: 200 });
      return new Response('<rss><item><title>criatividade digital</title><ht:approx_traffic>10K+</ht:approx_traffic></item><item><title>criatividade digital hoje</title><ht:approx_traffic>8K+</ht:approx_traffic></item></rss>', { status: 200 });
    }
    if (url.startsWith('https://news.google.com/')) { newsCalls++; return url.includes('gl=BR') ? new Response('<rss><item><title>Série A começa amanhã</title><link>https://example.org/serie-a</link></item></rss>', { status: 200 }) : new Response('', { status: 502 }); }
    throw new Error('Unexpected external source');
  }) as typeof fetch;
  try {
    const first = await getRadarSnapshot({ workspaceId: 'radar-test-a', isolationKey: 'scope-a', region: 'GLOBAL' });
    const second = await getRadarSnapshot({ workspaceId: 'radar-test-b', isolationKey: 'scope-b', region: 'GLOBAL' });
    assert.equal(first.trends.length, 1);
    assert.equal(first.trends[0].evidence.filter(item => item.source === 'google-trends').length, 2);
    assert.equal(first.sourceStatus.find(item => item.id === 'google-news')?.available, false);
    assert.equal(first.sourceStatus.find(item => item.id === 'google-trends')?.available, true);
    assert.equal(trendsCalls, 1);
    assert.equal(newsCalls, 1);
    assert.equal(second.trends.length, 1);
    assert.equal(first.trends[0].history.length, 1);
    assert.equal(second.trends[0].history.length, 1);
    const shortTopic = await getRadarSnapshot({ workspaceId: 'radar-test-c', isolationKey: 'scope-c', region: 'BR' });
    assert.equal(shortTopic.trends.length, 1);
    assert.equal(shortTopic.trends[0].evidence.filter(item => item.source === 'google-news').length, 0);
    assert.notEqual(shortTopic.trends[0].status, 'exploding');
  } finally {
    globalThis.fetch = originalFetch;
    process.chdir(previousDirectory);
    rmSync(directory, { recursive: true, force: true });
    if (originalPinterest === undefined) delete process.env.RADAR_PINTEREST_ACCESS_TOKEN; else process.env.RADAR_PINTEREST_ACCESS_TOKEN = originalPinterest;
    if (originalYouTube === undefined) delete process.env.YOUTUBE_API_KEY; else process.env.YOUTUBE_API_KEY = originalYouTube;
    if (originalGoogle === undefined) delete process.env.GOOGLE_API_KEY; else process.env.GOOGLE_API_KEY = originalGoogle;
  }
});
