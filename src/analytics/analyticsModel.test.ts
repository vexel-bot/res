import test from 'node:test';
import assert from 'node:assert/strict';
import { buildConnectedDataset } from './analyticsModel';
import type { ConnectedAccount, Post } from '../types';

test('connected Analytics never turns local published flags or placeholders into provider metrics', () => {
  const account = { id: 'social-one', platform: 'instagram', handle: '@one', connected: true,
    connectionStatus: 'connected', followers: '9.9k', engagement: '12%', bestTime: '18:00' } as ConnectedAccount;
  const localPost = { id: 'post-one', workspaceId: 'ws-one', socialAccountIds: ['social-one'], platform: 'instagram',
    title: 'Rascunho local marcado como publicado', copy: '', format: 'post', status: 'published', author: 'Local',
    createdAt: '2026-09-01T00:00:00.000Z', scheduledAt: '2026-09-02T00:00:00.000Z', reach: 10000, likes: 1000 } as Post;
  const network = buildConnectedDataset([account], [localPost])!.networks[0];
  assert.deepEqual(network.points, []);
  assert.deepEqual(network.contents, []);
  assert.deepEqual(network.formats, []);
});
