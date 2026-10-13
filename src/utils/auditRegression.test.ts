import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequestGuard } from './requestGuard';
import { calendarIncludesDate, calendarPeriodBounds, calendarPeriodDates, calendarSchedule, navigateCalendarDate } from './calendarDates';
import { canAccessNavigation } from '../security/accessControl';
import { csvCell } from './csv';
import { startKlicMessageCycle } from './klicMessageCycle';

function messageClock() {
  let now = 0;
  let id = 0;
  const timers = new Map<number, { at: number; callback: () => void }>();
  const events: Array<[string, number]> = [];
  const start = () => startKlicMessageCycle({
    schedule: (callback, delay) => { timers.set(++id, { at: now + delay, callback }); return id; },
    cancel: timer => { timers.delete(timer); },
    canShow: () => true,
    entryDuration: () => 240,
    exitDuration: () => 160,
    show: () => events.push(['show', now]),
    hide: () => events.push(['hide', now]),
    clear: () => events.push(['clear', now]),
  });
  const advance = (duration: number) => {
    const end = now + duration;
    while (timers.size) {
      assert.equal(timers.size, 1, 'only one message timer may exist');
      const [key, timer] = [...timers.entries()].sort((a, b) => a[1].at - b[1].at)[0];
      if (timer.at > end) break;
      now = timer.at; timers.delete(key); timer.callback();
    }
    now = end;
  };
  return { start, advance, events, timers };
}

test('KLIC waits 60s, holds 15s after entry, and waits again only after exit', () => {
  const clock = messageClock();
  const stop = clock.start();
  clock.advance(59_999); assert.deepEqual(clock.events, []);
  clock.advance(1); assert.deepEqual(clock.events, [['show', 60_000]]);
  clock.advance(15_239); assert.equal(clock.events.length, 1);
  clock.advance(1); assert.deepEqual(clock.events[1], ['hide', 75_240]);
  clock.advance(160); assert.deepEqual(clock.events[2], ['clear', 75_400]);
  clock.advance(59_999); assert.equal(clock.events.length, 3);
  clock.advance(1); assert.deepEqual(clock.events[3], ['show', 135_400]);
  clock.advance(600_000);
  assert.ok(clock.events.filter(([event]) => event === 'show').length > 6, 'cycle has no session cap');
  stop(); assert.equal(clock.timers.size, 0);
});

test('KLIC cancels timers in every phase, including StrictMode mount cleanup', () => {
  for (const elapsed of [0, 60_001, 75_241]) {
    const clock = messageClock();
    const stop = clock.start(); clock.advance(elapsed); stop();
    const count = clock.events.length;
    clock.advance(300_000); assert.equal(clock.events.length, count);
    assert.equal(clock.timers.size, 0);
    const stopAgain = clock.start();
    clock.advance(59_999); assert.equal(clock.events.length, count);
    clock.advance(1); assert.equal(clock.events.length, count + 1);
    stopAgain();
  }
});

test('a response from another account cannot update the current account', () => {
  const guard = createRequestGuard();
  let scope = 'personal';
  const personal = guard.begin(scope, () => scope);
  scope = 'company';
  assert.equal(personal(), false);
  const company = guard.begin(scope, () => scope);
  assert.equal(company(), true);
  scope = 'personal';
  assert.equal(personal(), false); // Switching back never revives an old response.
  assert.equal(company(), false);
});
test('latest refresh wins; clearing/unmounting invalidates responses', () => {
  const guard = createRequestGuard();
  const first = guard.begin('a', () => 'a');
  const second = guard.begin('a', () => 'a');
  assert.equal(first(), false);
  assert.equal(second(), true);
  guard.invalidate();
  assert.equal(second(), false);
});
test('calendar month navigation clamps month ends and supports leap years', () => {
  for (const [year, expected] of [[2026, 28], [2028, 29]]) {
    const original = new Date(year, 0, 31, 12);
    const next = navigateCalendarDate(original, 'month', 1);
    assert.equal(next.getMonth(), 1);
    assert.equal(next.getDate(), expected);
    assert.equal(original.getDate(), 31);
  }
  assert.equal(navigateCalendarDate(new Date(2026, 2, 31), 'month', -1).getMonth(), 1);
  assert.equal(navigateCalendarDate(new Date(2026, 11, 31), 'month', 1).getFullYear(), 2027);
});
test('calendar list uses its monthly period and weekly navigation preserves weekdays', () => {
  const date = new Date(2026, 0, 31, 12);
  assert.equal(navigateCalendarDate(date, 'list', 1).getMonth(), 1);
  const next = navigateCalendarDate(date, 'week', 1);
  assert.equal(next.getDay(), date.getDay());
  assert.equal(next.getDate(), 7);
});
test('calendar rejects empty, invalid and overflowing dates without throwing', () => {
  for (const [date, time] of [['', '09:00'], ['2026-02-31', '09:00'], ['2026-01-01', '25:00'], ['2026-13-01', '09:00']]) assert.equal(calendarSchedule(date, time), null);
  assert.ok(calendarSchedule('2028-02-29', '09:00'));
});
test('calendar period filters include local month/week boundaries, but not other periods or invalid dates', () => {
  const anchor = new Date(2026, 8, 5, 12);
  const date = (year: number, month: number, day: number, hour = 12) => new Date(year, month, day, hour).toISOString();
  for (const mode of ['month', 'list'] as const) {
    assert.equal(calendarIncludesDate(date(2026, 8, 1, 0), anchor, mode), true);
    assert.equal(calendarIncludesDate(date(2026, 8, 30, 23), anchor, mode), true);
    assert.equal(calendarIncludesDate(date(2026, 9, 1, 0), anchor, mode), false);
    assert.equal(calendarIncludesDate(date(2025, 8, 5), anchor, mode), false);
    assert.equal(calendarIncludesDate(undefined, anchor, mode), false);
    assert.equal(calendarIncludesDate('invalid', anchor, mode), false);
  }
  assert.equal(calendarIncludesDate(date(2026, 7, 30, 0), anchor, 'week'), true);
  assert.equal(calendarIncludesDate(date(2026, 8, 5, 23), anchor, 'week'), true);
  assert.equal(calendarIncludesDate(date(2026, 8, 6, 0), anchor, 'week'), false);
});
test('calendar custom periods include both selected dates and reject reversed ranges', () => {
  const anchor = new Date(2026, 9, 4, 12);
  const range = { start: '2026-10-03', end: '2026-10-06' };
  assert.equal(calendarIncludesDate(new Date(2026, 9, 3, 0).toISOString(), anchor, 'custom', range), true);
  assert.equal(calendarIncludesDate(new Date(2026, 9, 6, 23).toISOString(), anchor, 'custom', range), true);
  assert.equal(calendarIncludesDate(new Date(2026, 9, 7, 0).toISOString(), anchor, 'custom', range), false);
  assert.equal(calendarPeriodDates(anchor, 'custom', range).length, 4);
  assert.equal(calendarPeriodBounds(anchor, 'custom', { start: '2026-10-07', end: '2026-10-02' }), null);
});
test('personal/corporate and collaborator access rules remain enforced', () => {
  const master = { role: 'master' as const, modules: [] };
  const collaborator = { role: 'collaborator' as const, modules: ['calendar' as const] };
  assert.equal(canAccessNavigation(undefined, 'settings'), false);
  assert.equal(canAccessNavigation(master, 'team', 'personal'), false);
  assert.equal(canAccessNavigation(master, 'team', 'company'), true);
  assert.equal(canAccessNavigation(collaborator, 'settings', 'company'), true);
  assert.equal(canAccessNavigation(collaborator, 'calendar', 'company'), true);
  assert.equal(canAccessNavigation(collaborator, 'analytics', 'company'), false);
});
test('CSV quotes text and neutralizes formulas without changing numeric metrics', () => {
  assert.equal(csvCell('Olá, "Clicko"'), '"Olá, ""Clicko"""');
  assert.equal(csvCell('=1+1'), '"\'=1+1"');
  assert.equal(csvCell(' @SUM(A1)'), '"\' @SUM(A1)"');
  assert.equal(csvCell(-12), '"-12"');
  assert.equal(csvCell(null), '""');
});
