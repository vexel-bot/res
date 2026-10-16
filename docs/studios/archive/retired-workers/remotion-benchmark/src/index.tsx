import React from 'react';
import {Composition, registerRoot, useCurrentFrame} from 'remotion';

type Key = {frame: number; value: number; easing: string};
type Track = {targetLayerId: string; propertyPath: string; keyframes: Key[]};
type Layer = {id: string; kind: string; x: number; y: number; width: number; height: number; rotation: number; opacity: number; zIndex: number; visible: boolean; properties: Record<string, unknown>};
type Manifest = {width: number; height: number; durationFrames: number; fps: number; background: string; layers: Layer[]; tracks: Track[]; assets: Record<string,string>};

function valueAt(keys: Key[], frame: number): number {
  if (frame <= keys[0].frame) return keys[0].value;
  for (let i=0;i<keys.length-1;i++) {
    const a=keys[i], b=keys[i+1];
    if (frame <= b.frame) {
      let p=(frame-a.frame)/(b.frame-a.frame);
      if (a.easing==='ease_in_out') p=p<.5?2*p*p:1-(-2*p+2)**2/2;
      if (a.easing==='ease_out') p=1-(1-p)**2;
      if (a.easing==='ease_in') p=p*p;
      if (a.easing==='hold') p=0;
      return a.value+(b.value-a.value)*p;
    }
  }
  return keys[keys.length-1].value;
}

function Scene({manifest}: {manifest: Manifest}) {
  const frame=useCurrentFrame();
  return <div style={{position:'absolute',inset:0,background:manifest.background,overflow:'hidden'}}>
    {[...manifest.layers].sort((a,b)=>a.zIndex-b.zIndex).map(layer=>{
      const props=layer.properties;
      const values=Object.fromEntries(manifest.tracks.filter(track=>track.targetLayerId===layer.id)
        .map(track=>[track.propertyPath,valueAt(track.keyframes,frame)]));
      const style: React.CSSProperties={position:'absolute',left:layer.x,top:layer.y,width:layer.width,height:layer.height,
        opacity:layer.visible?(values.opacity??layer.opacity):0,zIndex:layer.zIndex,
        transform:`translate(${values['position.x']??0}px,${values['position.y']??0}px) scale(${values['scale.x']??1},${values['scale.y']??1}) rotate(${values['rotation.degrees']??layer.rotation}deg)`};
      if(layer.kind==='shape') return <div key={layer.id} style={{...style,background:String(props.fill??'#ffffff'),borderRadius:props.shape==='ellipse'?'50%':0}}/>;
      if(layer.kind==='image') return <img key={layer.id} src={manifest.assets[String(props.assetId)]} style={{...style,objectFit:'contain'}}/>;
      if(layer.kind==='text') return <div key={layer.id} style={{...style,color:String(props.color??'#fff'),fontFamily:'Arial',fontSize:Number(props.fontSize??48),fontWeight:700}}>{String(props.text??'')}</div>;
      throw new Error('unsupported_benchmark_layer:'+layer.kind);
    })}
  </div>;
}

function Root(){
  return <Composition id="ResComparison" component={Scene} width={480} height={320} fps={15} durationInFrames={15}
    defaultProps={{manifest:{width:480,height:320,fps:15,durationFrames:15,background:'#101827',layers:[],tracks:[],assets:{}}}}/>;
}
registerRoot(Root);
