import test from 'node:test';
import assert from 'node:assert/strict';
import { createCanvasFace, mountKlicHologram, rasterizeFaceDot } from './hologramRenderer';

function fakeCanvas() {
  const calls:Array<[string,...unknown[]]>=[];
  const context={globalAlpha:1,fillStyle:''} as unknown as CanvasRenderingContext2D;
  for(const name of ['clearRect','putImageData'] as const)
    (context as unknown as Record<string,unknown>)[name]=(...args:unknown[])=>calls.push([name,...args]);
  context.createImageData=((width:number,height:number)=>{
    calls.push(['createImageData',width,height]);return {width,height,data:new Uint8ClampedArray(width*height*4)} as ImageData;
  }) as typeof context.createImageData;
  const canvas=Object.assign(new EventTarget(),{width:300,height:150,getContext:(name:string,options:unknown)=>{
    calls.push(['getContext',name,options]);return context;
  }}) as unknown as HTMLCanvasElement;
  return {canvas,context,calls,named:(name:string)=>calls.filter(c=>c[0]===name)};
}

test('Canvas 2D only, Z-sort, Retina backing pixels and one reusable black raster surface',()=>{
  const {canvas,context,named}=fakeCanvas(),sink=createCanvasFace(canvas,5040)!;
  canvas.width=504;canvas.height=504;
  sink.render({time:2,light:0,delta:1/60},{width:252,height:252,ratio:2},5040);
  assert.deepEqual(named('getContext'),[['getContext','2d',{alpha:false}]]);
  assert.deepEqual(named('createImageData')[0],['createImageData',504,504]);
  const image=named('putImageData')[0][1] as ImageData;
  assert.deepEqual([...image.data.slice(0,4)],[0,0,0,255]);
  assert.ok(image.data.some((value,i)=>i%4!==3&&value>0));assert.equal(context.globalAlpha,1);
  const particles=sink.model.particles,order=sink.model.order;
  for(const light of [.25,.5,.75,1])sink.render({time:2+light,light,delta:1/60},{width:252,height:252,ratio:2},5040);
  assert.equal(sink.model.particles,particles);assert.equal(sink.model.order,order);
  assert.equal(named('getContext').length,1);
  assert.equal(named('createImageData').length,1);assert.equal(named('putImageData').length,5);
  assert.equal(named('putImageData').at(-1)![1],image);
  sink.dispose();sink.dispose();
  const draws=named('putImageData').length;
  sink.render({time:8,light:0},{width:252,height:252,ratio:2},5040);
  assert.equal(named('putImageData').length,draws);
});

test('transparent integration has no black rectangle; unavailable 2D context fails without WebGL or DOM fallback',()=>{
  const {canvas,named}=fakeCanvas(),sink=createCanvasFace(canvas,5040,'transparent')!;
  sink.render({time:2,light:1},{width:320,height:180,ratio:1.5},5040);
  assert.deepEqual(named('getContext')[0],['getContext','2d',{alpha:true}]);
  const image=named('putImageData')[0][1] as ImageData;
  assert.deepEqual([...image.data.slice(0,4)],[0,0,0,0]);sink.dispose();
  assert.equal(createCanvasFace({getContext:()=>null} as unknown as HTMLCanvasElement,5040),undefined);
});

test('mounted native engine retains context and phase through theme, visibility and context restoration; cleans every listener',()=>{
  const names=['navigator','window','document','performance','requestAnimationFrame','cancelAnimationFrame','ResizeObserver','IntersectionObserver','matchMedia'] as const;
  const originals=new Map(names.map(name=>[name,Object.getOwnPropertyDescriptor(globalThis,name)]));
  const {canvas,calls,named}=fakeCanvas();
  const pending=new Map<number,(time:number)=>void>();
  let now=0,sequence=0,removed=0,disconnected=0;
  const host=Object.assign(new EventTarget(),{dataset:{} as Record<string,string>,closest:()=>null,getBoundingClientRect:()=>({width:252,height:252,left:0,top:0})}) as unknown as HTMLSpanElement;
  class Resize{observe(){}disconnect(){disconnected++;}}
  const media={matches:false,addEventListener(){},removeEventListener(){removed++;}};
  const values:Record<string,unknown>={navigator:{hardwareConcurrency:8,deviceMemory:8},window:{devicePixelRatio:2},
    document:{hidden:false,addEventListener(){},removeEventListener(){removed++;}},performance:{now:()=>now},
    requestAnimationFrame:(callback:(time:number)=>void)=>{pending.set(++sequence,callback);return sequence;},cancelAnimationFrame:(id:number)=>pending.delete(id),
    ResizeObserver:Resize,IntersectionObserver:undefined,matchMedia:()=>media};
  for(const name of names)Object.defineProperty(globalThis,name,{configurable:true,value:values[name]});
  const step=(time:number)=>{now=time;const callbacks=[...pending.values()];pending.clear();calls.length=0;callbacks.forEach(callback=>callback(time));};
  try{
    const instance=mountKlicHologram(host,canvas,'dark');
    assert.equal(host.dataset.renderer,'canvas2d');assert.equal(canvas.width,504);assert.equal(canvas.height,504);
    assert.equal(named('getContext').length,1);
    step(0);const first=(named('putImageData')[0][1] as ImageData).data.slice();
    instance.setTheme('light');step(16);step(216);step(416);
    const last=(named('putImageData')[0][1] as ImageData).data.slice();assert.notDeepEqual(last,first);assert.equal(pending.size,1);
    assert.equal(named('getContext').length,0);
    instance.setActive(false);assert.equal(pending.size,0);
    instance.setActive(true);step(1000);assert.deepEqual((named('putImageData')[0][1] as ImageData).data,last);
    const lost=new Event('contextlost',{cancelable:true});canvas.dispatchEvent(lost);
    assert.equal(lost.defaultPrevented,true);assert.equal(pending.size,0);
    canvas.dispatchEvent(new Event('contextrestored'));step(1500);assert.deepEqual((named('putImageData')[0][1] as ImageData).data,last);
    instance.dispose();instance.dispose();assert.equal(pending.size,0);assert.equal(disconnected,1);assert.equal(removed,2);
    assert.equal(host.dataset.renderer,undefined);
    canvas.dispatchEvent(new Event('contextrestored'));assert.equal(pending.size,0);
  }finally{
    for(const name of names){const original=originals.get(name);if(original)Object.defineProperty(globalThis,name,original);else Reflect.deleteProperty(globalThis,name);}
  }
});

test('analytic micropoints source-over composite in painter order without blur and stay within pixel bounds',()=>{
  const pixels=new Uint8ClampedArray(8*8*4);
  rasterizeFaceDot(pixels,8,8,4.5,4.5,1,[110,184,245],.5);
  const center=(4*8+4)*4;
  assert.deepEqual([...pixels.slice(center,center+4)],[110,184,245,128]);
  rasterizeFaceDot(pixels,8,8,4.5,4.5,1,[180,225,255],.9);
  assert.ok(pixels[center]>170&&pixels[center+3]>240);
  rasterizeFaceDot(pixels,8,8,-10,-10,1,[255,255,255],1);
  assert.deepEqual([...pixels.slice(0,4)],[0,0,0,0]);
});

test('actual voice energy brightens particles without changing the imported geometry or renderer context',()=>{
  const {canvas,named}=fakeCanvas(),sink=createCanvasFace(canvas,288,'transparent')!;
  sink.render({time:2,light:0,delta:0,reduced:true},{width:300,height:150,ratio:1},288);
  const dark=(named('putImageData')[0][1] as ImageData).data.slice();
  const particles=sink.model.particles;
  sink.render({time:2,light:0,delta:0,reduced:true},{width:300,height:150,ratio:1},288,{listening:0,speaking:1,energy:1,low:0,high:0});
  const active=(named('putImageData').at(-1)![1] as ImageData).data;
  assert.ok(active.some((n,i)=>i%4===0&&n>dark[i]));
  assert.equal(sink.model.particles,particles);assert.equal(named('getContext').length,1);
  sink.dispose();
});

test('viewport raster keeps the sphere footprint and paints shatter points beyond all four former canvas edges',()=>{
  const {canvas,named}=fakeCanvas(),sink=createCanvasFace(canvas,2,'transparent')!;
  canvas.width=1000;canvas.height=700;
  // Controlled projections isolate the surface from the independently tested physics.
  sink.model.step=()=>{
    sink.model.screenX.set([-1,1]);sink.model.screenY.set([-.8,.8]);
    sink.model.radii.fill(1);sink.model.fronts.fill(1);sink.model.opacities.fill(1);
  };
  const frame={left:200,top:150,width:252,height:252};
  sink.render({time:0,light:0},{width:1000,height:700,ratio:1,frame},2);
  const upload=named('putImageData').at(-1)!;
  const image=upload[1] as ImageData,left=upload[2] as number,top=upload[3] as number;
  const alphaAt=(x:number,y:number)=>image.data[((y-top)*image.width+x-left)*4+3];
  assert.ok(alphaAt(74,74)>0,'upper-left particle escapes the old sphere rectangle');
  assert.ok(alphaAt(578,478)>0,'lower-right particle escapes the old sphere rectangle');
  assert.ok(image.width<canvas.width&&image.height<canvas.height,'only the live bounds are uploaded, not a full-screen raster');
  sink.render({time:1,light:0},{width:1000,height:700,ratio:1,frame:{...frame,left:300,top:120}},2);
  assert.deepEqual(named('clearRect').at(-1),['clearRect',left,top,image.width,image.height]);
  assert.equal(named('createImageData').length,1,'anchor movement reuses the raster buffer');
  assert.equal(named('putImageData').at(-1)![2],left+100);
  assert.equal(named('putImageData').at(-1)![3],top-30);
  sink.dispose();
});

test('viewport canvas follows its local anchor, resizes with the browser and releases viewport listeners',()=>{
  const names=['navigator','window','document','performance','requestAnimationFrame','cancelAnimationFrame','ResizeObserver','IntersectionObserver','matchMedia'] as const;
  const originals=new Map(names.map(name=>[name,Object.getOwnPropertyDescriptor(globalThis,name)]));
  const {canvas,named}=fakeCanvas(),pending=new Map<number,(time:number)=>void>();
  let now=0,sequence=0;
  const rect={left:200,top:150,width:252,height:252};
  const host=Object.assign(new EventTarget(),{dataset:{},closest:()=>null,getBoundingClientRect:()=>rect}) as unknown as HTMLSpanElement;
  const viewport=new EventTarget();
  const browser=Object.assign(new EventTarget(),{devicePixelRatio:2,innerWidth:1000,innerHeight:700,visualViewport:viewport});
  class Resize{observe(){}disconnect(){}}
  const values:Record<string,unknown>={navigator:{hardwareConcurrency:4,deviceMemory:4},window:browser,
    document:{hidden:false,addEventListener(){},removeEventListener(){}},performance:{now:()=>now},
    requestAnimationFrame:(callback:(time:number)=>void)=>{pending.set(++sequence,callback);return sequence;},cancelAnimationFrame:(id:number)=>pending.delete(id),
    ResizeObserver:Resize,IntersectionObserver:undefined,matchMedia:()=>({matches:false,addEventListener(){},removeEventListener(){}})};
  for(const name of names)Object.defineProperty(globalThis,name,{configurable:true,value:values[name]});
  const step=(time:number)=>{now=time;const callbacks=[...pending.values()];pending.clear();callbacks.forEach(callback=>callback(time));};
  try{
    const instance=mountKlicHologram(host,canvas,'dark',{surface:'viewport',background:'transparent'});
    assert.equal(canvas.width,2000);assert.equal(canvas.height,1400);
    step(0);const first=named('putImageData').at(-1)!;
    rect.left+=100;rect.top-=30;
    step(0);const moved=named('putImageData').at(-1)!;
    assert.equal(moved[2],Number(first[2])+200);assert.equal(moved[3],Number(first[3])-60);
    browser.innerWidth=800;browser.innerHeight=600;browser.dispatchEvent(new Event('resize'));
    assert.equal(canvas.width,1600);assert.equal(canvas.height,1200);
    browser.innerWidth=700;viewport.dispatchEvent(new Event('resize'));
    assert.equal(canvas.width,1400);
    rect.top=80;browser.dispatchEvent(new Event('scroll'));step(16);
    assert.equal(named('getContext').length,1,'viewport changes never recreate the simulation/context');
    instance.dispose();const width=canvas.width;
    browser.innerWidth=500;browser.dispatchEvent(new Event('resize'));viewport.dispatchEvent(new Event('scroll'));
    assert.equal(canvas.width,width);assert.equal(pending.size,0);
  }finally{
    for(const name of names){const original=originals.get(name);if(original)Object.defineProperty(globalThis,name,original);else Reflect.deleteProperty(globalThis,name);}
  }
});
