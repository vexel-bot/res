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
  const roots=nodes.map(node=>{
    if(!React.isValidElement<Record<string,any>>(node))return null;
    if(typeof node.type==='string')return {element:node,wrapped:false};
    if(componentInputs(node)?.tag==='asset_matte_v1'&&
      React.isValidElement<Record<string,any>>(node.props.children)&&typeof node.props.children.type==='string'){
      return {element:node.props.children,wrapped:true};
    }
    return null;
  });
  const sharedOpacity=roots[0]?.element.props.style?.opacity;
  const factored=typeof sharedOpacity==='number'&&Number.isFinite(sharedOpacity)&&sharedOpacity>=0&&sharedOpacity<=1&&
    roots.every(root=>root!==null&&root.element.props.style?.opacity===sharedOpacity&&
      (root.element.props.style?.mixBlendMode??'normal')==='normal');
  const samplesToComposite=factored?nodes.map((node,index)=>{
    const root=roots[index]!;
    const opaque=React.cloneElement(root.element,{style:{...root.element.props.style,opacity:1}});
    return root.wrapped?React.cloneElement(node as React.ReactElement<any>,{children:opaque}):opaque;
  }):nodes;
  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    data-experimental-opacity-factored={factored?sharedOpacity:undefined}
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate',opacity:factored?sharedOpacity:1}}>
    {(() => {
      const average=(items:React.ReactNode[]):React.ReactNode=>{
        if(items.length===1)return items[0];
        const cut=Math.floor(items.length/2),left=items.slice(0,cut),right=items.slice(cut);
        return <div style={{position:'absolute',inset:0,isolation:'isolate'}}>
          <div style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',opacity:left.length/items.length}}>
            {average(left)}
          </div>
          <div style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',opacity:right.length/items.length}}>
            {average(right)}
          </div>
        </div>;
      };
      return average(samplesToComposite);
    })()}
  </div>;
}
