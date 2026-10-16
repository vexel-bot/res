import React, {useId} from 'react';

export type Matrix=[number,number,number,number,number,number];
export type MatteTimeContext={centerFrame:number;sampledLayerIds:ReadonlySet<string>};
type Key={frame:number;value:number;easing:string;cubicBezier?:number[]};
type Layer={id:string;name?:string;x:number;y:number;width:number;height:number;rotation:number;opacity:number;
  visible:boolean;properties:Record<string,any>};
type Scene={layers:Layer[];nodes:{nodeId:string;targetLayerId:string;parentNodeId?:string;transformOriginX?:number;
  transformOriginY?:number}[];tracks:{targetLayerId:string;propertyPath:string;keyframes:Key[]}[]};
export function multiply(a:Matrix,b:Matrix):Matrix{
  return [a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],
    a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
}
export function inverse(m:Matrix):Matrix{
  const det=m[0]*m[3]-m[1]*m[2];
  if(!Number.isFinite(det)||Math.abs(det)<1e-12)throw new Error('hybrid_asset_matte_singular_transform');
  return [m[3]/det,-m[1]/det,-m[2]/det,m[0]/det,(m[2]*m[5]-m[3]*m[4])/det,(m[1]*m[4]-m[0]*m[5])/det];
}
const translation=(x:number,y:number):Matrix=>[1,0,0,1,x,y];
export function matteTransform(scene:Scene,targetId:string,sourceId:string,frame:number,
  valueAt:(keys:Key[],frame:number)=>number,timeContext?:MatteTimeContext){
  const cache=new Map<string,Matrix>();const visiting=new Set<string>();
  const evaluationFrames=new Map<string,number>();
  const timeFor=(id:string)=>timeContext&&!timeContext.sampledLayerIds.has(id)?timeContext.centerFrame:frame;
  function world(id:string):Matrix{
    const saved=cache.get(id);if(saved)return saved;
    if(visiting.has(id))throw new Error('hybrid_asset_matte_parent_cycle');visiting.add(id);
    const layer=scene.layers.find(l=>l.id===id),node=scene.nodes.find(n=>n.targetLayerId===id);
    if(!layer||!node)throw new Error('hybrid_asset_matte_layer_binding_missing');
    const evaluatedFrame=timeFor(id);evaluationFrames.set(id,evaluatedFrame);
    const v=Object.fromEntries(scene.tracks.filter(t=>t.targetLayerId===id)
      .map(t=>[t.propertyPath,valueAt(t.keyframes,evaluatedFrame)]));
    const rotation=(v['rotation.degrees']??layer.rotation)*Math.PI/180;
    const sx=v['scale.x']??1,sy=v['scale.y']??1,px=(node.transformOriginX??.5)*layer.width,
      py=(node.transformOriginY??.5)*layer.height;
    const rs:Matrix=[Math.cos(rotation)*sx,Math.sin(rotation)*sx,-Math.sin(rotation)*sy,Math.cos(rotation)*sy,0,0];
    let m=multiply(translation(layer.x+(v['position.x']??0)+px,layer.y+(v['position.y']??0)+py),
      multiply(rs,translation(-px,-py)));
    if(node.parentNodeId){
      const parent=scene.nodes.find(n=>n.nodeId===node.parentNodeId);
      if(!parent)throw new Error('hybrid_asset_matte_parent_missing');
      const parentLayer=scene.layers.find(layer=>layer.id===parent.targetLayerId)!;
      const border=parentLayer.properties.editorialBorder?.width??0;
      // Absolute children start at the parent's padding edge, inside its
      // border. The border offset is in parent space and is transformed once.
      m=multiply(world(parent.targetLayerId),multiply(translation(border,border),m));
    }
    if(!m.every(Number.isFinite))throw new Error('hybrid_asset_matte_transform_nonfinite');
    visiting.delete(id);cache.set(id,m);return m;
  }
  const source=scene.layers.find(l=>l.id===sourceId)!;
  if(!source)throw new Error('hybrid_asset_matte_source_missing');
  const timing=source.properties.editorialTiming;
  const sourceFrame=timeFor(sourceId);
  const active=source.visible&&(!timing||(sourceFrame>=timing.startFrame&&sourceFrame<timing.startFrame+timing.durationFrames));
  const opacityTrack=scene.tracks.find(t=>t.targetLayerId===sourceId&&t.propertyPath==='opacity');
  const opacity=active?(opacityTrack?valueAt(opacityTrack.keyframes,sourceFrame):source.opacity):0;
  const matrix=multiply(inverse(world(targetId)),world(sourceId));
  return {matrix,opacity,source,evaluationFrames:{target:timeFor(targetId),source:sourceFrame,
    nodes:Object.fromEntries(evaluationFrames)},timePolicy:timeContext?'local_subtree_effective_draw_times':'uniform_frame'};
}

export function AssetMatte({children,spec,mapping,width,height,src}:
  {children:React.ReactElement<{style?:React.CSSProperties}>;spec:any;
    mapping:ReturnType<typeof matteTransform>;width:number;height:number;src:string}){
  const unique=useId().replace(/[^a-zA-Z0-9_-]/g,'');
  const id='asset-matte-'+unique,filter='asset-matte-filter-'+unique,clip='asset-matte-clip-'+unique;
  const {matrix,source,opacity}=mapping;
  if(spec.schemaVersion!=='studio.asset-matte.v1'||!['alpha','luminance'].includes(spec.mode)||
    spec.coordinateSpace!=='composition_world'||spec.opacitySpace!=='source_layer_only'||typeof spec.invert!=='boolean'){
    throw new Error('hybrid_asset_matte_spec_invalid');
  }
  const diagnostic={schemaVersion:spec.schemaVersion,sourceLayerId:source.id,assetId:spec.assetId,mode:spec.mode,
    invert:spec.invert,coordinateSpace:spec.coordinateSpace,opacitySpace:spec.opacitySpace,
    sourceToTargetMatrix:matrix,sourceLocalOpacity:opacity,pixelCoverageObserved:false,
    evaluationFrames:mapping.evaluationFrames,timePolicy:mapping.timePolicy};
  return <>
    <svg width={0} height={0} style={{position:'absolute',pointerEvents:'none'}} aria-hidden="true">
      <defs>
        <clipPath id={clip} clipPathUnits="userSpaceOnUse">
          <rect x={0} y={0} width={width} height={height}/>
        </clipPath>
        {spec.invert?<filter id={filter} x="0%" y="0%" width="100%" height="100%" colorInterpolationFilters="sRGB">
          {spec.mode==='luminance'?<>
            <feColorMatrix in="SourceGraphic" type="luminanceToAlpha" result="luminance"/>
            <feComposite in="luminance" in2="SourceAlpha" operator="in"/>
          </>:<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/>}
        </filter>:null}
        <mask id={id} maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x={-width} y={-height} width={width*3} height={height*3}
          style={{maskType:spec.mode,colorInterpolation:'sRGB'}}>
          {/* Keep viewport rounding away from the target edge. One vector
              clip retains the authored target footprint for both modes. */}
          <g clipPath={`url(#${clip})`}>
          {null}
          <image href={src} width={source.width} height={source.height} transform={`matrix(${matrix.join(' ')})`}
            preserveAspectRatio={spec.objectFit==='cover'?'xMidYMid slice':'xMidYMid meet'} opacity={opacity}
            filter={undefined}/>
          </g>
        </mask>
      </defs>
    </svg>
    {React.cloneElement(children,{...{'data-asset-matte':JSON.stringify(diagnostic)},style:{...children.props.style,
      maskImage:spec.invert?`linear-gradient(#fff,#fff),url(#${id})`:`url(#${id})`,maskMode:'match-source',maskComposite:spec.invert?'subtract':'add',maskRepeat:'no-repeat',maskClip:'no-clip',outline:'2px solid transparent',outlineOffset:0}})}
  </>;
}
