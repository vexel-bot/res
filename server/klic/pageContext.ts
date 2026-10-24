import { canAccessNavigation } from '../../src/security/accessControl';
import { KLIC_MODULES, type KlicActor, type KlicPageContext, type KlicSource } from '../../src/klic/contracts';
import { KlicError } from './context';

const clean = (value: unknown, limit = 80) => typeof value === 'string' ? value.trim().slice(0, limit) : '';

/** Browser page metadata is ephemeral, scoped, and never a source of authority. */
export function checkedPageContext(actor: KlicActor, source: unknown, value: unknown, sources: KlicSource[]): KlicPageContext | null {
  if (value == null) return null;
  if (!value || typeof value !== 'object') throw new KlicError('KLIC_PAGE_CONTEXT_INVALID');
  const page = value as Partial<KlicPageContext>;
  if (page.workspaceId !== actor.workspaceId || (page.clientId ?? null) !== actor.clientId || page.module !== source
    || !KLIC_MODULES.includes(page.module!) || !canAccessNavigation(actor.user, page.module!, actor.accountType)) {
    throw new KlicError('KLIC_PAGE_CONTEXT_SCOPE_MISMATCH', 403);
  }
  const details = page.details && typeof page.details === 'object' ? page.details : {};
  const filters = details.filters && typeof details.filters === 'object'
    ? Object.fromEntries(Object.entries(details.filters).slice(0, 8).map(([key, entry]) => [clean(key, 40), clean(entry)]).filter(([key, entry]) => key && entry))
    : undefined;
  const selected = details.selected && typeof details.selected === 'object' ? details.selected : undefined;
  const selectedId = clean(selected?.id, 140);
  const verifiedSelection = selectedId && (selectedId === actor.clientId || sources.some(item => item.status === 'available' && item.records.some(record => record.id === selectedId)))
    ? { kind: clean(selected?.kind, 40), id: selectedId } : undefined;
  return { module: page.module!, workspaceId: actor.workspaceId, clientId: actor.clientId, details: {
    view: clean(details.view), period: clean(details.period, 120),
    ...(filters && Object.keys(filters).length ? { filters } : {}),
    ...(verifiedSelection ? { selected: verifiedSelection } : {}),
  } };
}
