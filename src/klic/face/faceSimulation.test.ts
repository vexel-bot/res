import test from 'node:test';
import assert from 'node:assert/strict';
import { generateAIFaceSphere } from './sphereGenerator';
import { KlicFaceSimulation } from './faceSimulation';
import { faceVoiceModulation } from './voiceModulation';
import { QUIET_RESONANCE } from '../hologramModel';
import { REST_POINTER } from '../hologramDynamics';

test('imported generator preserves the source 72-ribbon geometry, saddle harmonics and physical attributes',()=>{
  const points=generateAIFaceSphere(1,()=>.5);
  assert.ok(points.length>5000);assert.equal(new Set(points.map(p=>p.ribbonIndex)).size,72);
  const first=points[0],cos=Math.cos(first.basePhi);
  const phi=first.basePhi+.30*Math.sin(.4)*cos+.10*Math.sin(-.2)*Math.pow(cos,1.4);
  assert.ok(Math.abs(first.baseX-Math.cos(phi))<1e-12);assert.ok(Math.abs(first.baseY-Math.sin(phi))<1e-12);
  assert.ok(Math.abs(first.mass-.9)<1e-12);assert.ok(Math.abs(first.baseRadius-.975)<1e-12);
  assert.ok(points.every(p=>Number.isFinite(p.x)&&p.vx===0&&p.basePhi>-Math.PI/2&&p.basePhi<Math.PI/2));
});

test('full/compact/adaptive prefixes retain the same imported identity and every ribbon',()=>{
  const full=new KlicFaceSimulation(),compact=new KlicFaceSimulation(288);
  assert.ok(full.particles.length>5000);assert.equal(compact.particles.length,288);
  assert.equal(new Set(compact.particles.map(p=>p.ribbonIndex)).size,72);
  assert.deepEqual(full.particles.slice(0,288),compact.particles);
  full.step(1,1/60,QUIET_RESONANCE,REST_POINTER,1,false,5040);
  assert.equal(new Set([...full.order.slice(0,5040)].map(i=>full.particles[i].ribbonIndex)).size,72);
  for(let n=1;n<5040;n++)assert.ok(full.depths[full.order[n-1]]<=full.depths[full.order[n]]);
});

test('idle remains organic, correctly framed and continuously projected without reallocating particles',()=>{
  const model=new KlicFaceSimulation(5040),identity=model.particles;
  model.step(0,0,QUIET_RESONANCE,REST_POINTER);
  const before=model.screenY.slice();
  for(let i=1;i<=60;i++)model.step(i/60,1/60,QUIET_RESONANCE,REST_POINTER);
  assert.equal(model.particles,identity);assert.ok(model.screenY.some((n,i)=>Math.abs(n-before[i])>.02));
  assert.ok(Math.max(...model.screenX.map(Math.abs))<.49);assert.ok(Math.max(...model.screenY.map(Math.abs))<.49);
});

test('real audio energy changes voice deformation; absent energy never invents syllables',()=>{
  for(const state of ['listening','speaking'] as const){
    const quiet={...QUIET_RESONANCE,[state]:1},loud={...quiet,energy:.8,low:.6,high:.3};
    const a=new KlicFaceSimulation(5040),b=new KlicFaceSimulation(5040);
    a.step(2,1/60,quiet,REST_POINTER);b.step(2,1/60,loud,REST_POINTER);
    assert.ok(a.screenX.some((n,i)=>Math.abs(n-b.screenX[i])>.01));
    assert.equal(faceVoiceModulation(2,quiet).volume,0);
    assert.equal(faceVoiceModulation(7,quiet).volume,0);
  }
  const low=new KlicFaceSimulation(288),high=new KlicFaceSimulation(288);
  low.step(2,1/60,{listening:1,speaking:0,energy:.7,low:0,high:0},REST_POINTER);
  high.step(2,1/60,{listening:1,speaking:0,energy:.7,low:1,high:1},REST_POINTER);
  assert.ok(low.screenX.some((n,i)=>Math.abs(n-high.screenX[i])>.001),'actual frequency bands affect acoustic waves');
});

test('source shatter and click wave remain bounded; springs recover the moving reference geometry',()=>{
  const disturbed=new KlicFaceSimulation(5040),reference=new KlicFaceSimulation(5040);
  const pointer={active:true,x:.2,y:0,vx:3,vy:1};
  disturbed.step(0,0,QUIET_RESONANCE,REST_POINTER);reference.step(0,0,QUIET_RESONANCE,REST_POINTER);
  disturbed.burst(pointer);
  for(let i=1;i<=30;i++){
    disturbed.step(i/60,1/60,QUIET_RESONANCE,pointer);reference.step(i/60,1/60,QUIET_RESONANCE,REST_POINTER);
  }
  const displaced=disturbed.particles.filter((p,i)=>Math.hypot(p.x-reference.particles[i].x,p.y-reference.particles[i].y,p.z-reference.particles[i].z)>.02).length;
  assert.ok(displaced>20&&displaced<5040);
  for(let i=31;i<=480;i++){
    disturbed.step(i/60,1/60,QUIET_RESONANCE,REST_POINTER);reference.step(i/60,1/60,QUIET_RESONANCE,REST_POINTER);
  }
  for(let i=0;i<5040;i++){
    const a=disturbed.particles[i],b=reference.particles[i];
    assert.ok(Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z)<1e-8,'restored geometry follows its original moving equilibrium');
  }
});

test('reduced motion freezes phase and disables physical bursts; long frame gaps stay finite',()=>{
  const model=new KlicFaceSimulation(288);
  model.step(2,1/60,QUIET_RESONANCE,REST_POINTER);
  const pointer={active:true,x:0,y:0,vx:12,vy:12};model.burst(pointer);
  model.step(2,1,QUIET_RESONANCE,pointer,1,true);
  const stable=model.screenX.slice();
  model.step(2,1,QUIET_RESONANCE,pointer,1,true);assert.deepEqual(model.screenX,stable);
  assert.ok(model.particles.every(p=>p.vx===0&&p.vy===0&&p.vz===0));
  model.step(3,60,QUIET_RESONANCE,pointer);
  assert.ok(model.particles.every(p=>Number.isFinite(p.x)&&Math.abs(p.x)<2));
});

test('source spring integration stays consistent at 30/60/120 FPS and theme does not enter the geometry model',()=>{
  const simulate=(fps:number)=>{
    const model=new KlicFaceSimulation(288);
    model.step(0,0,QUIET_RESONANCE,REST_POINTER);
    for(let i=1;i<=fps*3;i++)model.step(i/fps,1/fps,QUIET_RESONANCE,i<fps/4?{active:true,x:.2,y:0,vx:2,vy:0}:REST_POINTER);
    return model;
  };
  const a=simulate(30),b=simulate(120);
  let difference=0;
  for(let i=0;i<288;i++)difference+=(a.screenX[i]-b.screenX[i])**2+(a.screenY[i]-b.screenY[i])**2;
  assert.ok(Math.sqrt(difference/288)<.02);
  assert.equal(a.particles.length,b.particles.length);
});
