import test from 'node:test';
import assert from 'node:assert/strict';
import { CanvasFaceModel, type VoiceState } from './canvasFaceModel';
import { QUIET_RESONANCE } from './hologramModel';
import { REST_POINTER } from './hologramDynamics';

test('native face has requested Particle3D fields, 72 harmonic bands, stable identities and exact depth order',()=>{
  const model=new CanvasFaceModel(5040), particles=model.particles, order=model.order;
  assert.equal(particles.length,5040);
  for(const p of particles){
    assert.ok(p.mass>=.7&&p.mass<=1.1);assert.ok(p.baseRadius>=.75&&p.baseRadius<=1.35);
    assert.ok(Number.isFinite(p.theta)&&Number.isFinite(p.basePhi));
  }
  model.step(1,1/60,QUIET_RESONANCE,REST_POINTER);
  const before=particles.map(p=>p.x);
  model.step(2,1/60,QUIET_RESONANCE,REST_POINTER);
  assert.equal(model.particles,particles);assert.equal(model.order,order);
  assert.ok(particles.some((p,i)=>Math.abs(p.x-before[i])>.005));
  for(let i=1;i<order.length;i++)assert.ok(particles[order[i-1]].z<=particles[order[i]].z);
  assert.ok(Math.min(...model.opacities)>=.19&&Math.max(...model.opacities)<=.981);
});

test('localized cursor shatter returns every particle exactly to its dynamic rest shape',()=>{
  const disturbed=new CanvasFaceModel(5040), reference=new CanvasFaceModel(5040);
  disturbed.step(0,0,QUIET_RESONANCE,REST_POINTER);
  for(let i=1;i<=20;i++)disturbed.step(i/60,1/60,QUIET_RESONANCE,{active:true,x:.22,y:0,vx:2,vy:-1});
  reference.step(20/60,1/60,QUIET_RESONANCE,REST_POINTER);
  const affected=disturbed.particles.filter((p,i)=>Math.hypot(p.x-reference.particles[i].x,p.y-reference.particles[i].y)>.001).length;
  assert.ok(affected>20&&affected<4000,`local displacement, not the whole sphere: ${affected}`);
  for(let i=21;i<=400;i++)disturbed.step(i/60,1/60,QUIET_RESONANCE,REST_POINTER);
  reference.step(400/60,1/60,QUIET_RESONANCE,REST_POINTER);
  for(let i=0;i<5040;i++){
    const a=disturbed.particles[i],b=reference.particles[i];
    assert.deepEqual([a.x,a.y,a.z,a.vx,a.vy,a.vz],[b.x,b.y,b.z,0,0,0]);
  }
});

test('voice deformation and reduced motion preserve geometry identities and reset residual force',()=>{
  const model=new CanvasFaceModel(5040), first=model.particles[0];
  const states:VoiceState[]=['idle','listening','speaking'];
  for(const state of states)model.step(3,1/60,{listening:state==='listening'?1:0,speaking:state==='speaking'?1:0,energy:.8,low:.4,high:.3},{active:true,x:0,y:0,vx:2,vy:2});
  assert.equal(model.particles[0],first);
  model.step(3,1/60,QUIET_RESONANCE,REST_POINTER,1,true);
  const stable=model.particles.map(p=>[p.x,p.y,p.z]);
  model.step(3,1/60,QUIET_RESONANCE,{active:true,x:0,y:0,vx:12,vy:12},1,true);
  assert.deepEqual(model.particles.map(p=>[p.x,p.y,p.z]),stable);
  assert.ok(model.particles.every(p=>p.vx===0&&p.vy===0&&p.vz===0));
});
