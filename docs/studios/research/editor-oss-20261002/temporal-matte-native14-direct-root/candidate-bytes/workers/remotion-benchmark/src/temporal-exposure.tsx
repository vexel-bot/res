import React from 'react';

export type ExposurePolicy={schemaVersion:'studio.temporal-exposure.v1';sampling:'centered_clipped';
  coordinateSpace:'local_subtree';ancestorTime:'center_frame';compositing:'premultiplied_srgb_plus_lighter';
  staticReduction:'identical_registered_draw_inputs'};
type ComponentInputs=(element:React.ReactElement<any>)=>{tag:string;props:Record<string,any>}|null;

export function exposureFrames(frame:number,start:number,end:number,samples:number,shutter:number):number[]{
  if(![frame,start,end,shutter].every(Number.isFinite)||start>=end||frame<start||frame>=end||
    !Number.isInteger(samples)||samples<2||samples>32||shutter<0||shutter>360){
    throw new Error('hybrid_temporal_exposure_interval_invalid');
  }
  if(shutter===0)return [frame];
  const half=shutter/720,low=Math.max(start,frame-half),high=Math.min(end,frame+half);
  return Array.from({length:samples},(_,index)=>low+(high-low)*(index+.5)/samples);
}

// Compare the actual draw inputs rather than inventing a second animation
// evaluator. Unknown components/functions cannot justify a static reduction.
export function visualFingerprint(node:React.ReactNode,componentInputs:ComponentInputs):string|null{
  let supported=true;
  function visit(value:React.ReactNode,depth:number):any{
    if(depth>100){supported=false;return null;}
    if(value===null||value===undefined||typeof value==='boolean')return null;
    if(typeof value==='string'||typeof value==='number')return value;
    if(Array.isArray(value))return value.map(child=>visit(child,depth+1));
    if(!React.isValidElement<Record<string,any>>(value)){supported=false;return null;}
    const element=value as React.ReactElement<Record<string,any>>;
    const normalized=typeof element.type==='string'?{tag:element.type,props:element.props}:
      element.type===React.Fragment?{tag:'fragment',props:element.props}:componentInputs(element);
    if(!normalized){supported=false;return null;}
    const {children,...props}=normalized.props;
    return {tag:normalized.tag,props,children:visit(children,depth+1)};
  }
  const tree=visit(node,0);
  const result=JSON.stringify(tree,(_key,value)=>{
    if(typeof value==='function'||typeof value==='symbol'){supported=false;return null;}
    return value;
  });
  return supported?result:null;
}

export function TemporalExposure({frame,start,end,samples,shutter,policy,zIndex,draw,componentInputs}:
  {frame:number;start:number;end:number;samples:number;shutter:number;policy:ExposurePolicy;zIndex:number;
    draw:(frame:number)=>React.ReactNode;componentInputs:ComponentInputs}){
  if(policy.schemaVersion!=='studio.temporal-exposure.v1'||policy.sampling!=='centered_clipped'||
    policy.coordinateSpace!=='local_subtree'||policy.ancestorTime!=='center_frame'||
    policy.compositing!=='premultiplied_srgb_plus_lighter'||policy.staticReduction!=='identical_registered_draw_inputs'){
    throw new Error('hybrid_temporal_exposure_policy_invalid');
  }
  const requestedFrames=exposureFrames(frame,start,end,samples,shutter);
  const nodes=requestedFrames.map(draw),fingerprints=nodes.map(node=>visualFingerprint(node,componentInputs));
  const center=draw(frame),centerFingerprint=visualFingerprint(center,componentInputs);
  const stationary=centerFingerprint!==null&&fingerprints.every(value=>value===centerFingerprint);
  const single=shutter===0||stationary;
  const frames=single?[frame]:requestedFrames;
  const diagnostic={schemaVersion:policy.schemaVersion,...policy,frame,requestedSamples:samples,
    actualSamples:frames.length,sampleFrames:frames,requestedSampleFrames:requestedFrames,
    reduction:shutter===0?'zero_shutter':stationary?'identical_registered_draw_inputs':'none',
    sampleWeights:frames.map(()=>1/frames.length),pixelCoverageObserved:false};
  if(single)return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    style={{position:'absolute',inset:0,zIndex}}>{center}</div>;
  const weighted=(node:React.ReactNode,index:number)=>
    React.isValidElement<Record<string,any>>(node)&&typeof node.type==='string'
      ? React.cloneElement(node,{key:index,style:{...node.props.style,mixBlendMode:'plus-lighter',opacity:1/frames.length}})
      : <div key={index} style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>;
  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate'}}>
    {nodes.map(weighted)}
  </div>;
}
