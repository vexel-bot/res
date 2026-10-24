import { hologramParticles, hologramPose, projectHologramPoint, type HologramProjection, type HologramResonance } from './hologramModel';
import type { HologramPointer } from './hologramDynamics';

export type VoiceState = 'idle' | 'listening' | 'speaking';

export interface Particle3D {
  baseX: number; baseY: number; baseZ: number;
  x: number; y: number; z: number;
  vx: number; vy: number; vz: number;
  mass: number;
  baseRadius: number;
  theta: number; basePhi: number; seed: number;
}

const clamp = (n:number, limit:number) => Math.max(-limit, Math.min(limit, n));

/** Camera-space positions, elastic offsets relative to a moving rest shape, and reusable Z-order. */
export class CanvasFaceModel {
  readonly particles: Particle3D[];
  readonly order: Uint32Array;
  readonly fronts: Float32Array;
  readonly opacities: Float32Array;
  readonly radii: Float32Array;
  private readonly points: Float32Array;
  private readonly rest: Float64Array;
  private readonly baseLengths: Float64Array;
  private readonly pose=hologramPose(0);
  private activeOrder: Uint32Array;
  private readonly projected = {} as HologramProjection;
  private initialized = false;
  private moving = false;

  constructor(count:number) {
    this.points = hologramParticles(count);
    const total = this.points.length / 5;
    this.rest = new Float64Array(total * 3);
    this.order = Uint32Array.from({length:total}, (_,i)=>i);
    this.activeOrder=this.order;
    this.baseLengths=new Float64Array(total);
    this.fronts = new Float32Array(total);
    this.opacities = new Float32Array(total);
    this.radii = new Float32Array(total);
    this.particles = Array.from({length:total}, (_,i)=>{
      const k=i*5, baseX=this.points[k], baseY=this.points[k+1], baseZ=this.points[k+2], seed=this.points[k+3];
      this.baseLengths[i]=Math.hypot(baseX,baseY,baseZ);
      return {baseX,baseY,baseZ,x:baseX,y:baseY,z:baseZ,vx:0,vy:0,vz:0,
        mass:.7+seed*.4,baseRadius:.75+((i*.73205080757)%1)*.6,
        theta:Math.atan2(baseZ,baseX),basePhi:Math.acos(baseY/Math.hypot(baseX,baseY,baseZ)),seed};
    });
  }

  reset() {
    this.initialized = false; this.moving = false;
    for (const p of this.particles) { p.vx=0; p.vy=0; p.vz=0; }
  }

  step(time:number, delta:number, voice:HologramResonance, pointer:HologramPointer, aspect=1, reduced=false, count=this.particles.length) {
    const limit=Math.min(count,this.particles.length);
    if(this.activeOrder.length!==limit){
      for(let i=0;i<limit;i++)this.order[i]=i;
      this.activeOrder=this.order.subarray(0,limit);
    }
    hologramPose(time,this.pose);
    const dt=Math.max(0,Math.min(.05,Number.isFinite(delta)?delta:0));
    const steps=Math.max(1,Math.ceil(dt*120)), h=dt/steps, damping=Math.pow(.9,h*60);
    const physical=!reduced && (pointer.active || this.moving);
    let energy=0;
    for (let i=0;i<limit;i++) {
      const p=this.particles[i], k=i*3;
      const target=projectHologramPoint(this.points,i,time,voice,this.projected,this.pose,p.theta,this.baseLengths[i]);
      let ox=this.initialized && !reduced ? p.x-this.rest[k] : 0;
      let oy=this.initialized && !reduced ? p.y-this.rest[k+1] : 0;
      let oz=this.initialized && !reduced ? p.z-this.rest[k+2] : 0;
      if (physical && dt>0) {
        const perspective=2.65/(3.7-target.z);
        const dx=target.cameraX+ox-pointer.x*Math.max(1,aspect)/perspective;
        const dy=target.cameraY+oy-pointer.y*Math.max(1,1/aspect)/perspective;
        const distance=Math.hypot(dx,dy), falloff=Math.max(0,1-distance/.43)**2;
        const force=pointer.active ? Math.min(22,.12/(distance*distance+.012))*falloff*(.25+.75*target.front) : 0;
        const nx=distance>.001?dx/distance:Math.cos(p.theta), ny=distance>.001?dy/distance:Math.sin(p.theta);
        const ax=nx*force+(pointer.active?clamp(pointer.vx,12)*falloff*.9:0);
        const ay=ny*force+(pointer.active?clamp(pointer.vy,12)*falloff*.9:0);
        for(let s=0;s<steps;s++) {
          p.vx=clamp((p.vx+(ax-65*ox)/p.mass*h)*damping,2.2);
          p.vy=clamp((p.vy+(ay-65*oy)/p.mass*h)*damping,2.2);
          p.vz=clamp((p.vz+(force*.22-65*oz)/p.mass*h)*damping,2.2);
          ox+=p.vx*h; oy+=p.vy*h; oz+=p.vz*h;
          if(Math.abs(ox)>.24){ox=clamp(ox,.24);p.vx*=.35;}
          if(Math.abs(oy)>.24){oy=clamp(oy,.24);p.vy*=.35;}
          if(Math.abs(oz)>.24){oz=clamp(oz,.24);p.vz*=.35;}
        }
        energy=Math.max(energy,Math.abs(ox),Math.abs(oy),Math.abs(oz),Math.abs(p.vx),Math.abs(p.vy),Math.abs(p.vz));
      } else if(reduced) { p.vx=0;p.vy=0;p.vz=0; }
      this.rest[k]=target.cameraX;this.rest[k+1]=target.cameraY;this.rest[k+2]=target.z;
      p.x=target.cameraX+ox;p.y=target.cameraY+oy;p.z=target.z+oz;
      const front=Math.max(0,Math.min(1,(p.z+1.1)/2.2));
      const depth=Math.max(0,Math.min(1,(p.z+.2)/.9)), near=depth*depth*(3-2*depth);
      this.fronts[i]=front;
      this.opacities[i]=(.20+.15*p.seed)*(1-near)+(.85+.13*p.seed)*near;
      this.radii[i]=p.baseRadius*(.65+.35*front)+voice.speaking*voice.energy*.15;
    }
    this.initialized=true;
    this.moving=energy>.00004;
    if(physical && !this.moving) {
      for(let i=0;i<limit;i++) {
        const p=this.particles[i],k=i*3;
        p.x=this.rest[k];p.y=this.rest[k+1];p.z=this.rest[k+2];p.vx=0;p.vy=0;p.vz=0;
      }
    }
    this.activeOrder.sort((a,b)=>this.particles[a].z-this.particles[b].z || a-b);
  }
}
