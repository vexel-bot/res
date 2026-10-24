import type { Post } from '../types';

const isScheduled = (post: Post) => ['scheduled', 'approved'].includes(post.status)
  && Boolean(post.scheduledAt) && Number.isFinite(Date.parse(post.scheduledAt!));
const localKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

/** Uses the user's local access time. Early-morning hours remain part of the night period. */
export function dashboardGreeting(now = new Date()) {
  const hour = now.getHours();
  if (hour >= 5 && hour < 12) return 'Bom dia';
  if (hour >= 12 && hour < 18) return 'Boa tarde';
  return 'Boa noite';
}

/** Read-only projection of the current local calendar week; never creates or reschedules content. */
export function dashboardWeek(posts: Post[], workspaceId: string, now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  start.setDate(start.getDate() - (start.getDay() + 6) % 7);
  const scheduled = posts.filter(post => post.workspaceId === workspaceId && isScheduled(post))
    .sort((a, b) => Date.parse(a.scheduledAt!) - Date.parse(b.scheduledAt!));
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    const key = localKey(date);
    return { date, key, today: key === localKey(now), posts: scheduled.filter(post => localKey(new Date(post.scheduledAt!)) === key) };
  });
}

export function dashboardUpcoming(posts: Post[], workspaceId: string, now = new Date()) {
  return posts.filter(post => post.workspaceId === workspaceId && isScheduled(post) && Date.parse(post.scheduledAt!) >= now.getTime())
    .sort((a, b) => Date.parse(a.scheduledAt!) - Date.parse(b.scheduledAt!)).slice(0, 3);
}

/** Keep missing provider days as gaps rather than implying zero or inventing a trend. */
export function dashboardReachChart(points: Array<{ date: string; reach: number | null }>) {
  const sampled = points.slice(-14);
  const values = sampled.flatMap(point => typeof point.reach === 'number' && Number.isFinite(point.reach) ? [point.reach] : []);
  if (values.length < 2) return [];
  const maximum = Math.max(...values, 1);
  const minimum = Math.min(...values, 0);
  const range = Math.max(1, maximum - minimum);
  return sampled.map((point, index) => typeof point.reach === 'number' && Number.isFinite(point.reach)
    ? { x: 28 + index * (744 / (sampled.length - 1)), y: 142 - (point.reach - minimum) / range * 110, value: point.reach, date: point.date }
    : null);
}
