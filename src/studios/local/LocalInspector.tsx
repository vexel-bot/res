import type { LocalLayer } from './localApi';
import { LocalSelect } from './LocalSelect';
import { LocalLayerControls } from './LocalLayerControls';

export function LocalInspector({ layer, locked, video, duration, patch, duplicate, remove, deselect }: {
  layer: LocalLayer; locked: boolean; video: boolean; duration: number;
  patch: (update: Partial<LocalLayer>, properties?: Partial<LocalLayer['properties']>) => void;
  duplicate: () => void; remove: () => void; deselect: () => void;
}) {
  return <div className="lp-context-properties">
    <div className="lp-context-heading"><h3>{layer.kind === 'text' ? 'Texto' : layer.kind === 'image' ? 'Imagem' : 'Forma'}</h3><button type="button" onClick={deselect}>Desmarcar</button></div>
    <fieldset disabled={locked || layer.locked}>
      <label>Nome<input value={layer.name} onChange={event => patch({ name: event.target.value })} /></label>
      {layer.kind === 'text' && <>
        <label>Texto<textarea value={layer.properties.text || ''} onChange={event => patch({}, { text: event.target.value })} /></label>
        <div className="lp-field-pair"><label>Tamanho<input type="number" min={8} max={240} value={layer.properties.fontSize || 48} onChange={event => patch({}, { fontSize: Number(event.target.value) })} /></label><label>Cor<input type="color" value={layer.properties.color || '#FFFFFF'} onChange={event => patch({}, { color: event.target.value })} /></label></div>
      </>}
      {layer.kind === 'shape' && <>
        <label>Preenchimento<input type="color" value={layer.properties.fill || '#FF7F50'} onChange={event => patch({}, { fill: event.target.value })} /></label>
        <LocalSelect value={layer.properties.shape || 'rectangle'} options={[{ value: 'rectangle', label: 'Retângulo' }, { value: 'ellipse', label: 'Elipse' }]} onChange={shape => patch({}, { shape: shape as 'rectangle' | 'ellipse' })} ariaLabel="Forma" disabled={locked || layer.locked} />
        <label>Cantos<input type="number" min={0} max={240} value={layer.properties.radius || 0} onChange={event => patch({}, { radius: Number(event.target.value) })} /></label>
      </>}
      {layer.kind === 'image' && <>
        {(['brightness', 'contrast', 'saturation'] as const).map(property => <label key={property}>{({ brightness: 'Brilho', contrast: 'Contraste', saturation: 'Saturação' })[property]}<input type="range" min={property === 'saturation' ? 0 : .25} max={2} step={.05} value={layer.properties[property] ?? 1} onChange={event => patch({}, { [property]: Number(event.target.value) })} /></label>)}
        <button type="button" onClick={() => patch({}, { crop: { x: .1, y: .1, width: .8, height: .8 } })}>Recortar 10% nas bordas</button>
        <button type="button" onClick={() => patch({}, { crop: null })}>Restaurar recorte original</button>
      </>}
      <details className="studio-fold"><summary>Posição e transformação</summary><div className="lp-field-pair">
        {(['x', 'y', 'width', 'height', 'rotation', 'opacity', 'zIndex'] as const).map(property => <label key={property}>{({ x: 'Posição X', y: 'Posição Y', width: 'Largura', height: 'Altura', rotation: 'Rotação', opacity: 'Opacidade', zIndex: 'Ordem' })[property]}<input type="number" step={property === 'opacity' ? .05 : 1} min={property === 'opacity' ? 0 : property === 'width' || property === 'height' ? 1 : undefined} max={property === 'opacity' ? 1 : undefined} value={layer[property]} onChange={event => patch({ [property]: Number(event.target.value) })} /></label>)}
      </div></details>
      {video && <details className="studio-fold" open><summary>Tempo e animação</summary>
        <div className="lp-field-pair"><label>Início (quadros)<input type="number" min={0} max={duration - 1} value={layer.properties.startFrame || 0} onChange={event => patch({}, { startFrame: Number(event.target.value) })} /></label><label>Duração (quadros)<input type="number" min={1} max={duration} value={layer.properties.durationFrames || duration} onChange={event => patch({}, { durationFrames: Number(event.target.value) })} /></label></div>
        <button type="button" onClick={() => patch({}, { keyframes: [{ property: 'x', frame: 0, value: -50 }, { property: 'x', frame: Math.min(24, layer.properties.durationFrames || duration), value: 0, easing: 'ease-out' }] })}>Animar entrada pela esquerda</button>
      </details>}
    </fieldset>
    <details className="studio-fold"><summary>{video ? 'Acabamento e keyframes' : 'Acabamento e tipografia'}</summary>
      <LocalLayerControls layer={layer} disabled={locked} video={video} duration={duration} patch={patch} duplicate={duplicate} />
    </details>
    {layer.locked && <p>Esta camada está bloqueada no projeto.</p>}
    <button type="button" disabled={locked || layer.locked} onClick={remove}>Remover elemento</button>
  </div>;
}
