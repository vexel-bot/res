/** Clamps the day before month navigation so January 31 never skips February. */
export type CalendarPeriodMode = 'day' | 'week' | 'month' | 'custom' | 'list';

export type CalendarCustomRange = { start: string; end: string };

function localDate(value: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
  date.setHours(0, 0, 0, 0);
  return date;
}

export function navigateCalendarDate(date: Date, mode: CalendarPeriodMode, direction: number): Date {
  const next = new Date(date);
  if (mode === 'day') {
    next.setDate(next.getDate() + direction);
  } else if (mode === 'week') {
    next.setDate(next.getDate() + direction * 7);
  } else {
    const day = next.getDate();
    next.setDate(1);
    next.setMonth(next.getMonth() + direction);
    const lastDay = new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate();
    next.setDate(Math.min(day, lastDay));
  }
  return next;
}

export function calendarSchedule(date: string, time: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) return null;
  const [year, month, day] = date.split('-').map(Number);
  const [hour, minute] = time.split(':').map(Number);
  const value = new Date(`${date}T${time}:00`);
  if (!Number.isFinite(value.getTime()) || value.getFullYear() !== year || value.getMonth() !== month - 1 || value.getDate() !== day || value.getHours() !== hour || value.getMinutes() !== minute) return null;
  return value.toISOString();
}

/** Calendar periods use local dates, matching the visible month/week headings. */
export function calendarPeriodBounds(anchor: Date, mode: CalendarPeriodMode, customRange?: CalendarCustomRange): { start: Date; end: Date } | null {
  if (!Number.isFinite(anchor.getTime())) return null;
  if (mode === 'custom') {
    const start = localDate(customRange?.start || '');
    const endInclusive = localDate(customRange?.end || '');
    if (!start || !endInclusive || endInclusive < start) return null;
    const end = new Date(endInclusive);
    end.setDate(end.getDate() + 1);
    return { start, end };
  }
  const start = new Date(anchor);
  start.setHours(0, 0, 0, 0);
  if (mode === 'week') start.setDate(start.getDate() - start.getDay());
  else if (mode !== 'day') start.setDate(1);
  const end = new Date(start);
  if (mode === 'day') end.setDate(end.getDate() + 1);
  else if (mode === 'week') end.setDate(end.getDate() + 7);
  else end.setMonth(end.getMonth() + 1);
  return { start, end };
}

/** Builds the exact visible date sequence for day, week, month or a custom interval. */
export function calendarPeriodDates(anchor: Date, mode: Exclude<CalendarPeriodMode, 'list'>, customRange?: CalendarCustomRange): Date[] {
  const bounds = calendarPeriodBounds(anchor, mode, customRange);
  if (!bounds) return [];
  if (mode === 'month') {
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    first.setDate(first.getDate() - first.getDay());
    return Array.from({ length: 42 }, (_, index) => { const day = new Date(first); day.setDate(first.getDate() + index); return day; });
  }
  const dates: Date[] = [];
  for (const date = new Date(bounds.start); date < bounds.end; date.setDate(date.getDate() + 1)) dates.push(new Date(date));
  return dates;
}

export function calendarIncludesDate(value: string | undefined, anchor: Date, mode: CalendarPeriodMode, customRange?: CalendarCustomRange): boolean {
  if (!value || !Number.isFinite(anchor.getTime())) return false;
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return false;
  const bounds = calendarPeriodBounds(anchor, mode, customRange);
  return Boolean(bounds && timestamp >= bounds.start.getTime() && timestamp < bounds.end.getTime());
}
