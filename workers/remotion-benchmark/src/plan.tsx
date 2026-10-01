import React, {useEffect, useState} from 'react';
import {Composition, Img, cancelRender, continueRender, delayRender, registerRoot, useCurrentFrame} from 'remotion';

type Key = {frame: number; value: number; easing: string; cubicBezier?: number[]};
type Track = {targetLayerId: string; propertyPath: string; keyframes: Key[]};
type Transition = {kind: 'hard_cut' | 'dissolve'; fromLayerId: string; toLayerId: string; startFrame: number; endFrameExclusive: number};
type Layer = {id: string; kind: 'text' | 'shape' | 'image' | 'group'; x: number; y: number; width: number; height: number;
  rotation: number; opacity: number; zIndex: number; visible: boolean; properties: Record<string, any>};
type Manifest = {width: number; height: number; fps: number; durationFrames: number; background: string; layers: Layer[];
  nodes: {nodeId: string; targetLayerId: string; parentNodeId?: string}[]; tracks: Track[]; transitions: Transition[];
  assets: Record<string, string>; fonts: {assetId: string; family: string; weight: number | string}[]};

function bezier(key: Key, progress: number): number {
  const c = key.cubicBezier;
  if (!c) return progress;
  const curve = (t: number, a: number, b: number) => 3 * (1-t)**2*t*a + 3*(1-t)*t*t*b + t**3;
  let low=0, high=1;
  for (let i=0;i<18;i++) {const mid=(low+high)/2; if(curve(mid,c[0],c[2])<progress)low=mid;else high=mid;}
  return curve((low+high)/2,c[1],c[3]);
}
function valueAt(keys: Key[], frame: number): number {
  if(frame<=keys[0].frame)return keys[0].value;
  for(let i=0;i<keys.length-1;i++){
    const a=keys[i],b=keys[i+1];
    if(frame<=b.frame){
      let p=(frame-a.frame)/(b.frame-a.frame);
      if(a.easing==='hold')p=0;
      else if(a.easing==='ease_in')p=p*p;
      else if(a.easing==='ease_out')p=1-(1-p)**2;
      else if(a.easing==='ease_in_out')p=p<.5?2*p*p:1-(-2*p+2)**2/2;
      else if(a.easing==='cubic_bezier')p=bezier(a,p);
      return a.value+(b.value-a.value)*p;
    }
  }
  return keys[keys.length-1].value;
}
function color(raw: unknown, fallback: string): string {return typeof raw==='string'&&/^#[0-9a-fA-F]{6}$/.test(raw)?raw:fallback;}
function num(raw: unknown, fallback: number): number {return typeof raw==='number'&&Number.isFinite(raw)?raw:fallback;}

function Scene({manifest}: {manifest: Manifest}) {
  const frame=useCurrentFrame();
  const [fontHandle] = useState(() => delayRender('res-remotion-fonts'));
  useEffect(() => {
    Promise.all(manifest.fonts.map(async font => {
      const source=manifest.assets[font.assetId];
      if(!source)throw new Error(`font_asset_missing:${font.assetId}`);
      const face=new FontFace(font.family,`url(${source})`,{weight:String(font.weight)});
      await face.load(); document.fonts.add(face);
    })).then(() => continueRender(fontHandle)).catch(error => cancelRender(error));
  }, [fontHandle, manifest]);
  const byId=new Map(manifest.layers.map(layer=>[layer.id,layer]));
  const nodeToLayer=new Map(manifest.nodes.map(node=>[node.nodeId,node.targetLayerId]));
  const children=new Map<string,Layer[]>();
  for(const layer of manifest.layers){
    const node=manifest.nodes.find(item=>item.targetLayerId===layer.id);
    const parent=typeof layer.properties.parentId==='string'?layer.properties.parentId:node?.parentNodeId?nodeToLayer.get(node.parentNodeId):undefined;
    if(parent&&!byId.has(parent))throw new Error(`parent_missing:${parent}`);
    const list=children.get(parent??'root')??[];list.push(layer);children.set(parent??'root',list);
  }
  for(const list of children.values())list.sort((a,b)=>a.zIndex-b.zIndex);
  const renderLayer=(layer:Layer):React.ReactNode=>{
    const p=layer.properties;
    const tracks=manifest.tracks.filter(track=>track.targetLayerId===layer.id);
    const v=Object.fromEntries(tracks.map(track=>[track.propertyPath,valueAt(track.keyframes,frame)]));
    const timing=p.editorialTiming as {startFrame:number;durationFrames:number;reveal?:string;revealFrames?:number}|undefined;
    const active=!timing||(frame>=timing.startFrame&&frame<timing.startFrame+timing.durationFrames);
    let transitionOpacity=1;
    for(const t of manifest.transitions){
      if(t.fromLayerId===layer.id){
        if(t.kind==='hard_cut'&&frame>=t.startFrame)transitionOpacity=0;
        if(t.kind==='dissolve'&&frame>=t.startFrame)transitionOpacity*=frame>=t.endFrameExclusive?0:1-(frame-t.startFrame)/(t.endFrameExclusive-t.startFrame);
      }
      if(t.toLayerId===layer.id){
        if(frame<t.startFrame)transitionOpacity=0;
        else if(t.kind==='dissolve'&&frame<t.endFrameExclusive)transitionOpacity*=(frame-t.startFrame)/(t.endFrameExclusive-t.startFrame);
      }
    }
    const opacity=active&&layer.visible?(num(v.opacity,layer.opacity))*transitionOpacity:0;
    const style:React.CSSProperties={position:'absolute',left:layer.x,top:layer.y,width:layer.width,height:layer.height,
      opacity,zIndex:layer.zIndex,transformOrigin:'center center',
      transform:`translate(${num(v['position.x'],0)}px,${num(v['position.y'],0)}px) scale(${num(v['scale.x'],1)},${num(v['scale.y'],1)}) rotate(${num(v['rotation.degrees'],layer.rotation)}deg)`,
      filter:num(v['filters.blurPx'],0)>0?`blur(${num(v['filters.blurPx'],0)}px)`:undefined};
    let content:React.ReactNode;
    if(layer.kind==='group')content=children.get(layer.id)?.map(renderLayer);
    else if(layer.kind==='image'){
      const source=manifest.assets[String(p.assetId??'')];if(!source)throw new Error(`image_missing:${layer.id}`);
      content=<Img src={source} style={{width:'100%',height:'100%',objectFit:p.objectFit==='fill'?'fill':p.objectFit==='contain'?'contain':'cover'}}/>;
    }else if(layer.kind==='shape'&&p.editorialPath){
      const path=p.editorialPath as {points:{x:number;y:number}[];strokeWidth?:number};
      if(!path.points?.length)throw new Error(`path_empty:${layer.id}`);
      const progress=timing?.reveal==='path'?Math.max(0,Math.min(1,(frame-timing.startFrame)/(timing.revealFrames??12))):1;
      const d=path.points.map((pt,i)=>`${i?'L':'M'} ${pt.x} ${pt.y}`).join(' ');
      content=<svg width="100%" height="100%" viewBox={`0 0 ${layer.width} ${layer.height}`} style={{overflow:'visible'}}>
        <path d={d} fill="none" stroke={color(p.color,'#fff')} strokeWidth={num(path.strokeWidth,4)}
          pathLength={1} strokeDasharray="1" strokeDashoffset={1-progress}/></svg>;
    }else if(layer.kind==='shape')content=<div style={{width:'100%',height:'100%',background:color(p.fill,'#fff'),
      borderRadius:p.shape==='ellipse'?'50%':num(p.borderRadius,0)}}/>;
    else{
      const original=String(p.text??'');
      const tokens=original.split(/(\s+)/u);const count=tokens.filter(token=>token&&!/^\s+$/u.test(token)).length;
      const elapsed=timing?Math.max(0,frame-timing.startFrame):0;
      const visible=timing?.reveal==='words'?Math.min(count,Math.max(1,Math.ceil(count*elapsed/(timing.revealFrames??12)))):count;
      let seen=0;const displayed=tokens.filter(token=>/^\s+$/u.test(token)?seen>0&&seen<visible:++seen<=visible).join('').trimEnd();
      const family=String(p.fontFamily??'Arial');const weight=num(v.fontWeight,p.fontWeight==='normal'?400:num(p.fontWeight,700));
      const authored=num(v['fontSize.px'],num(p.fontSize,48));const lineHeight=num(v['lineHeight.ratio'],num(p.lineHeight,1.1));
      const spacing=num(v['letterSpacing.px'],num(p.letterSpacing,0));
      const oneLine=!original.includes('\n')&&layer.height<2*authored*lineHeight;
      let size=authored;
      if(oneLine&&typeof document!=='undefined'){
        const ctx=document.createElement('canvas').getContext('2d');
        if(ctx){ctx.font=`${weight} ${authored}px "${family.replace(/"/g,'')}"`;
          const measured=ctx.measureText(original).width+Math.max(0,original.length-1)*spacing;
          if(measured>layer.width*.96)size=Math.max(12,authored*layer.width*.96/measured);}
      }
      content=<div style={{width:'100%',height:'100%',color:color(p.color,'#fff'),fontFamily:family,fontWeight:weight,
        fontSize:size,lineHeight,letterSpacing:spacing,textAlign:p.textAlign==='center'||p.textAlign==='right'?p.textAlign:'left',
        whiteSpace:oneLine?'nowrap':'pre-wrap',overflow:'hidden'}}>{displayed}</div>;
    }
    return <div key={layer.id} style={style}>{content}</div>;
  };
  return <div style={{position:'absolute',inset:0,background:manifest.background,overflow:'hidden'}}>{children.get('root')?.map(renderLayer)}</div>;
}
function Root(){return <Composition id="ResPlanComparison" component={Scene} width={720} height={1280} fps={30} durationInFrames={30}
  defaultProps={{manifest:{width:720,height:1280,fps:30,durationFrames:30,background:'#10181c',layers:[],tracks:[],transitions:[],nodes:[],assets:{},fonts:[]}}}
  calculateMetadata={({props})=>({width:props.manifest.width,height:props.manifest.height,fps:props.manifest.fps,durationInFrames:props.manifest.durationFrames})}/>;}
registerRoot(Root);
