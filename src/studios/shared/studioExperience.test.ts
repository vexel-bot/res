import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { canvasDocumentPoint } from '../local/localModel';
import { initialVideoBrief, validateBrief, videoBriefDefaults } from '../video/videoModel';
import { initialImageDraft, imageDocumentInput, imageDraftFromDocument, imagePrompt, imageDraftError } from '../image/imageModel';
import type { CraftDocument } from '../craft/craftApi';
import { studioDefaultTimelineHeight, studioTimelineHeight, studioWorkspaceHeight, isStudioTypingTarget, studioShortcut } from './studioWorkspaceModel';
import { matchesStudioDraft } from '../studioSession';

test('video creation defaults are deterministic, reviewable and do not mutate the draft', () => {
  const draft = { ...initialVideoBrief(), objective:'Apresentar nossa nova coleção' };
  const before = structuredClone(draft), resolved = videoBriefDefaults(draft);
  assert.deepEqual(draft, before); assert.equal(resolved.title, draft.objective); assert.equal(resolved.audience,'Público geral');
  assert.equal(validateBrief(resolved), undefined);
});
test('explicit direction and advertising audience are never invented or replaced', () => {
  const draft = { ...initialVideoBrief(), title:'Nome escolhido', audience:'Clientes existentes', objective:'Apresentar nossa nova coleção' };
  assert.deepEqual(videoBriefDefaults(draft,true),draft);
  assert.equal(videoBriefDefaults({...draft,audience:''},true).audience,'');
  assert.ok(validateBrief(videoBriefDefaults({...draft,audience:''},true)));
});
test('defaults do not bypass missing ideas or invalid duration validation', () => {
  assert.ok(validateBrief(videoBriefDefaults(initialVideoBrief())));
  assert.ok(validateBrief(videoBriefDefaults({...initialVideoBrief(),objective:'Uma ideia suficiente',duration:0})));
});
test('image advertising fields round-trip on the existing document and brief', () => {
  const draft = {...initialImageDraft(),prompt:'Campanha do nosso produto',purpose:'Anúncio',audience:'Clientes locais',campaignGoal:'Levar visitas ao site'};
  const input = imageDocumentInput('workspace',draft);
  assert.equal(input.brief.audience,draft.audience); assert.equal(imageDraftFromDocument({...input,documentId:'doc'} as unknown as CraftDocument).campaignGoal,draft.campaignGoal);
  assert.match(imagePrompt(draft),/Clientes locais/); assert.match(imagePrompt(draft),/Levar visitas ao site/);
  assert.ok(imageDraftError({...draft,campaignGoal:'a'.repeat(1001)}));
});
test('old image drafts remain compatible without advertising properties', () => {
  const old = {...initialImageDraft(),prompt:'Imagem autorizada'};
  assert.equal(matchesStudioDraft(old,initialImageDraft()),true);
  assert.equal(imageDraftError(old),undefined); assert.doesNotMatch(imagePrompt(old),/undefined/);
});
test('canvas hit testing accounts for horizontal and vertical letterboxes', () => {
  assert.deepEqual(canvasDocumentPoint(250,250,500,500,1000,500),{x:500,y:250});
  assert.equal(canvasDocumentPoint(250,30,500,500,1000,500),undefined);
  assert.deepEqual(canvasDocumentPoint(250,250,500,500,500,1000),{x:250,y:500});
  assert.equal(canvasDocumentPoint(30,250,500,500,500,1000),undefined);
});
test('canvas hit testing handles actual size, boundaries and zero-sized surfaces', () => {
  assert.deepEqual(canvasDocumentPoint(100,50,400,200,800,400),{x:200,y:100});
  assert.deepEqual(canvasDocumentPoint(400,200,400,200,800,400),{x:800,y:400});
  assert.equal(canvasDocumentPoint(10,10,0,200,800,400),undefined);
});
test('workspace and timeline stay bounded with a usable canvas area', () => {
  assert.equal(studioWorkspaceHeight(768,160),592); assert.equal(studioWorkspaceHeight(300,160),260);
  assert.equal(studioTimelineHeight(1000,600),270); assert.equal(studioTimelineHeight(20,600),100);
  assert.equal(studioTimelineHeight(Number.NaN,600),160); assert.equal(isStudioTypingTarget(null),false);
  assert.equal(studioDefaultTimelineHeight(420),110); assert.equal(studioDefaultTimelineHeight(600),170);
});
test('save works while typing, while text undo and unmodified keys remain native', () => {
  assert.equal(studioShortcut('s',true,false,true),'save');
  assert.equal(studioShortcut('z',true,false,true),undefined);
  assert.equal(studioShortcut('s',false,false,false),undefined);
});
test('editor undo/redo require modifiers and apply outside text controls', () => {
  assert.equal(studioShortcut('z',true,false,false),'undo');
  assert.equal(studioShortcut('Z',true,true,false),'redo');
  assert.equal(studioShortcut('x',true,false,false),undefined);
});
test('canonical editor retains manual editing, recovery and real export entry points', () => {
  const source = readFileSync('src/studios/video/CanonicalVideoEditor.tsx','utf8');
  for (const entry of ['Dividir no cursor','Volume (dB)','Entrada no arquivo (s)','Velocidade','Keyframes essenciais','Limpar keyframes','Adicionar título','Ativar áudio','Recuperar','Gerar prévia / MP4','Cancelar','Tentar novamente']) assert.ok(source.includes(entry),entry);
  assert.match(source,/inspector=\{item \?/); assert.match(source,/StudioEditorFrame/);
});
test('local workspace retains versions, agent plans, assets and same-document montage', () => {
  const source = readFileSync('src/studios/local/LocalProductionStudio.tsx','utf8');
  for (const entry of ['restoreStudioDocumentVersion','confirmPending','Aplicar plano','configure(workspaceId','insertAsset','CanonicalVideoEditor','expectedRevision','studio-before-leave','StudioKlicButton']) assert.ok(source.includes(entry),entry);
  assert.doesNotMatch(source,/window\.fetch\(/);
});

test('image creation container is not mistaken for a global progress bar', () => {
  const source = readFileSync('src/studios/image/ImageStudio.tsx','utf8');
  const css = readFileSync('src/studios/image/image-studio.css','utf8');
  assert.match(source,/className="is-root is-focused"/);
  assert.doesNotMatch(source,/className="is-root [^"]*progress/);
  assert.match(css,/\.is-focused\[data-creation-state=idea\]/);
});

test('video opens its editor after the save leave guard has settled', () => {
  const source = readFileSync('src/studios/video/VideoStudio.tsx','utf8');
  assert.match(source,/pendingArea\.current = next; updateArea\(next\)/);
  assert.match(source,/busy \|\| studio\.busy \|\| actionRef\.current \|\| !pendingArea\.current/);
  assert.match(source,/const next = pendingArea\.current; pendingArea\.current = undefined;\s+onAreaChange\?\.\(next\)/);
});

test('Studios exposes category and tool navigation without the hidden desktop switcher', () => {
  const source = readFileSync('src/studios/StudiosWorkspace.tsx','utf8');
  assert.match(source,/aria-label="Áreas dos Studios"/);
  assert.match(source,/className="studios-tool-nav"/);
  assert.match(source,/label="Área dos Studios"/); assert.match(source,/label="Ferramenta"/);
  assert.doesNotMatch(source,/Alterar Studio|studios-switcher/);
  assert.match(source,/if \(next.id !== tool.id && !studioNavigationAllowed\(\)\) return/);
});

test('image primary generation precedes optional settings and keeps the authorization guard', () => {
  const source = readFileSync('src/studios/image/ImageStudio.tsx','utf8');
  assert.ok(source.indexOf('className="is-generate"') < source.indexOf('className="is-creation-details"'));
  assert.match(source,/hasInputs && !authorized/);
  assert.match(source,/Confirmo a autorização declarada/);
  assert.match(source,/Configurações avançadas/);
});

test('video project discovery does not wait for optional AI service preflights', () => {
  const source = readFileSync('src/studios/video/VideoStudio.tsx','utf8');
  assert.match(source,/productApi\.studioDocuments\(workspaceId\)\.then\(documents/);
  assert.match(source,/finally\(\(\) => \{ if \(!controller\.signal\.aborted\) setLoading\(false\)/);
  assert.doesNotMatch(source,/Promise\.allSettled/);
  assert.match(source,/if \(!controller\.signal\.aborted\) setScene\(generation\)/);
});

test('Studios narrow KLIC view constrains both sides instead of inheriting global mobile width', () => {
  const css = readFileSync('src/studios/studios-workspace.css','utf8');
  assert.match(css,/left:252px;right:20px;width:auto/);
  assert.match(css,/left:74px;right:10px/);
});
