import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {CameraMotionBlur} from '@remotion/motion-blur';
import {MeasuredRecipeText} from './typography-layout';
import {AssetMatte, matteTransform, type MatteTimeContext} from './asset-matte';
import {TemporalExposure} from './temporal-exposure';
import {spatialFilter} from './spatial-effects';
import {Composition, Img, OffthreadVideo, Sequence, cancelRender, continueRender, delayRender, registerRoot, staticFile, useCurrentFrame} from 'remotion';

type Key = {frame:number; value:number; easing:string; cubicBezier?:number[]};
type Native = {component:'action_montage'|'product_demonstration'|'integrated_typography'|'gesture_occlusion_reveal'|'moving_variant_mask'; version:1;
  entranceFrames:number; travelRatio:number; revealAxis:'horizontal'|'vertical'; staggerFrames:number; continuityKey?:string;
  baseTargetId?:string; occluderTargetId?:string; switchFrame:number; maskStartX:number; maskStartY:number;
  maskEndX:number; maskEndY:number; maskRadius:number};
type Layer = {id:string; name?:string; kind:'video'|'image'|'shape'|'text'|'group'; x:number; y:number;
  width:number; height:number; rotation:number; opacity:number; zIndex:number; visible:boolean; properties:Record<string,any>};
type Manifest = {schemaVersion:string; nativeCompositionDigest?:string; width:number; height:number; fps:number; durationFrames:number; background:string;
  layers:Layer[]; assets:Record<string,string>; fonts:{assetId:string;family:string;weight:number}[];
  nodes:{nodeId:string;targetLayerId:string;parentNodeId?:string;transformOriginX?:number;transformOriginY?:number}[];
  tracks:{targetLayerId:string;propertyPath:string;keyframes:Key[]}[];
  transitions:{kind:string;fromLayerId:string;toLayerId:string;startFrame:number;endFrameExclusive:number}[]};
const clamp=(x:number)=>Math.max(0,Math.min(1,x));
function valueAt(keys:Key[],frame:number):number {
  if(frame<=keys[0].frame)return keys[0].value;
  for(let i=0;i<keys.length-1;i++){
    const a=keys[i],b=keys[i+1];
    if(frame>=b.frame)continue;
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
function SampledGraphic({draw}:{draw:(frame:number)=>React.ReactNode}) {
  return <>{draw(useCurrentFrame())}</>;
}
function RecipeTypography({text,frame,spec}:{text:string;frame:number;spec:any}) {
  if(spec.version===2){
    const segmentation=spec.segmentation;
    if(segmentation?.schemaVersion!=='studio.typography-units.v1'||
      segmentation.policy!=='unicode17.regex2026.1.15.whitespace-v1'||segmentation.unit!==spec.unit||
      !Array.isArray(segmentation.units)||segmentation.units.map((u:any)=>u.text).join('')!==text){
      throw new Error('hybrid_typography_units_invalid');
    }
    let count=0;
    for(const unit of segmentation.units){
      if(typeof unit.text!=='string'||!unit.text||
        (/^\p{White_Space}+$/u.test(unit.text)?unit.animationIndex!==null:unit.animationIndex!==count++)){
        throw new Error('hybrid_typography_indices_invalid');
      }
    }
    if(count!==segmentation.animatedCount||count<1||
      spec.completeFrame!==spec.startFrame+(count-1)*spec.staggerFrames+spec.entranceFrames){
      throw new Error('hybrid_typography_timing_invalid');
    }
    return <>{segmentation.units.map((unit:any,key:number)=>{
      if(unit.animationIndex===null)return unit.text;
      const t=progress(frame-spec.startFrame-unit.animationIndex*spec.staggerFrames,spec.entranceFrames);
      return <span key={key} data-typography-unit={unit.animationIndex} style={{display:'inline-block',opacity:t,
        transform:`translateY(${(1-t)*.18}em)`}}>{unit.text}</span>;
    })}</>;
  }
  if(spec.version!==undefined&&spec.version!==1)throw new Error('hybrid_typography_version_unsupported');
  let index=0;
  const units=spec.unit==='character'?Array.from(text):text.split(/(\s+)/u);
  return <>{units.map((unit,key)=>{
    if(/^\s+$/u.test(unit))return unit;
    const t=progress(frame-spec.startFrame-index++*spec.staggerFrames,spec.entranceFrames);
    return <span key={key} style={{display:'inline-block',opacity:t,
      transform:`translateY(${(1-t)*.18}em)`}}>{unit}</span>;
  })}</>;
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
  const fontsReleased=useRef(false);
  useEffect(()=>{
    Promise.all([...m.fonts.map(async f=>{
      const font=new FontFace(f.family,`url(${staticFile(m.assets[f.assetId])})`,{weight:String(f.weight)});
      await font.load();(document.fonts as FontFaceSet & {add(font:FontFace):void}).add(font);
    }),...m.layers.filter(layer=>layer.properties.matteSourceOnly).map(async layer=>{
      const image=new Image();image.src=staticFile(m.assets[layer.properties.assetId]);await image.decode();
    })]).then(()=>{setReady(true);}).catch(cancelRender);
  },[m,handle]);
  useLayoutEffect(()=>{
    if(!ready||!stage.current)return;
    const root=stage.current.getBoundingClientRect();
    const sx=m.width/root.width,sy=m.height/root.height;
    const seen=new Set<string>();
    const elements=Array.from(stage.current.querySelectorAll<HTMLElement>('[data-layer-id]')).filter(el=>{
      const id=el.dataset.layerId!;if(seen.has(id))return false;seen.add(id);return true;
    }).map(el=>{
      const box=el.getBoundingClientRect();let opacity=1;let cursor:HTMLElement|null=el;
      while(cursor&&cursor!==stage.current){opacity*=Number(getComputedStyle(cursor).opacity);cursor=cursor.parentElement;}
      const layer=m.layers.find(l=>l.id===el.dataset.layerId)!;
      const timing=layer.properties.editorialTiming;
      const present=!timing||(frame>=timing.startFrame&&frame<timing.startFrame+timing.durationFrames);
      const native=layer.properties.nativeComponent as Native|undefined;
      const local=frame-(timing?.startFrame??0);
      const maskProgress=native?.component==='moving_variant_mask'?progress(local-native.switchFrame,native.entranceFrames):undefined;
      const typography=layer.properties.recipeTypography;
      const layoutElement=el.querySelector<HTMLElement>('[data-text-layout]');
      const textLayout=layoutElement?.dataset.textLayout?JSON.parse(layoutElement.dataset.textLayout):undefined;
      const exposureElement=el.closest<HTMLElement>('[data-temporal-exposure]');
      const exposure=exposureElement?.dataset.temporalExposure?JSON.parse(exposureElement.dataset.temporalExposure):undefined;
      if(layer.properties.recipeTextLayout&&!textLayout)throw new Error('hybrid_typography_layout_missing:'+layer.id);
      const typographyUnits=typography?.version===2?Array.from(el.querySelectorAll<HTMLElement>('[data-typography-unit]')).map(unit=>{
        const rect=unit.getBoundingClientRect();const computed=getComputedStyle(unit);
        return {animationIndex:Number(unit.dataset.typographyUnit),text:unit.textContent,
          localOpacity:Number(computed.opacity),fontFamily:computed.fontFamily,fontSizePx:parseFloat(computed.fontSize),
          bounds:{x:(rect.x-root.x)*sx,y:(rect.y-root.y)*sy,width:rect.width*sx,height:rect.height*sy}};
      }):undefined;
      if(typographyUnits&&typographyUnits.length!==typography.segmentation.animatedCount){
        throw new Error('hybrid_typography_geometry_incomplete');
      }
      return {layerId:layer.id,semanticId:layer.name||layer.id,present,
        visible:present&&opacity>.01&&!layer.properties.matteSourceOnly,opacity,
        ...(layer.properties.matteSourceOnly?{matteSourceOnly:true}:{}),
        geometryBasis:'dom_bounding_box',maskCoverageObserved:false,
        ...(el.dataset.assetMatte?{assetMatte:JSON.parse(el.dataset.assetMatte)}:{}),
        ...(layer.properties.recipeTemporalBlur?{temporalBlurGeometryBasis:'sampled_dom_not_pixel_coverage'}:{}),
        ...(exposure?{temporalExposure:{...exposure,observedSampleFrame:exposure.sampleFrames[0]},
          geometryBasis:'first_exposure_sample_dom_bounding_box'}:{}),
        bounds:{x:(box.x-root.x)*sx,y:(box.y-root.y)*sy,width:box.width*sx,height:box.height*sy},
        ...(typographyUnits?{typography:{policy:typography.segmentation.policy,geometryBasis:'dom_span_bounding_box',
          animatedCount:typography.segmentation.animatedCount,completeFrame:typography.completeFrame,
          holdEligible:(exposure?.sampleFrames??[frame]).every((time:number)=>time>=typography.completeFrame),
          units:typographyUnits,...(textLayout?{layout:textLayout}:{})}}:{}),
        ...(maskProgress!==undefined?{nativeMask:{centerX:native!.maskStartX+(native!.maskEndX-native!.maskStartX)*maskProgress,
          centerY:native!.maskStartY+(native!.maskEndY-native!.maskStartY)*maskProgress,radius:native!.maskRadius}}:{}),
        ...(native?.component==='gesture_occlusion_reveal'?{nativeReveal:progress(local-native.switchFrame,native.entranceFrames)}:{}),
        ...(layer.kind==='video'?{sourceTimeSeconds:layer.properties.sourceStartSeconds+
          (frame-timing.startFrame)/m.fps*(layer.properties.playbackRate??1),sourceTimeBasis:'timeline_mapping'}:{})};
    });
    console.log('RES_GEOMETRY:'+JSON.stringify({frame,elements}));
    if(!fontsReleased.current){fontsReleased.current=true;continueRender(handle);}
  },[frame,ready,m]);
  const nodeToLayer=new Map(m.nodes.map(n=>[n.nodeId,n.targetLayerId]));
  const children=new Map<string,Layer[]>();
  for(const layer of m.layers){
    const n=m.nodes.find(n=>n.targetLayerId===layer.id);
    const parent=n?.parentNodeId?nodeToLayer.get(n.parentNodeId):'root';
    const bucket=children.get(parent??'root')??[];bucket.push(layer);children.set(parent??'root',bucket);
  }
  for(const bucket of children.values())bucket.sort((a,b)=>a.zIndex-b.zIndex);
  const draw=(layer:Layer,frame:number,disableTemporal=false,timeContext?:MatteTimeContext):React.ReactNode=>{
    const p=layer.properties,timing=p.editorialTiming;
    const temporal=p.recipeTemporalBlur;
    if(temporal&&!disableTemporal&&frame>=temporal.startFrame&&frame<temporal.endFrameExclusive){
      if(temporal.exposurePolicy){
        const sampledLayerIds=new Set<string>();
        const collect=(item:Layer)=>{if(sampledLayerIds.has(item.id))return;sampledLayerIds.add(item.id);
          children.get(item.id)?.forEach(collect);};
        collect(layer);
        const sampleContext:MatteTimeContext={centerFrame:frame,sampledLayerIds};
        return <TemporalExposure key={layer.id} frame={frame} start={temporal.startFrame} end={temporal.endFrameExclusive}
          samples={temporal.samples} shutter={temporal.shutterAngle} policy={temporal.exposurePolicy} zIndex={layer.zIndex}
          draw={sample=>draw(layer,sample,true,sampleContext)} componentInputs={element=>{
            const props=element.props;
            if(element.type===AssetMatte){const {evaluationFrames:_,...paintMapping}=props.mapping;
              return {tag:'asset_matte_v1',props:{...props,mapping:paintMapping}};}
            if(element.type===MeasuredRecipeText){const {frame:_,...inputs}=props;return {tag:'measured_text_v1',props:inputs};}
            if(element.type===RecipeTypography&&props.spec?.version===2&&props.frame>=props.spec.completeFrame){
              const {frame:_,...inputs}=props;return {tag:'settled_typography_v2',props:inputs};
            }
            return null;
          }}/>
      }
      return <CameraMotionBlur key={layer.id} samples={temporal.samples} shutterAngle={temporal.shutterAngle}>
        <SampledGraphic draw={sample=>draw(layer,sample,true)}/>
      </CameraMotionBlur>;
    }
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
    const spatialEffects=spatialFilter(blur,shadow,layer.id);
    const mask=p.maskAssetId?`url(${staticFile(m.assets[p.maskAssetId])})`:undefined;
    const occlusion=p.recipeOcclusion;
    if(occlusion&&frame>=occlusion.startFrame&&frame<occlusion.endFrameExclusive){
      const cover=m.layers.find(candidate=>candidate.id===occlusion.occluderLayerId)!;
      const cv=Object.fromEntries(m.tracks.filter(t=>t.targetLayerId===cover.id).map(t=>[t.propertyPath,valueAt(t.keyframes,frame)]));
      const tx=layer.x+(v['position.x']??0),ty=layer.y+(v['position.y']??0);
      const left=cover.x+(cv['position.x']??0)-tx,top=cover.y+(cv['position.y']??0)-ty;
      // A real rectangular matte follows the occluder's local trajectory.
      clipPath=occlusion.axis==='vertical'?`inset(0 0 ${Math.max(0,layer.height-top)}px 0)`:
        `inset(0 ${Math.max(0,layer.width-left)}px 0 0)`;
    }
    const style:React.CSSProperties={position:'absolute',left:layer.x,top:layer.y,width:layer.width,height:layer.height,
      opacity,zIndex:layer.zIndex,clipPath,transformOrigin:`${(n?.transformOriginX??.5)*100}% ${(n?.transformOriginY??.5)*100}%`,
      transform:`translate(${(v['position.x']??0)+occluderX}px,${(v['position.y']??0)+occluderY}px) rotate(${v['rotation.degrees']??layer.rotation}deg) scale(${v['scale.x']??1},${v['scale.y']??1})`,
      filter:spatialEffects,
      mixBlendMode:p.editorialBlendMode??'normal',maskImage:mask,maskSize:'100% 100%',maskMode:'luminance',
      border:p.editorialBorder?.width?`${p.editorialBorder.width}px solid ${p.editorialBorder.color}`:undefined,boxSizing:'border-box'};
    let content:React.ReactNode;
    if(layer.kind==='group')content=children.get(layer.id)?.map(child=>draw(child,frame,disableTemporal,timeContext));
    else if(layer.kind==='video')content=<ActionMontage src={staticFile(m.assets[p.assetId])} start={start} duration={duration}
      offset={p.sourceStartSeconds??0} rate={p.playbackRate??1} fps={m.fps} fit={p.objectFit??'contain'}/>;
    else if(layer.kind==='image')content=p.matteSourceOnly?null:<Img src={staticFile(m.assets[p.assetId])} style={{width:'100%',height:'100%',objectFit:p.objectFit??'contain'}}/>;
    else if(layer.kind==='shape'&&p.editorialPath){
      const points=p.editorialPath.points;
      const d=p.editorialPath.mode==='quadratic'?`M ${points[0].x} ${points[0].y} Q ${points[1].x} ${points[1].y} ${points[2].x} ${points[2].y}`:
        points.map((pt:any,i:number)=>`${i?'L':'M'} ${pt.x} ${pt.y}`).join(' ');
      content=<svg width="100%" height="100%" viewBox={`0 0 ${layer.width} ${layer.height}`} style={{display:'block',overflow:'visible'}}>
        <path d={d} fill="none" stroke={p.color} strokeWidth={p.editorialPath.strokeWidth} pathLength={1} strokeDasharray="1"
          strokeDashoffset={p.recipeStroke?1-clamp(valueAt(p.recipeStroke,frame)):
            timing?.reveal==='path'?1-clamp(local/(timing.revealFrames??12)):0}/></svg>;
    }else if(layer.kind==='shape')content=<div style={{width:'100%',height:'100%',background:p.fill,borderRadius:p.shape==='ellipse'?'50%':p.borderRadius}}/>;
    else{
      let fontSize=v['fontSize.px']??p.fontSize;
      if(p.editorialTextFit===true&&ready&&!p.recipeTextLayout){
        const ctx=document.createElement('canvas').getContext('2d');
        if(ctx){ctx.font=`${v.fontWeight??p.fontWeight} ${fontSize}px "${p.fontFamily??'Arial'}"`;
          const width=Math.max(...String(p.text).split('\n').map(line=>ctx.measureText(line).width+
            Math.max(0,Array.from(line).length-1)*(v['letterSpacing.px']??p.letterSpacing??0)));
          if(width>layer.width)fontSize*=layer.width/width;
        }
      }
      const textStyle:React.CSSProperties={width:'100%',height:'100%',fontFamily:p.fontFamily??'Arial',
        fontWeight:v.fontWeight??p.fontWeight,lineHeight:v['lineHeight.ratio']??p.lineHeight,letterSpacing:v['letterSpacing.px']??p.letterSpacing,
        color:p.color,textAlign:p.textAlign,whiteSpace:'pre-wrap',fontSize};
      const textContent=p.recipeTypography?<RecipeTypography text={p.text} frame={frame} spec={p.recipeTypography}/>:
          native?.component==='integrated_typography'?<IntegratedTypography text={p.text} frame={local} spec={native}/>:
          timing?.reveal==='words'?String(p.text).split(/\s+/u).slice(0,Math.ceil(clamp(local/(timing.revealFrames??12))*String(p.text).split(/\s+/u).length)).join(' '):p.text;
      content=p.recipeTextLayout?<MeasuredRecipeText style={textStyle} width={layer.width} height={layer.height}
        requested={fontSize} policy={p.recipeTextLayout} digest={m.nativeCompositionDigest??''} ready={ready}
        frame={frame} layerId={layer.id} fontBound={Boolean(p.fontAssetId)}>{textContent}</MeasuredRecipeText>:
        <div style={textStyle}>{textContent}</div>;
    }
    if(native?.component==='product_demonstration')content=<ProductDemonstration frame={local} spec={native}>{content}</ProductDemonstration>;
    else if(native?.component==='gesture_occlusion_reveal')content=<GestureOcclusionReveal frame={local} spec={native}>{content}</GestureOcclusionReveal>;
    else if(native?.component==='moving_variant_mask')content=<MovingVariantMask frame={local} spec={native}>{content}</MovingVariantMask>;
    else if(timing?.reveal==='wipe')content=<div style={{width:'100%',height:'100%',clipPath:`inset(0 ${(1-clamp(local/(timing.revealFrames??12)))*100}% 0 0)`}}>{content}</div>;
    const element=<div key={layer.id} data-layer-id={layer.id} style={style}>{content}</div>;
    if(p.recipeAssetMatte&&frame>=p.recipeAssetMatte.startFrame&&frame<p.recipeAssetMatte.endFrameExclusive){
      return <AssetMatte key={layer.id} spec={p.recipeAssetMatte} width={layer.width} height={layer.height}
        mapping={matteTransform(m,layer.id,p.recipeAssetMatte.sourceLayerId,frame,valueAt,timeContext)}
        src={staticFile(m.assets[p.recipeAssetMatte.assetId])}>{element}</AssetMatte>;
    }
    return element;
  };
  return <div ref={stage} style={{position:'absolute',inset:0,overflow:'hidden',background:m.background}}>{children.get('root')?.map(layer=>draw(layer,frame))}</div>;
}
const defaults:Manifest={schemaVersion:'res.remotion-native-composition.v2',width:720,height:1280,fps:30,durationFrames:450,
  background:'#101010',layers:[],assets:{},fonts:[],nodes:[],tracks:[],transitions:[]};
registerRoot(()=> <Composition id="ResHybrid" component={Hybrid} width={720} height={1280} fps={30} durationInFrames={450}
  defaultProps={{manifest:defaults}} calculateMetadata={({props})=>({width:props.manifest.width,height:props.manifest.height,
    fps:props.manifest.fps,durationInFrames:props.manifest.durationFrames})}/>);
