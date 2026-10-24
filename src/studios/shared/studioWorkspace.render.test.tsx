import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { StudioEditorFrame, StudioUtilityPanel, StudioKlicButton } from './StudioWorkspace';

test('integrated editor renders one preview, materials and timeline with accessible resize', () => {
  const html = renderToStaticMarkup(<StudioEditorFrame toolbar={<button>Salvar</button>} materials={<p>Materiais reais</p>} preview={<canvas/>} timeline={<p>Faixas editáveis</p>} pane="preview" onPaneChange={()=>{}}/>);
  assert.equal((html.match(/<canvas/g)||[]).length,1); assert.match(html,/Materiais reais/); assert.match(html,/Faixas editáveis/);
  assert.match(html,/role="separator"/); assert.match(html,/aria-label="Redimensionar timeline"/);
  assert.doesNotMatch(html,/aria-label="Propriedades da seleção"/);
});
test('selection adds the contextual inspector, without cloning the editing surface', () => {
  const html = renderToStaticMarkup(<StudioEditorFrame toolbar={null} materials={null} preview={<canvas/>} inspector={<input aria-label="Cor"/>} pane="properties" onPaneChange={()=>{}}/>);
  assert.match(html,/data-pane="properties"/); assert.match(html,/Propriedades da seleção/);
  assert.equal((html.match(/<canvas/g)||[]).length,1);
});
test('invalid mobile pane falls back to preview when selection disappears', () => {
  const html = renderToStaticMarkup(<StudioEditorFrame toolbar={null} materials={null} preview={<p>Projeto</p>} pane="properties" onPaneChange={()=>{}}/>);
  assert.match(html,/data-pane="preview"/); assert.doesNotMatch(html,/aria-label="Redimensionar timeline"/);
});
test('utility panels are closed initially and preserve a labeled nonmodal entry', () => {
  assert.equal(renderToStaticMarkup(<StudioUtilityPanel title="Histórico" open={false} onClose={()=>{}}>Versões</StudioUtilityPanel>),'');
  const html = renderToStaticMarkup(<StudioUtilityPanel title="Histórico" open onClose={()=>{}}>Versões</StudioUtilityPanel>);
  assert.match(html,/role="dialog"/); assert.match(html,/aria-modal="false"/); assert.match(html,/Fechar Histórico/); assert.match(html,/Versões/);
});
test('KLIC access reuses one button, not another conversation field', () => {
  const html = renderToStaticMarkup(<StudioKlicButton/>);
  assert.match(html,/KLIC/); assert.doesNotMatch(html,/textarea|input/);
  assert.match(html,/aria-controls="klic-floating-dialog"/); assert.match(html,/aria-expanded="false"/);
});
