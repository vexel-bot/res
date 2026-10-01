import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {Composition, Img, OffthreadVideo, Sequence, cancelRender, continueRender, delayRender, registerRoot, staticFile, useCurrentFrame} from 'remotion';

type Key = {frame:number; value:number; easing:string; cubicBezier?:number[]};
type Native = {component:'action_montage'|'product_demonstration'|'integrated_typography'|'gesture_occlusion_reveal'|'moving_variant_mask'; version:1;
  entranceFrames:number; travelRatio:number; revealAxis:'horizontal'|'vertical'; staggerFrames:number; continuityKey?:string;
  baseTargetId?:string; occluderTargetId?:string; switchFrame:number; maskStartX:number; maskStartY:number;
  maskEndX:number; maskEndY:number; maskRadius:number};
type Layer = {id:string; name?:string; kind:'video'|'image'|'shape'|'text'|'group'; x:number; y:number;
  width:number; height:number; rotation:number; opacity:number; zIndex:number; visible:boolean; properties:Record<string,any>};
type Manifest = {schemaVersion:string; width:number; height:number; fps:number; durationFrames:number; background:string;
  layers:Layer[]; assets:Record<string,string>; fonts:{assetId:string;family:string;weight:number}[];
  nodes:{nodeId:string;targetLayerId:string;parentNodeId?:string;transformOriginX?:number;transformOriginY?:number}[];
  tracks:{targetLayerId:string;propertyPath:string;keyframes:Key[]}[];
  transitions:{kind:string;fromLayerId:string;toLayerId:string;startFrame:number;endFrameExclusive:number}[]};
const clamp=(x:number)=>Math.max(0,Math.min(1,x));
function valueAt(keys:Key[],frame:number):number {
  if(frame<=keys[0].frame)return keys[0].value;
  for(let i=0;i<keys.length-1;i++){
    const a=keys[i],b=keys[i+1];
    if(frame>b.frame)continue;
    let p=clamp((frame-a.frame)/(b.frame-a.frame));
    if(a.easing==='hold')p=0;
    else if(a.easing==='ease_in')p*=p;
    else if(a.easing==='ease_out')p=1-(1-p)**2;
    else if(a.easing==='ease_in_out')p=p<.5?2*p*p:1-(-2*p+2)**2/2;
    else if(a.easing==='cubic_bezier'&&a.cubicBezier){
      const [x1,y1,x2,y2]=a.cubicBezier;
      const curve=(t:number,u:number,v:number)=>3*(1-t)**2*t*u+3*(1-t)*t*t*v+t**3;
      let low=0,high=1;
      for(let n=0;n<18;n++){const m=(low+high)/2;if(curve(m,x1,x2)<p)low=m;else high=m;}
      p=curve((low+high)/2,y1,y2);
    }
    return a.value+(b.value-a.value)*p;
  }
  return keys.at(-1)!.value;
}
const progress=(frame:number,duration:number)=>1-(1-clamp(frame/Math.max(1,duration)))**3;

export function ActionMontage({src,start,duration,offset,rate,fps,fit}:{src:string;start:number;duration:number;offset:number;rate:number;fps:number;fit:any}) {
  return <Sequence from={start} durationInFrames={duration} layout="none">
    <OffthreadVideo src={src} muted trimBefore={Math.round(offset*fps)} playbackRate={rate}
      style={{width:'100%',height:'100%',objectFit:fit}} />
  </Sequence>;
}
export function ProductDemonstration({children,frame,spec}:{children:React.ReactNode;frame:number;spec:Native}) {
  const t=progress(frame,spec.entranceFrames);
  const inset=spec.revealAxis==='vertical'?`inset(${(1-t)*100}% 0 0 0)`:`inset(0 ${(1-t)*100}% 0 0)`;
  return <div style={{width:'100%',height:'100%',clipPath:inset}}>{children}</div>;
}
export function IntegratedTypography({text,frame,spec}:{text:string;frame:number;spec:Native}) {
  return <>{text.split(/(\s+)/u).map((word,index)=>/^\s+$/u.test(word)?word:
    <span key={index} style={{display:'inline-block',opacity:progress(frame-Math.floor(index/2)*spec.staggerFrames,spec.entranceFrames),
      transform:`translateY(${(1-progress(frame-Math.floor(index/2)*spec.staggerFrames,spec.entranceFrames))*spec.travelRatio*100}%)`}}>{word}</span>)}</>;
}

export function GestureOcclusionReveal({children,frame,spec}:{children:React.ReactNode;frame:number;spec:Native}) {
  const covered=progress(frame-spec.switchFrame,spec.entranceFrames);
  const edge=spec.revealAxis==='vertical'?spec.maskStartY+(spec.maskEndY-spec.maskStartY)*covered:
    spec.maskStartX+(spec.maskEndX-spec.maskStartX)*covered;
  const clip=frame<spec.switchFrame?'inset(100%)':spec.revealAxis==='vertical'?`inset(0 0 ${(1-edge)*100}% 0)`:
    `inset(0 ${(1-edge)*100}% 0 0)`;
  return <div style={{width:'100%',height:'100%',clipPath:clip}}>{children}</div>;
}

export function MovingVariantMask({children,frame,spec}:{children:React.ReactNode;frame:number;spec:Native}) {
  const t=progress(frame-spec.switchFrame,spec.entranceFrames);
  const x=(spec.maskStartX+(spec.maskEndX-spec.maskStartX)*t)*100;
  const y=(spec.maskStartY+(spec.maskEndY-spec.maskStartY)*t)*100;
  return <div style={{width:'100%',height:'100%',clipPath:frame<spec.switchFrame?'inset(100%)':
    `circle(${spec.maskRadius*100}% at ${x}% ${y}%)`}}>{children}</div>;
}

function Hybrid({manifest:m}:{manifest:Manifest}) {
  const frame=useCurrentFrame();
  const stage=useRef<HTMLDivElement>(null);
  const [handle]=useState(()=>delayRender('hybrid-fonts'));
  const [ready,setReady]=useState(false);
  useEffect(()=>{
    Promise.all(m.fonts.map(async f=>{
      const font=new FontFace(f.family,`url(${staticFile(m.assets[f.assetId])})`,{weight:String(f.weight)});
      await font.load();(document.fonts as FontFaceSet & {add(font:FontFace):void}).add(font);
    })).then(()=>{setReady(true);continueRender(handle);}).catch(cancelRender);
  },[m,handle]);
  useLayoutEffect(()=>{
    if(!ready||!stage.current)return;
    const root=stage.current.getBoundingClientRect();
    const sx=m.width/root.width,sy=m.height/root.height;
    const elements=Array.from(stage.current.querySelectorAll<HTMLElement>('[data-layer-id]')).map(el=>{
      const box=el.getBoundingClientRect();let opacity=1;let cursor:HTMLElement|null=el;
      while(cursor&&cursor!==stage.current){opacity*=Number(getComputedStyle(cursor).opacity);cursor=cursor.parentElement;}
      const layer=m.layers.find(l=>l.id===el.dataset.layerId)!;
      const timing=layer.properties.editorialTiming;
      const present=!timing||(frame>=timing.startFrame&&frame<timing.startFrame+timing.durationFrames);
      const native=layer.properties.nativeComponent as Native|undefined;
      const local=frame-(timing?.startFrame??0);
      const maskProgress=native?.component==='moving_variant_mask'?progress(local-native.switchFrame,native.entranceFrames):undefined;
      return {layerId:layer.id,semanticId:layer.name||layer.id,present,visible:present&&opacity>.01,opacity,
        bounds:{x:(box.x-root.x)*sx,y:(box.y-root.y)*sy,width:box.width*sx,height:box.height*sy},
        ...(maskProgress!==undefined?{nativeMask:{centerX:native!.maskStartX+(native!.maskEndX-native!.maskStartX)*maskProgress,
          centerY:native!.maskStartY+(native!.maskEndY-native!.maskStartY)*maskProgress,radius:native!.maskRadius}}:{}),
        ...(native?.component==='gesture_occlusion_reveal'?{nativeReveal:progress(local-native.switchFrame,native.entranceFrames)}:{}),
        ...(layer.kind==='video'?{sourceTimeSeconds:layer.properties.sourceStartSeconds+
          (frame-timing.startFrame)/m.fps*(layer.properties.playbackRate??1),sourceTimeBasis:'timeline_mapping'}:{})};
    });
    console.log('RES_GEOMETRY:'+JSON.stringify({frame,elements}));
  },[frame,ready,m]);
  const nodeToLayer=new Map(m.nodes.map(n=>[n.nodeId,n.targetLayerId]));
  const children=new Map<string,Layer[]>();
  for(const layer of m.layers){
    const n=m.nodes.find(n=>n.targetLayerId===layer.id);
    const parent=n?.parentNodeId?nodeToLayer.get(n.parentNodeId):'root';
    const bucket=children.get(parent??'root')??[];bucket.push(layer);children.set(parent??'root',bucket);
  }
  for(const bucket of children.values())bucket.sort((a,b)=>a.zIndex-b.zIndex);
  const draw=(layer:Layer):React.ReactNode=>{
    const p=layer.properties,timing=p.editorialTiming;
    const start=timing?.startFrame??0,duration=timing?.durationFrames??m.durationFrames,local=frame-start;
    const v=Object.fromEntries(m.tracks.filter(t=>t.targetLayerId===layer.id).map(t=>[t.propertyPath,valueAt(t.keyframes,frame)]));
    const active=local>=0&&local<duration&&layer.visible;
    let opacity=active?(v.opacity??layer.opacity):0,clipPath: string|undefined;
    for(const t of m.transitions){
      const part=clamp((frame-t.startFrame)/Math.max(1,t.endFrameExclusive-t.startFrame));
      if(t.fromLayerId===layer.id&&frame>=t.startFrame)opacity*=t.kind==='hard_cut'?0:1-part;
      if(t.toLayerId===layer.id){
        if(frame<t.startFrame)opacity=0;
        else if(t.kind==='dissolve')opacity*=part;
        else if(t.kind==='wipe')clipPath=`inset(0 ${(1-part)*100}% 0 0)`;
      }
    }
    const native=p.nativeComponent as Native|undefined;
    const occluderLayer=m.layers.find(candidate=>candidate.properties.editorialSceneId===p.editorialSceneId&&
      (candidate.properties.nativeComponent as Native|undefined)?.component==='gesture_occlusion_reveal'&&
      (candidate.properties.nativeComponent as Native).occluderTargetId===layer.name);
    const occluderSpec=occluderLayer?.properties.nativeComponent as Native|undefined;
    const occluderFrame=frame-(occluderLayer?.properties.editorialTiming?.startFrame??0);
    const occluderProgress=occluderSpec?progress(occluderFrame-occluderSpec.switchFrame,occluderSpec.entranceFrames):0;
    const occluderX=occluderSpec?(occluderSpec.maskStartX+(occluderSpec.maskEndX-occluderSpec.maskStartX)*occluderProgress)*m.width-
      (layer.x+layer.width/2):0;
    const occluderY=occluderSpec?(occluderSpec.maskStartY+(occluderSpec.maskEndY-occluderSpec.maskStartY)*occluderProgress)*m.height-
      (layer.y+layer.height/2):0;
    const n=m.nodes.find(n=>n.targetLayerId===layer.id);
    const blur=v['filters.blurPx']??p.editorialDepth?.blurPx??0;
    const shadow=p.editorialShadow;
    const mask=p.maskAssetId?`url(${staticFile(m.assets[p.maskAssetId])})`:undefined;
    const style:React.CSSProperties={position:'absolute',left:layer.x,top:layer.y,width:layer.width,height:layer.height,
      opacity,zIndex:layer.zIndex,clipPath,transformOrigin:`${(n?.transformOriginX??.5)*100}% ${(n?.transformOriginY??.5)*100}%`,
      transform:`translate(${(v['position.x']??0)+occluderX}px,${(v['position.y']??0)+occluderY}px) rotate(${v['rotation.degrees']??layer.rotation}deg) scale(${v['scale.x']??1},${v['scale.y']??1})`,
      filter:`blur(${blur}px)${shadow?` drop-shadow(${shadow.offset_x??shadow.offsetX??0}px ${shadow.offset_y??shadow.offsetY??0}px ${shadow.blur_px??shadow.blurPx??0}px ${shadow.color??'#000000'})`:''}`,
      mixBlendMode:p.editorialBlendMode??'normal',maskImage:mask,maskSize:'100% 100%',maskMode:'luminance',
      border:p.editorialBorder?.width?`${p.editorialBorder.width}px solid ${p.editorialBorder.color}`:undefined,boxSizing:'border-box'};
    let content:React.ReactNode;
    if(layer.kind==='group')content=children.get(layer.id)?.map(draw);
    else if(layer.kind==='video')content=<ActionMontage src={staticFile(m.assets[p.assetId])} start={start} duration={duration}
      offset={p.sourceStartSeconds??0} rate={p.playbackRate??1} fps={m.fps} fit={p.objectFit??'contain'}/>;
    else if(layer.kind==='image')content=<Img src={staticFile(m.assets[p.assetId])} style={{width:'100%',height:'100%',objectFit:p.objectFit??'contain'}}/>;
    else if(layer.kind==='shape'&&p.editorialPath){
      const points=p.editorialPath.points;
      const d=p.editorialPath.mode==='quadratic'?`M ${points[0].x} ${points[0].y} Q ${points[1].x} ${points[1].y} ${points[2].x} ${points[2].y}`:
        points.map((pt:any,i:number)=>`${i?'L':'M'} ${pt.x} ${pt.y}`).join(' ');
      content=<svg width="100%" height="100%" viewBox={`0 0 ${layer.width} ${layer.height}`} style={{overflow:'visible'}}>
        <path d={d} fill="none" stroke={p.color} strokeWidth={p.editorialPath.strokeWidth} pathLength={1} strokeDasharray="1"
          strokeDashoffset={timing?.reveal==='path'?1-clamp(local/(timing.revealFrames??12)):0}/></svg>;
    }else if(layer.kind==='shape')content=<div style={{width:'100%',height:'100%',background:p.fill,borderRadius:p.shape==='ellipse'?'50%':p.borderRadius}}/>;
    else{
      content=<div style={{width:'100%',height:'100%',fontFamily:p.fontFamily??'Arial',fontSize:v['fontSize.px']??p.fontSize,
        fontWeight:v.fontWeight??p.fontWeight,lineHeight:v['lineHeight.ratio']??p.lineHeight,letterSpacing:v['letterSpacing.px']??p.letterSpacing,
        color:p.color,textAlign:p.textAlign,whiteSpace:'pre-wrap'}}>
        {native?.component==='integrated_typography'?<IntegratedTypography text={p.text} frame={local} spec={native}/>:
          timing?.reveal==='words'?String(p.text).split(/\s+/u).slice(0,Math.ceil(clamp(local/(timing.revealFrames??12))*String(p.text).split(/\s+/u).length)).join(' '):p.text}
      </div>;
    }
    if(native?.component==='product_demonstration')content=<ProductDemonstration frame={local} spec={native}>{content}</ProductDemonstration>;
    else if(native?.component==='gesture_occlusion_reveal')content=<GestureOcclusionReveal frame={local} spec={native}>{content}</GestureOcclusionReveal>;
    else if(native?.component==='moving_variant_mask')content=<MovingVariantMask frame={local} spec={native}>{content}</MovingVariantMask>;
    else if(timing?.reveal==='wipe')content=<div style={{width:'100%',height:'100%',clipPath:`inset(0 ${(1-clamp(local/(timing.revealFrames??12)))*100}% 0 0)`}}>{content}</div>;
    return <div key={layer.id} data-layer-id={layer.id} style={style}>{content}</div>;
  };
  return <div ref={stage} style={{position:'absolute',inset:0,overflow:'hidden',background:m.background}}>{children.get('root')?.map(draw)}</div>;
}
const defaults:Manifest={schemaVersion:'res.remotion-native-composition.v2',width:720,height:1280,fps:30,durationFrames:450,
  background:'#101010',layers:[],assets:{},fonts:[],nodes:[],tracks:[],transitions:[]};
registerRoot(()=> <Composition id="ResHybrid" component={Hybrid} width={720} height={1280} fps={30} durationInFrames={450}
  defaultProps={{manifest:defaults}} calculateMetadata={({props})=>({width:props.manifest.width,height:props.manifest.height,
    fps:props.manifest.fps,durationInFrames:props.manifest.durationFrames})}/>);
