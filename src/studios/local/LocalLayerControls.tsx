import type { LocalLayer, LocalKey } from './localApi';
import { LocalSelect } from './LocalSelect';

export function LocalLayerControls({ layer, disabled, video, duration, patch, duplicate }: {
    layer: LocalLayer; disabled: boolean; video: boolean; duration: number;
    patch: (update: Partial<LocalLayer>, style?: Partial<LocalLayer['properties']>) => void;
    duplicate: () => void;
}) {
    const keys = layer.properties.keyframes || [];
    function updateKey(index: number, update: Partial<LocalKey>) {
        patch({}, { keyframes: keys.map((key, i) => i === index ? { ...key, ...update } : key) });
    }
    return <section className="lp-layer-tools" aria-label="Controles do elemento selecionado">
        <h3>{layer.name} · acabamento e animação</h3>
        <fieldset disabled={disabled || layer.locked}>
            <button type="button" onClick={duplicate}>Duplicar elemento</button>
            <label>Sombra suave<LocalSelect ariaLabel="Sombra suave" value={layer.properties.shadow ? 'yes' : 'no'}
                options={[{value:'no',label:'Sem sombra'},{value:'yes',label:'Sombra local 2D'}]}
                onChange={value => patch({}, {shadow:value === 'yes'})}/></label>
            {layer.kind === 'text' && <>
                <label>Peso da fonte do sistema<LocalSelect ariaLabel="Peso da fonte" value={String(layer.properties.fontWeight || 700)}
                    options={[{value:'400',label:'Regular'},{value:'700',label:'Negrito'}]}
                    onChange={value => patch({}, {fontFamily:'system',fontWeight:Number(value) as 400 | 700})}/></label>
                <label>Alinhamento<LocalSelect ariaLabel="Alinhamento do texto" value={layer.properties.align || 'left'}
                    options={[{value:'left',label:'Esquerda'},{value:'center',label:'Centro'},{value:'right',label:'Direita'}]}
                    onChange={value => patch({}, {align:value as 'left' | 'center' | 'right'})}/></label>
                {video && <><label>Entrada do texto<LocalSelect ariaLabel="Revelação do texto" value={layer.properties.textReveal || 'all'}
                    options={[{value:'all',label:'Texto completo'},{value:'words',label:'Palavra por palavra'}]}
                    onChange={value => patch({}, {textReveal:value as 'all' | 'words'})}/></label>
                    {layer.properties.textReveal === 'words' && <label>Intervalo por palavra (quadros)<input type="number" min={1} max={120}
                        value={layer.properties.wordStaggerFrames || 6} onChange={event => patch({}, {wordStaggerFrames:Number(event.target.value)})}/></label>}</>}
            </>}
            {layer.kind === 'shape' && <label>Final do gradiente<input type="color" value={layer.properties.gradientEnd || layer.properties.fill || '#FF7F50'}
                onChange={event => patch({}, {gradientEnd:event.target.value})}/><button onClick={() => patch({}, {gradientEnd:null})}>Remover gradiente</button></label>}
            {video && <details className="lp-key-editor"><summary>Editar keyframes · {keys.length}/32</summary>
                {keys.map((key,index) => <div className="lp-key-row" key={index}>
                    <label>Propriedade<LocalSelect ariaLabel={`Propriedade do keyframe ${index+1}`} value={key.property}
                        options={['x','y','scale','rotation','opacity'].map(value => ({value,label:value}))}
                        onChange={value => updateKey(index,{property:value as LocalKey['property']})}/></label>
                    <label>Quadro<input type="number" min={0} max={layer.properties.durationFrames || duration} value={key.frame} onChange={event => updateKey(index,{frame:Number(event.target.value)})}/></label>
                    <label>Valor<input type="number" step={.05} value={key.value} onChange={event => updateKey(index,{value:Number(event.target.value)})}/></label>
                    <label>Curva<LocalSelect ariaLabel={`Curva do keyframe ${index+1}`} value={key.easing || 'linear'}
                        options={[{value:'linear',label:'Linear'},{value:'ease-out',label:'Desacelerar'},{value:'ease-in-out',label:'Suave'}]}
                        onChange={value => updateKey(index,{easing:value as LocalKey['easing']})}/></label>
                    <button aria-label={`Remover keyframe ${index+1}`} onClick={() => patch({}, {keyframes:keys.filter((_,i)=>i!==index)})}>Remover</button>
                </div>)}
                <button disabled={keys.length >= 32} onClick={() => {
                    const last = layer.properties.durationFrames || duration;
                    const frame = Array.from({length:last+1},(_,i)=>i).find(frame=>!keys.some(key=>key.property==='x'&&key.frame===frame));
                    if(frame !== undefined) patch({}, {keyframes:[...keys,{property:'x',frame,value:0,easing:'ease-in-out'}]});
                }}>Adicionar keyframe X</button>
            </details>}
        </fieldset>
    </section>;
}
