import { REST_POINTER, type HologramPointer } from './hologramDynamics';

export type HologramInteractionMode = 'full' | 'click';

/** Local pointer physics only. No capture/preventDefault on touch or scrolling. */
export function bindHologramInteraction(target: HTMLElement, wake: () => void, options?:{onPress?:(pointer:HologramPointer)=>void;mode?:HologramInteractionMode}) {
  const pointer: HologramPointer = { ...REST_POINTER };
  const clickOptions={capture:true};
  let mode=options?.mode||'full';
  let lastTime = 0, down = false, startX = 0, startY = 0, dragged = false, releasedAt = -Infinity;
  const position = (event:PointerEvent|MouseEvent) => {
    const bounds=target.getBoundingClientRect();
    return {x:(event.clientX-bounds.left)/Math.max(1,bounds.width)*2-1,y:1-(event.clientY-bounds.top)/Math.max(1,bounds.height)*2};
  };
  const move = (event: PointerEvent) => {
    if(mode==='click')return;
    if (event.isPrimary === false || (event.pointerType === 'touch' && !down)) return;
    const bounds = target.getBoundingClientRect(), now = performance.now();
    const x = (event.clientX - bounds.left) / Math.max(1, bounds.width) * 2 - 1;
    const y = 1 - (event.clientY - bounds.top) / Math.max(1, bounds.height) * 2;
    const dt = Math.max(.008, Math.min(.1, (now - lastTime) / 1000));
    pointer.vx = pointer.active ? Math.max(-12, Math.min(12, (x - pointer.x) / dt)) : 0;
    pointer.vy = pointer.active ? Math.max(-12, Math.min(12, (y - pointer.y) / dt)) : 0;
    pointer.active = true; pointer.x = x; pointer.y = y; lastTime = now;
    if (down && Math.hypot(event.clientX - startX, event.clientY - startY) > 9) dragged = true;
    wake();
  };
  const press = (event: PointerEvent) => {
    if (event.isPrimary === false) return;
    down = true; dragged = false; startX = event.clientX; startY = event.clientY;
    if(mode==='full'){move(event);options?.onPress?.(pointer);}
  };
  const release = (event: PointerEvent) => {
    if (event.isPrimary === false) return;
    down = false; releasedAt = performance.now();
    if (event.pointerType !== 'mouse') pointer.active = false;
    pointer.vx = 0; pointer.vy = 0; wake();
  };
  const leave = () => { down = false; pointer.active = false; pointer.vx = 0; pointer.vy = 0; releasedAt = performance.now(); wake(); };
  const click = (event: MouseEvent) => {
    // Miniatures keep their ordinary click action and a brief particle response,
    // but never create a hover/drag force field or intercept navigation.
    if(mode==='click'){
      const at=event.detail===0?{x:0,y:0}:position(event);
      options?.onPress?.({...REST_POINTER,...at});wake();return;
    }
    // A deliberate shatter drag is not a request to start microphone capture.
    if (event.detail !== 0 && dragged && performance.now() - releasedAt < 800) { event.preventDefault(); event.stopPropagation(); }
  };
  target.addEventListener('pointerenter', move); target.addEventListener('pointermove', move);
  target.addEventListener('pointerdown', press); target.addEventListener('pointerup', release);
  target.addEventListener('pointerleave', leave); target.addEventListener('pointercancel', leave);
  target.addEventListener('click', click, clickOptions);
  return { pointer, decay(delta:number) {
    const decay = Math.exp(-Math.max(0, delta) * 18); pointer.vx *= decay; pointer.vy *= decay;
  }, reset() { Object.assign(pointer, REST_POINTER); down = false;dragged=false; },
  setMode(next:HologramInteractionMode){mode=next;Object.assign(pointer,REST_POINTER);down=false;dragged=false;wake();}, dispose() {
    target.removeEventListener('pointerenter', move); target.removeEventListener('pointermove', move);
    target.removeEventListener('pointerdown', press); target.removeEventListener('pointerup', release);
    target.removeEventListener('pointerleave', leave); target.removeEventListener('pointercancel', leave);
    target.removeEventListener('click', click, clickOptions);
  } };
}
