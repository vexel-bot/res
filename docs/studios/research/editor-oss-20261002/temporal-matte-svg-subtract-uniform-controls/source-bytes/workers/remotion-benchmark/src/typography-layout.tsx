import React, {useLayoutEffect, useRef} from 'react';
import {cancelRender} from 'remotion';

// Original implementation. Measure the actual canonical unit spans in local
// space; parent/entrance transforms affect world geometry, not line wrapping.
export type LayoutPolicy = {schemaVersion:string;policy:string;fitMode:string;minFontSizePx:number;
  maxMeasureSteps:number;maxLayoutUnits:number;tolerancePx:number;fontQuantizationPx:number};
type Box = {x:number;y:number;width:number;height:number};
type UnitMetrics = {animationIndex:number;text:string;layout:Box;baselinePx:number;ink:Box};
type Measurement = {fontSizePx:number;contentHeightPx:number;lines:Box[];units:UnitMetrics[];fits:boolean};
type LayoutResult = Measurement & {policy:string;requestedFontSizePx:number;minimumFontSizePx:number;
  fontFamily:string;fontWeight:string;letterSpacingPx:number;lineHeightPx:string;measurements:number;
  geometryBasis:string;inkBasis:string;inkCoverageObserved:false;fontBindingBasis:string};
const cache=new Map<string,LayoutResult>();
function validatePolicy(p:LayoutPolicy){
  if(p.schemaVersion!=='studio.typography-layout-policy.v1'||p.policy!=='dom.units-fit.v1'||p.fitMode!=='wrap_shrink'||
    !Number.isFinite(p.minFontSizePx)||p.minFontSizePx<8||p.minFontSizePx>205||p.maxMeasureSteps!==18||
    p.maxLayoutUnits!==2000||p.tolerancePx!==.5||p.fontQuantizationPx!==1/64){
    throw new Error('hybrid_typography_layout_policy_invalid');
  }
}

export function measureTypography(source:HTMLElement,width:number,height:number,requested:number,p:LayoutPolicy,
  digest:string,fontBindingBasis:string):LayoutResult {
  validatePolicy(p);
  if(!digest||![width,height,requested].every(n=>Number.isFinite(n)&&n>0)){
    throw new Error('hybrid_typography_layout_binding_invalid');
  }
  const computed=getComputedStyle(source);
  const spans=Array.from(source.querySelectorAll<HTMLElement>('[data-typography-unit]'));
  if(!spans.length||source.childNodes.length>p.maxLayoutUnits||spans.length>p.maxLayoutUnits){
    throw new Error('hybrid_typography_layout_unit_limit');
  }
  const spacing=parseFloat(computed.letterSpacing)||0;
  const key=JSON.stringify([digest,source.textContent,spans.map(s=>s.textContent),width,height,requested,p,
    computed.fontFamily,computed.fontWeight,source.style.lineHeight,spacing,computed.textAlign,computed.direction,fontBindingBasis]);
  const cached=cache.get(key);if(cached)return cached;
  if(requested<p.minFontSizePx){
    throw new Error('hybrid_typography_below_reading_floor:increase_fontSize_or_canvas');
  }
  const mirror=source.cloneNode(true) as HTMLElement;
  Object.assign(mirror.style,{position:'fixed',left:'0px',top:'0px',width:`${width}px`,height:'auto',
    visibility:'hidden',opacity:'1',transform:'none',margin:'0px',padding:'0px',border:'none',
    fontFamily:computed.fontFamily,fontWeight:computed.fontWeight,whiteSpace:'pre-wrap',
    letterSpacing:computed.letterSpacing,textAlign:computed.textAlign,direction:computed.direction});
  // A computed pixel line-height would freeze it during fitting. Preserve the
  // authored unitless ratio from the actual source inline style instead.
  mirror.style.lineHeight=source.style.lineHeight;
  mirror.removeAttribute('data-text-layout');
  const measuredSpans=Array.from(mirror.querySelectorAll<HTMLElement>('[data-typography-unit]'));
  const markers=measuredSpans.map(span=>{
    span.style.transform='none';span.style.opacity='1';
    const marker=document.createElement('i');
    Object.assign(marker.style,{display:'inline-block',width:'0px',height:'0px',padding:'0px',margin:'0px',verticalAlign:'baseline'});
    span.appendChild(marker);return marker;
  });
  document.body.appendChild(mirror);
  const ctx=document.createElement('canvas').getContext('2d');
  let measurements=0;
  try{
    if(!ctx)throw new Error('hybrid_typography_font_metrics_unavailable');
    const measure=(fontSize:number):Measurement=>{
      measurements++;
      mirror.style.fontSize=`${fontSize}px`;
      const origin=mirror.getBoundingClientRect();
      const style=getComputedStyle(mirror);
      ctx.font=`${style.fontWeight} ${fontSize}px ${style.fontFamily}`;
      ctx.textBaseline='alphabetic';ctx.textAlign='left';
      ctx.direction=style.direction==='rtl'?'rtl':'ltr';
      if('letterSpacing' in ctx)(ctx as CanvasRenderingContext2D & {letterSpacing:string}).letterSpacing=style.letterSpacing;
      else if(spacing!==0)throw new Error('hybrid_typography_letter_spacing_metrics_pending');
      const lines:Box[]=[];
      const units=measuredSpans.map((span,index):UnitMetrics=>{
        const range=document.createRange();range.selectNodeContents(span.firstChild!);
        const rect=range.getBoundingClientRect();
        const box={x:rect.x-origin.x,y:rect.y-origin.y,width:rect.width,height:rect.height};
        // Canonical words/graphemes are atomic inline blocks: one baseline each.
        const baseline=markers[index].getBoundingClientRect().y-origin.y;
        const text=spans[index].textContent!;
        const metrics=ctx.measureText(text);
        const ink={x:box.x-metrics.actualBoundingBoxLeft,y:baseline-metrics.actualBoundingBoxAscent,
          width:metrics.actualBoundingBoxLeft+metrics.actualBoundingBoxRight,
          height:metrics.actualBoundingBoxAscent+metrics.actualBoundingBoxDescent};
        if(!Object.values({...box,...ink,baseline}).every(Number.isFinite)){
          throw new Error('hybrid_typography_font_metrics_nonfinite');
        }
        const line=lines.find(line=>Math.abs(line.y-box.y)<.5);
        if(line){const right=Math.max(line.x+line.width,box.x+box.width);line.x=Math.min(line.x,box.x);
          line.width=right-line.x;line.height=Math.max(line.height,box.height);}
        else lines.push({...box});
        return {animationIndex:Number(span.dataset.typographyUnit),text,layout:box,baselinePx:baseline,ink};
      });
      // Ink bounds are font-engine diagnostics; this fit decision constrains
      // occupied DOM layout, including blank line height. It does not prove ink
      // clipping/coverage or readability under the parent transform.
      const fits=origin.height<=height+p.tolerancePx&&units.every(u=>u.layout.x>=-p.tolerancePx&&
        u.layout.x+u.layout.width<=width+p.tolerancePx);
      return {fontSizePx:fontSize,contentHeightPx:origin.height,lines,units,fits};
    };
    let measured=measure(requested);
    if(!measured.fits){
      let low=p.minFontSizePx,high=requested;
      measured=measure(low);
      if(!measured.fits)throw new Error('hybrid_typography_does_not_fit_at_reading_floor:enlarge_box_or_shorten_text');
      for(let i=0;i<p.maxMeasureSteps;i++){
        const mid=(low+high)/2,candidate=measure(mid);
        if(candidate.fits){low=mid;measured=candidate;}else high=mid;
      }
      const quantized=Math.max(p.minFontSizePx,Math.floor(low/p.fontQuantizationPx)*p.fontQuantizationPx);
      measured=measure(quantized);
      if(!measured.fits)throw new Error('hybrid_typography_fit_unstable:adjust_box_or_spacing');
    }
    const result:LayoutResult={...measured,policy:p.policy,requestedFontSizePx:requested,minimumFontSizePx:p.minFontSizePx,
      fontFamily:computed.fontFamily,fontWeight:computed.fontWeight,letterSpacingPx:spacing,
      lineHeightPx:getComputedStyle(mirror).lineHeight,measurements,geometryBasis:'local_dom_range_and_block_height',
      inkBasis:'canvas_font_textmetrics',inkCoverageObserved:false,fontBindingBasis};
    if(cache.size>=128)cache.delete(cache.keys().next().value!);cache.set(key,result);
    return result;
  }finally{mirror.remove();}
}

export function MeasuredRecipeText({children,style,width,height,requested,policy,digest,ready,frame,layerId,fontBound}:
  {children:React.ReactNode;style:React.CSSProperties;width:number;height:number;requested:number;policy:LayoutPolicy;
    digest:string;ready:boolean;frame:number;layerId:string;fontBound:boolean}){
  const ref=useRef<HTMLDivElement>(null);
  useLayoutEffect(()=>{
    if(!ready||!ref.current)return;
    try{
      const result=measureTypography(ref.current,width,height,requested,policy,digest,
        fontBound?'checksum_bound_asset':'unfixed_platform_font');
      ref.current.style.fontSize=`${result.fontSizePx}px`;
      ref.current.dataset.textLayout=JSON.stringify(result);
    }catch(error){cancelRender(new Error(`${String(error)}:target=${layerId}:frame=${frame}`));}
  },[ready,frame,width,height,requested,policy,digest,style.fontFamily,style.fontWeight,style.lineHeight,
    style.letterSpacing,style.textAlign,layerId,fontBound,children]);
  return <div ref={ref} style={style}>{children}</div>;
}
