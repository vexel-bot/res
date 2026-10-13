import test from 'node:test';
import assert from 'node:assert/strict';
import { calendarPublishRequest } from './publicationRequest';
import type { ConnectedAccount, Post } from '../types';

test('calendar publication selects the real capability and never passes a blob URL to a provider', () => {
  const account = { id: 'social-one', platform: 'facebook', capabilities: { canPublishText: true, canPublishImage: true } } as ConnectedAccount;
  const post = { id: 'post-one', format: 'post', title: 'Título', copy: 'Texto válido', assetIds: [], imageUrl: 'blob:local' } as Post;
  assert.deepEqual(calendarPublishRequest(post, account, []), { kind: 'text', text: 'Texto válido', title: 'Título' });
  assert.throws(() => calendarPublishRequest({ ...post, format: 'carousel' }, account, []), /permissão/);
});
