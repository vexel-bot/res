import test from 'node:test';
import assert from 'node:assert/strict';
import { providerFailure } from './providerErrors';
import { klicProviderConfig, klicTranscriptionModel } from './providerConfig';
import { consumeKlicStream, readKlicJson, requestKlicJson } from '../../src/klic/transport';

test('provider selection is explicit, server-only and does not treat TTS credentials or placeholders as Gemini authorization', () => {
  assert.equal(klicProviderConfig({}).configured, false);
  assert.equal(klicProviderConfig({ GOOGLE_APPLICATION_CREDENTIALS: '/private/tts.json', GOOGLE_CLOUD_PROJECT: 'tts-project' }).configured, false);
  assert.equal(klicProviderConfig({ GEMINI_API_KEY: 'MY_GEMINI_API_KEY' }).configured, false);
  assert.equal(klicProviderConfig({ GOOGLE_API_KEY: 'test-only' }).configured, false);
  assert.equal(klicProviderConfig({ GOOGLE_API_KEY: 'test-only' }).googleApiKeyIgnored, true);
  assert.equal(klicProviderConfig({ GEMINI_API_KEY: 'gemini-test', GOOGLE_API_KEY: 'other-service-test' }).apiKey, 'gemini-test');
  assert.equal(klicProviderConfig({ GEMINI_API_KEY: 'test-only' }).mode, 'developer-api');
  const vertex = klicProviderConfig({ GOOGLE_GENAI_USE_VERTEXAI: 'true', GOOGLE_CLOUD_PROJECT: 'test-project', KLIC_CHAT_MODEL: 'selected-model' });
  assert.equal(vertex.mode, 'vertex'); assert.equal(vertex.configured, true); assert.equal(vertex.model, 'selected-model');
  assert.equal(klicProviderConfig({ GOOGLE_GENAI_USE_VERTEXAI: 'true', GEMINI_API_KEY: 'test-only' }).configured, false);
});

test('audio transcription model is server-configurable and independent from the chat model', () => {
  assert.equal(klicTranscriptionModel({ KLIC_CHAT_MODEL: 'gemini-chat' }), 'gemini-3.5-flash');
  assert.equal(klicTranscriptionModel({ KLIC_CHAT_MODEL: 'gemini-chat', KLIC_TRANSCRIPTION_MODEL: 'gemini-audio' }), 'gemini-audio');
});

test('provider failures distinguish configuration, authorization, disabled API, billing, quota, model, timeout, network and empty text without leaks', () => {
  const cases: Array<[unknown,string]> = [
    [new Error('KLIC_PROVIDER_NOT_CONFIGURED'),'KLIC_GEMINI_API_KEY_REQUIRED'],
    [new Error('KLIC_GEMINI_API_KEY_REQUIRED'),'KLIC_GEMINI_API_KEY_REQUIRED'],
    [new Error('KLIC_VERTEX_CONFIGURATION_REQUIRED'),'KLIC_VERTEX_CONFIGURATION_REQUIRED'],
    [{status:403,message:'{"details":[{"reason":"SERVICE_DISABLED","metadata":{"project":"PRIVATE","key":"SECRET"}}]}'},'KLIC_PROVIDER_SERVICE_DISABLED'],
    [{status:403,message:'PERMISSION_DENIED SECRET'},'KLIC_PROVIDER_ACCESS_DENIED'],
    [{status:400,message:'API_KEY_INVALID SECRET'},'KLIC_PROVIDER_ACCESS_DENIED'],
    [{status:403,message:'BILLING_DISABLED SECRET'},'KLIC_PROVIDER_BILLING'],
    [{status:429,message:'RESOURCE_EXHAUSTED SECRET'},'KLIC_PROVIDER_QUOTA'],
    [{status:404},'KLIC_PROVIDER_MODEL_UNAVAILABLE'],
    [new DOMException('SECRET','TimeoutError'),'KLIC_PROVIDER_TIMEOUT'],
    [new Error('fetch failed SECRET'),'KLIC_PROVIDER_NETWORK'],
    [new Error('KLIC_EMPTY_RESPONSE'),'KLIC_EMPTY_RESPONSE'],
    [new Error('KLIC_RESPONSE_BLOCKED'),'KLIC_RESPONSE_BLOCKED'],
    [{status:500,message:'SECRET'},'KLIC_PROVIDER_UNAVAILABLE'],
  ];
  for (const [error, code] of cases) {
    const failure = providerFailure(error);
    assert.equal(failure.code, code); assert.ok(failure.status >= 400);
    assert.doesNotMatch(JSON.stringify(failure), /SECRET|PRIVATE/);
  }
});

test('NDJSON preserves split UTF-8 and final line without newline; a terminal event does not wait for transport EOF', async () => {
  const conversation = { id: 'conversation', messages: [] };
  const input = JSON.stringify({type:'delta',data:'ação 🧡'}) + '\n' + JSON.stringify({type:'done',data:conversation});
  const bytes = new TextEncoder().encode(input);
  const events: any[] = [];
  await consumeKlicStream(new ReadableStream({start(c){for (const byte of bytes)c.enqueue(Uint8Array.of(byte));c.close();}}), e=>events.push(e));
  assert.equal(events[0].data,'ação 🧡'); assert.equal(events.at(-1).type,'done');
  let cancelled = false;
  await consumeKlicStream(new ReadableStream({start(c){c.enqueue(new TextEncoder().encode(JSON.stringify({type:'done',data:conversation})+'\n'));},cancel(){cancelled=true;}}),()=>{});
  assert.equal(cancelled,true);
});

test('malformed or truncated streams and proxy HTML fail explicitly; a later valid response still succeeds', async () => {
  for (const raw of ['not json\n', '{"type":"delta","data":"partial"}\n', '{"type":"done","data":{}}\n']) {
    await assert.rejects(()=>consumeKlicStream(new Response(raw).body!,()=>{}));
  }
  await assert.rejects(()=>readKlicJson(new Response('<html>PRIVATE</html>',{status:502})),error=>error instanceof Error && error.message.includes('502') && !error.message.includes('PRIVATE'));
  await assert.rejects(()=>readKlicJson(new Response(JSON.stringify({error:'Credencial recusada.'}),{status:503})),/Credencial recusada/);
  assert.deepEqual(await readKlicJson(new Response('{"ok":true}')), {ok:true});
});

test('JSON requests abort within their deadline and caller cancellation is preserved', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (_url,init) => new Promise<Response>((_resolve,reject) => {
    const signal=init!.signal!; if(signal.aborted)reject(signal.reason);
    else signal.addEventListener('abort',()=>reject(signal.reason),{once:true});
  });
  try {
    await assert.rejects(()=>requestKlicJson('/test',{},10),e=>e instanceof Error && e.name==='TimeoutError');
    const controller=new AbortController();controller.abort();
    await assert.rejects(()=>requestKlicJson('/test',{signal:controller.signal},1000),e=>e instanceof Error && e.name==='AbortError');
  } finally {globalThis.fetch=original;}
});
