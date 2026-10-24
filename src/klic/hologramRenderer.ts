import { HologramLoop, hologramBudget, hologramPresentation, hologramPointColor, HOLOGRAM_MIN_PARTICLES,
  QUIET_RESONANCE, type HologramFrame, type HologramTheme, type HologramResonance } from './hologramModel';
import { KlicFaceSimulation } from './face/faceSimulation';
import { observePlasma } from './plasmaVisibility';
import { HologramCommunication, REST_POINTER, SILENT_AUDIO, type HologramPointer, type KlicAudioSignal } from './hologramDynamics';
import { bindHologramInteraction, type HologramInteractionMode } from './hologramInteraction';
import type { KlicPlasmaState } from './plasmaState';

type FaceFrame = { left:number; top:number; width:number; height:number };
type Viewport = { width:number; height:number; ratio:number; frame?:FaceFrame };
export type FaceSurface = 'local' | 'viewport';
export type FaceBackground = 'black' | 'transparent';
export type FaceMetrics = { drawMs:number; frameMs:number; particles:number };

/** Native Canvas 2D only: one context, one model, manual perspective and exact Z-sort. */
export function createCanvasFace(canvas:HTMLCanvasElement, count:number, background:FaceBackground='black') {
  const context=canvas.getContext('2d',{alpha:background==='transparent'});
  if(!context) return;
  const model=new KlicFaceSimulation(count);
  let shade=NaN, previousGlow=NaN, palette:number[][]=[];
  let image:ImageData | undefined, packed:Uint32Array | undefined;
  let painted:FaceFrame | undefined, backingWidth=0,backingHeight=0;
  let disposed=false;
  return { model,
    render(frame:HologramFrame,view:Viewport,count:number,voice:HologramResonance=QUIET_RESONANCE,pointer:HologramPointer=REST_POINTER) {
      if(disposed)return;
      // The projection belongs to the original sphere, not the drawing surface.
      // A viewport canvas lets displaced points leave every clipped chat ancestor.
      const anchor=view.frame||{left:0,top:0,width:view.width,height:view.height};
      model.step(frame.time,frame.delta||0,voice,pointer,anchor.width/anchor.height,frame.reduced,count);
      const scale=Math.min(anchor.width,anchor.height)/2,pointScale=Math.min(1,Math.max(.5,scale/180));
      const centerX=anchor.left+anchor.width/2,centerY=anchor.top+anchor.height/2;
      const limit=Math.min(count,model.particles.length);
      let left=0,top=0,width=canvas.width,height=canvas.height;
      if(view.frame){
        // Upload only the live particle bounds, never a fixed sphere-sized crop.
        // The transparent canvas itself still covers the entire viewport.
        let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
        for(let i=0;i<limit;i++){
          const x=(centerX+model.screenX[i]*scale*2)*view.ratio,y=(centerY+model.screenY[i]*scale*2)*view.ratio;
          const radius=model.radii[i]*pointScale*view.ratio+2;
          minX=Math.min(minX,x-radius);maxX=Math.max(maxX,x+radius);
          minY=Math.min(minY,y-radius);maxY=Math.max(maxY,y+radius);
        }
        left=Math.max(0,Math.min(canvas.width-1,Math.floor(minX)));
        top=Math.max(0,Math.min(canvas.height-1,Math.floor(minY)));
        width=Math.max(1,Math.min(canvas.width-left,Math.ceil(maxX)-left+1));
        height=Math.max(1,Math.min(canvas.height-top,Math.ceil(maxY)-top+1));
      }
      const resized=backingWidth!==canvas.width||backingHeight!==canvas.height;
      if(!image||resized||image.width<width||image.height<height){
        const w=view.frame?Math.min(canvas.width,Math.max(image&&!resized?image.width:0,Math.ceil(width/32)*32)):width;
        const h=view.frame?Math.min(canvas.height,Math.max(image&&!resized?image.height:0,Math.ceil(height/32)*32)):height;
        image=context.createImageData(w,h);
        packed=new Uint32Array(image.data.buffer);
      }
      backingWidth=canvas.width;backingHeight=canvas.height;
      // Rasterize crisp subpixel dots into one reusable surface, then upload once.
      // This avoids 5,000–7,200 beginPath/arc/fill/state changes on every frame.
      packed!.fill(background==='black'?0xff000000:0);
      const presentation=hologramPresentation(frame.light);
      const voiceGlow=Math.round(voice.energy*(voice.listening*15+voice.speaking*35));
      if(shade!==presentation.shade||voiceGlow!==previousGlow){
        shade=presentation.shade;
        previousGlow=voiceGlow;
        palette=Array.from({length:32},(_,i)=>hologramPointColor(i/31,shade)
          .map((value,axis)=>Math.min(255,value+voiceGlow*(axis===0?1:axis===1?.8:0)*shade)));
      }
      for(let n=0;n<limit;n++) {
        const i=model.order[n];
        const x=centerX+model.screenX[i]*scale*2,y=centerY+model.screenY[i]*scale*2;
        const color=palette[Math.min(31,Math.max(0,Math.round(model.fronts[i]*31)))];
        rasterizeFaceDot(image.data,image.width,image.height,x*view.ratio-left,y*view.ratio-top,
          model.radii[i]*pointScale*view.ratio,color,model.opacities[i]*presentation.opacity);
      }
      if(view.frame&&painted)context.clearRect(painted.left,painted.top,painted.width,painted.height);
      context.putImageData(image,left,top);
      painted={left,top,width:image.width,height:image.height};
    },
    dispose(){if(disposed)return;disposed=true;model.reset();image=undefined;packed=undefined;context.clearRect(0,0,canvas.width,canvas.height);},
  };
}

/** Source-over compositing with analytic edge coverage, no blur/filter or image sequence. */
export function rasterizeFaceDot(pixels:Uint8ClampedArray,width:number,height:number,x:number,y:number,radius:number,color:number[],opacity:number) {
  const left=Math.max(0,Math.floor(x-radius-.5)),right=Math.min(width-1,Math.ceil(x+radius+.5));
  const top=Math.max(0,Math.floor(y-radius-.5)),bottom=Math.min(height-1,Math.ceil(y+radius+.5));
  for(let py=top;py<=bottom;py++)for(let px=left;px<=right;px++){
    const dx=px+.5-x,dy=py+.5-y;
    const coverage=Math.min(1,Math.max(0,radius+.5-Math.sqrt(dx*dx+dy*dy)));
    const alpha=opacity*coverage;
    if(alpha<=0)continue;
    const k=(py*width+px)*4,previous=pixels[k+3]/255,remaining=previous*(1-alpha),combined=alpha+remaining;
    pixels[k]=(color[0]*alpha+pixels[k]*remaining)/combined;
    pixels[k+1]=(color[1]*alpha+pixels[k+1]*remaining)/combined;
    pixels[k+2]=(color[2]*alpha+pixels[k+2]*remaining)/combined;
    pixels[k+3]=combined*255;
  }
}

export function mountKlicHologram(host:HTMLSpanElement,canvas:HTMLCanvasElement,theme:HologramTheme,
  options?:{signal?:()=>KlicAudioSignal;background?:FaceBackground;compact?:boolean;interaction?:HologramInteractionMode;surface?:FaceSurface;onMetrics?:(metrics:FaceMetrics)=>void}) {
  const device=navigator as Navigator & {deviceMemory?:number;connection?:{saveData?:boolean}};
  let count=Math.min(7200,hologramBudget(device.hardwareConcurrency,device.deviceMemory,device.connection?.saveData));
  if(options?.compact)count=host.getBoundingClientRect().width<42?288:1152;
  const sink=createCanvasFace(canvas,count,options?.background ?? 'black'), communication=new HologramCommunication();
  if(sink)count=Math.min(count,sink.model.particles.length);
  let state:KlicPlasmaState='idle',maxDpr=2,visible=false,active=true,contextLost=false,disposed=false;
  let view:Viewport={width:1,height:1,ratio:1};
  let lastDraw=0,samples=0,slow=0,drawTotal=0,frameTotal=0;
  let elapsed=0,lastPaint=0;
  let interaction:ReturnType<typeof bindHologramInteraction> | undefined;
  const viewportSurface=options?.surface==='viewport';
  const followAnchor=()=>{
    if(!viewportSurface)return;
    const rect=host.getBoundingClientRect();
    view.frame={left:rect.left,top:rect.top,width:Math.max(1,rect.width),height:Math.max(1,rect.height)};
  };
  host.dataset.renderer=sink?'canvas2d':'unavailable';host.dataset.particles=String(count);
  const loop=new HologramLoop({now:()=>performance.now(),request:callback=>requestAnimationFrame(callback),cancel:id=>cancelAnimationFrame(id),draw:frame=>{
    if(!sink||contextLost)return;
    const start=performance.now();
    followAnchor();
    elapsed+=frame.delta||0;
    if(options?.compact&&!frame.reduced&&lastPaint&&start-lastPaint<32)return;
    lastPaint=start;
    const delta=elapsed;elapsed=0;
    const voice=communication.step(state,options?.signal?.()||SILENT_AUDIO,delta||1/60,start,frame.reduced);
    if(frame.reduced)voice.energy=0;
    sink.render({...frame,delta},view,count,voice,interaction?.pointer||REST_POINTER);
    interaction?.decay(delta);
    const end=performance.now(), interval=lastDraw?start-lastDraw:0;lastDraw=start;
    if(interval>0&&interval<150&&!frame.reduced){
      samples++;drawTotal+=end-start;frameTotal+=interval;if(interval>(options?.compact?45:25))slow++;
      if(samples>=120){
        options?.onMetrics?.({drawMs:drawTotal/samples,frameMs:frameTotal/samples,particles:count});
        if(slow>60){
          if(!options?.compact&&count>HOLOGRAM_MIN_PARTICLES){count=Math.max(HOLOGRAM_MIN_PARTICLES,Math.floor(count*.8/72)*72);host.dataset.particles=String(count);}
          else if(maxDpr>1){maxDpr=Math.max(1,maxDpr-.25);resize();}
        }
        samples=0;slow=0;drawTotal=0;frameTotal=0;
      }
    }
  }},theme);
  const resize=()=>{
    const rect=host.getBoundingClientRect();
    const width=Math.max(1,viewportSurface?window.innerWidth:rect.width),height=Math.max(1,viewportSurface?window.innerHeight:rect.height);
    const ratio=Math.min(maxDpr,window.devicePixelRatio||1,2048/Math.max(width,height));
    view={width,height,ratio};
    followAnchor();
    const w=Math.max(1,Math.round(width*ratio)),h=Math.max(1,Math.round(height*ratio));
    if(canvas.width!==w)canvas.width=w;if(canvas.height!==h)canvas.height=h;
    loop.invalidate();
  };
  resize();
  interaction=bindHologramInteraction(host.closest<HTMLElement>('.klic-plasma')||host,()=>loop.invalidate(),{
    mode:options?.interaction||(options?.compact?'click':'full'),
    onPress:pointer=>{if(!media.matches)sink?.model.burst(pointer);},
  });
  const observer=new ResizeObserver(resize);observer.observe(host);
  if(viewportSurface){
    window.addEventListener('resize',resize);
    window.addEventListener('scroll',resize,true);
    window.visualViewport?.addEventListener('resize',resize);
    window.visualViewport?.addEventListener('scroll',resize);
  }
  const media=matchMedia('(prefers-reduced-motion: reduce)');
  const motion=()=>{sink?.model.reset();interaction?.reset();loop.setReducedMotion(media.matches);};
  motion();media.addEventListener('change',motion);
  const syncVisibility=()=>{
    lastDraw=0;lastPaint=0;elapsed=0;samples=0;slow=0;drawTotal=0;frameTotal=0;
    if(!visible||!active)interaction?.reset();
    loop.setVisible(visible&&active&&!contextLost&&!!sink);
  };
  const stopObserving=observePlasma(host,next=>{visible=next;syncVisibility();});
  const lost=(event:Event)=>{event.preventDefault();contextLost=true;loop.setVisible(false);};
  const restored=()=>{if(disposed)return;contextLost=false;resize();syncVisibility();};
  canvas.addEventListener('contextlost',lost);canvas.addEventListener('contextrestored',restored);
  return {setTheme(next:HologramTheme){loop.setTheme(next);},setState(next:KlicPlasmaState){state=next;loop.invalidate();},
    setInteraction(next:HologramInteractionMode){interaction?.setMode(next);},
    setActive(next:boolean){active=next;syncVisibility();},dispose(){
      if(disposed)return;disposed=true;loop.dispose();stopObserving();observer.disconnect();media.removeEventListener('change',motion);
      if(viewportSurface){
        window.removeEventListener('resize',resize);
        window.removeEventListener('scroll',resize,true);
        window.visualViewport?.removeEventListener('resize',resize);
        window.visualViewport?.removeEventListener('scroll',resize);
      }
      interaction?.dispose();canvas.removeEventListener('contextlost',lost);canvas.removeEventListener('contextrestored',restored);sink?.dispose();
      delete host.dataset.renderer;delete host.dataset.particles;
    }};
}
