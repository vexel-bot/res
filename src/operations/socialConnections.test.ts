import test from 'node:test';
import assert from 'node:assert/strict';
import { connectedAccountsFromServer, type SocialConnectionSummary } from './socialConnections';

test('two profiles from one provider keep their independent server identities and capabilities', () => {
  const capabilities = { canReadProfile: true, canReadAnalytics: false, canPublishText: false, canPublishImage: true, canPublishCarousel: false, canPublishVideo: false, canPublishShortVideo: false, canPublishStory: false, canPublishDocument: false, canSchedule: false, canReadPosts: false, canReadComments: false, canReplyComments: false };
  const records: SocialConnectionSummary[] = [
    { id: 'social-a', provider: 'instagram', providerAccountId: 'ig-a', username: 'brand-a', displayName: 'Brand A', scopes: ['content_publish'], status: 'connected', capabilities },
    { id: 'social-b', provider: 'instagram', providerAccountId: 'ig-b', username: 'brand-b', displayName: 'Brand B', scopes: [], status: 'expired', capabilities: { ...capabilities, canPublishImage: false } },
  ];
  const accounts = connectedAccountsFromServer('ws-1', records, []);
  assert.deepEqual(accounts.map(item => item.id), ['social-a', 'social-b']);
  assert.deepEqual(accounts.map(item => item.providerConnectionIds), [['social-a'], ['social-b']]);
  assert.deepEqual(accounts.map(item => item.connected), [true, false]);
  assert.deepEqual(accounts.map(item => item.workspaceId), ['ws-1', 'ws-1']);
  assert.equal(accounts[0].capabilities?.canPublishImage, true);
  assert.equal(accounts[1].capabilities?.canPublishImage, false);
});
