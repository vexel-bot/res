import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { motionGeminiError } from './motionGeminiModel';

test('experimental credential UI never uses browser persistence or project recovery',()=>{
  const ui=readFileSync('src/studios/local/MotionGeminiSettings.tsx','utf8');
  assert.doesNotMatch(ui,/localStorage|sessionStorage|pendingRef/);
  assert.match(ui,/if\(!development\?\.enabled\|\|!status\?\.available\)return null/);
  assert.match(ui,/setKey\(''\);setVisible\(false\)/);
  assert.match(ui,/autoComplete="off"/);
  assert.match(ui,/maxLength=\{8192\}/);
});
test('experimental failures explain their limit and never advertise automatic fallback',()=>{
  assert.match(motionGeminiError('llm_provider_http_429'),/Nenhum retry/);
  assert.match(motionGeminiError('motion_gemini_free_tier_unverified'),/bloqueada/);
  assert.match(motionGeminiError('llm_provider_transport_failed'),/incerto/);
});
test('existing motion explicitly chooses planner and preserves reviewed application and rendering',()=>{
  const source=readFileSync('src/studios/local/LocalProductionStudio.tsx','utf8');
  for(const feature of ['A · Planejador atual','B · Gemini experimental','Planejar com Gemini','Criar Motion Design','gemini.inferenceReady','localApi.document','expectedRevision','render-jobs'])assert.ok(source.includes(feature),feature);
  const proxy=readFileSync('server/studios/proxy.ts','utf8');
  assert.match(proxy,/CLICKO_MOTION_GEMINI_EXPERIMENTAL === 'true' && module === 'create-video' && isLocalDevRequest\(req\)/);
});
