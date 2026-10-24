import { KLIC_DOMAINS, type KlicSource } from '../../src/klic/contracts';
import { memberHasScope, readKlicGovernance, workspaceOwnsClient } from '../governance';
import { hasPermission } from '../../src/security/accessControl';
import { readKlicAnalytics, readKlicConnections, readKlicScheduledPublications } from '../integrations';
import { getRadarSnapshot } from '../radar';
import type { KlicCore } from './core';

export function registerAdapters(core: KlicCore) {
  for (const domain of KLIC_DOMAINS) core.register({
    id: domain + '.read', domain, effect: 'read',
    async run({ actor, local, request }) {
      let records: KlicSource['records'] = [];
      let provenance: KlicSource['provenance'] = 'service';
      if (['approvals', 'team', 'history', 'connections', 'analytics'].includes(domain)) {
        if (domain === 'connections' && !hasPermission(actor.user, 'connections.read') || domain === 'analytics' && !hasPermission(actor.user, 'analytics.read')) {
          return { domain, provenance, status: 'denied', records, reason: 'This role cannot access the requested operational data.' };
        }
        if (actor.clientId && (!workspaceOwnsClient(actor.workspaceId, actor.clientId) || !memberHasScope(actor.user, 'client', actor.clientId))) {
          return { domain, provenance, status: 'unavailable', records, reason: 'Client relationship is not available for this authorized view.' };
        }
        const governance = readKlicGovernance({ workspaceId: actor.workspaceId, user: actor.user });
        if (domain === 'approvals') records = governance.approvals;
        if (domain === 'team') records = governance.team;
        if (domain === 'history') records = governance.history;
        if (domain === 'connections') records = await readKlicConnections(actor.workspaceId, actor.accountType, actor.clientId);
        if (domain === 'analytics') records = await readKlicAnalytics(actor.workspaceId, actor.accountType, actor.clientId);
      } else if (domain === 'calendar') {
        if (actor.clientId && !workspaceOwnsClient(actor.workspaceId, actor.clientId)) {
          return { domain, provenance, status: 'unavailable', records, reason: 'Client relationship is not available for this authorized view.' };
        }
        const serviceRecords = hasPermission(actor.user, 'connections.read')
          ? await readKlicScheduledPublications(actor.workspaceId, actor.accountType, actor.clientId) : [];
        const localRecords = local.calendar || [];
        const confirmedIds = new Set(serviceRecords.map(record => record.id));
        records = [...serviceRecords, ...localRecords.filter(record => !confirmedIds.has(record.id))];
        provenance = serviceRecords.length && localRecords.length ? 'mixed' : serviceRecords.length ? 'service' : 'browser-local';
        if (!serviceRecords.length && !(domain in local)) return { domain, provenance, status: 'unavailable', records, reason: 'No authorized calendar data is available.' };
      } else if (domain === 'radar') {
        const brand = local.brand?.[0];
        const snapshot = await getRadarSnapshot({ workspaceId: actor.workspaceId, region: request.region === 'GLOBAL' ? 'GLOBAL' : 'BR', forceRefresh: request.forceRefresh === true, contextProfile: brand, clientContext: local.clients?.[0],
          isolationKey: JSON.stringify([actor.workspaceId, actor.userId, actor.clientId]), });
        records = snapshot.trends.slice(0, 4).map(trend => ({ ...trend, workspaceId: actor.workspaceId, clientId: actor.clientId }));
        if (!records.length && snapshot.sourceStatus.every(s => !s.available)) return { domain, provenance, status: 'unavailable', records, reason: 'Radar sources unavailable.' };
        return { domain, provenance, status: records.length ? 'available' : 'empty', records, radar: snapshot };
      } else {
        provenance = 'browser-local';
        if (!(domain in local)) return { domain, provenance, status: 'unavailable', records, reason: 'No authorized local snapshot was supplied for this domain.' };
        records = local[domain] || [];
      }
      return { domain, provenance, status: records.length ? 'available' : 'empty', records };
    },
  });
  core.register({ id: 'automations.start', domain: 'automations', effect: 'external', run: () => ({ domain: 'automations', provenance: 'service', status: 'unavailable', records: [], reason: 'Executor not connected.' }) });
}
