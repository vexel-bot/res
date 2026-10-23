import test from 'node:test';
import assert from 'node:assert/strict';
import { matchesStudioDraft, readStudioSession, writeStudioSession } from './studioSession';

test('partial and non-finite stored forms are rejected before mounting inputs', () => {
  assert.equal(matchesStudioDraft({ title:'QA', duration:15 }, { title:'', duration:1 }), true);
  assert.equal(matchesStudioDraft({ title:'QA' }, { title:'', duration:1 }), false);
  assert.equal(matchesStudioDraft({ title:'QA', duration:NaN }, { title:'', duration:1 }), false);
  assert.equal(matchesStudioDraft([], { title:'' }), false);
});

test('navigation drafts survive a module change and remain scoped by user and workspace', () => {
  const records = new Map<string,string>();
  const previous = globalThis.sessionStorage;
  Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:{ getItem:(key:string) => records.get(key) || null, setItem:(key:string,value:string) => records.set(key,value), removeItem:(key:string) => records.delete(key) } });
  try {
    const key = JSON.stringify(['image','user-a','workspace-a']);
    writeStudioSession(key, { draft:{ prompt:'Uma imagem editorial' } });
    assert.deepEqual(readStudioSession(key), { draft:{ prompt:'Uma imagem editorial' } });
    assert.equal(readStudioSession(JSON.stringify(['video','user-a','workspace-a'])), undefined);
    assert.equal(readStudioSession(JSON.stringify(['image','user-b','workspace-a'])), undefined);
    assert.equal(readStudioSession(JSON.stringify(['image','user-a','workspace-b'])), undefined);
    assert.ok(records.has('clicko:studios-navigation:v1:' + key));
  } finally { Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:previous }); }
});
test('corrupt or incompatible navigation recovery never crashes the editor', () => {
  const previous = globalThis.sessionStorage;
  Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:{ getItem:() => '{bad json' } });
  try { assert.equal(readStudioSession('corrupt'), undefined); }
  finally { Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:previous }); }
});
test('a new mount can hydrate a versioned session draft without sharing another scope', () => {
  const previous = globalThis.sessionStorage;
  const key = 'clicko:studios-navigation:v1:reloaded-session';
  Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:{ getItem:(candidate:string) => candidate === key ? JSON.stringify({ version:1, value:{ title:'Retomar projeto' } }) : JSON.stringify({ version:99, value:{ title:'Incompatível' } }) } });
  try {
    assert.deepEqual(readStudioSession('reloaded-session'), { title:'Retomar projeto' });
    assert.equal(readStudioSession('incompatible-session'), undefined);
  } finally { Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:previous }); }
});
test('blocked storage still allows in-session recovery without requests or file generation', () => {
  const previous = globalThis.sessionStorage;
  Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:{ setItem:() => { throw new Error('blocked'); } } });
  try { writeStudioSession('blocked', { title:'Rascunho' }); assert.deepEqual(readStudioSession('blocked'), { title:'Rascunho' }); }
  finally { Object.defineProperty(globalThis, 'sessionStorage', { configurable:true, value:previous }); }
});
