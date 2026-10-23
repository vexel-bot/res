import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultStudioTool, isStudioModule, permittedStudioTools, studioCategories, studioNavigationAllowed, studioToolForPath, studioTools } from './studioNavigation';
import { canAccessNavigation } from '../security/accessControl';
import type { WorkspaceMember } from '../types';

test('Studios tools have unique URLs and resolve to the original API module', () => {
  assert.equal(new Set(studioTools.map(tool => tool.id)).size, studioTools.length);
  assert.equal(new Set(studioTools.map(tool => tool.path)).size, studioTools.length);
  for (const tool of studioTools) {
    assert.deepEqual(studioToolForPath(tool.path + '/'), tool);
    assert.ok(isStudioModule(tool.module));
    assert.ok(studioCategories.some(category => category.id === tool.category));
  }
  assert.equal(studioToolForPath('/studios/not-a-tool'), undefined);
  assert.equal(studioToolForPath('/settings'), undefined);
});
test('old image/video links remain aliases without inventing a new entitlement', () => {
  assert.deepEqual(studioToolForPath('/image'), defaultStudioTool('create-image'));
  assert.deepEqual(studioToolForPath('/video/'), defaultStudioTool('create-video'));
  assert.deepEqual(studioToolForPath('/studios'), defaultStudioTool('create-image'));
  assert.equal(isStudioModule('library'), false);
});
test('image-only and video-only members never gain the other media permission through Studios', () => {
  for (const module of ['create-image', 'create-video'] as const) {
    const user = { role:'creative', modules:[module] } as WorkspaceMember;
    const tools = permittedStudioTools(tab => canAccessNavigation(user, tab));
    assert.ok(tools.length > 0);
    assert.ok(tools.every(tool => tool.module === module));
    assert.ok(tools.some(tool => tool.category === 'advertising'));
  }
  assert.equal(permittedStudioTools(() => false).length, 0);
});
test('existing motion, ads and editorial tools remain mapped to actual implementations', () => {
  assert.equal(studioTools.find(tool => tool.id === 'video-motion')?.entry, 'motion');
  assert.equal(studioTools.find(tool => tool.id === 'ad-create')?.entry, 'ad');
  assert.equal(studioTools.find(tool => tool.id === 'ad-creatives')?.entry, 'advertising');
  assert.equal(studioTools.find(tool => tool.id === 'image-editorial')?.entry, 'editorial');
  assert.ok(!studioTools.some(tool => /variation/.test(tool.id)), 'Unimplemented batch variations must not receive a working route');
});
test('pending editor operations can prevent navigation without changing their request scope', () => {
  const previous = globalThis.window;
  const target = new EventTarget();
  Object.defineProperty(globalThis, 'window', { configurable:true, value:target });
  try {
    assert.equal(studioNavigationAllowed(), true);
    const block = (event: Event) => event.preventDefault();
    target.addEventListener('clicko:studio-before-leave', block);
    assert.equal(studioNavigationAllowed(), false);
    target.removeEventListener('clicko:studio-before-leave', block);
    assert.equal(studioNavigationAllowed(), true);
  } finally { Object.defineProperty(globalThis, 'window', { configurable:true, value:previous }); }
});
