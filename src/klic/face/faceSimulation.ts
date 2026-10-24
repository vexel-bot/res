import { generateAIFaceSphere } from './sphereGenerator';
import { faceVoiceModulation } from './voiceModulation';
import type { Particle3D } from './types';
import type { HologramResonance } from '../hologramModel';
import type { HologramPointer } from '../hologramDynamics';

const clamp=(n:number,max:number)=>Math.max(-max,Math.min(max,n));
const seedRandom=()=>{let n=0x434c4943;return()=>{n^=n<<13;n^=n>>>17;n^=n<<5;return (n>>>0)/4294967296;};};

/** Interleave the unmodified source geometry so adaptive prefixes preserve every ribbon/hemisphere. */
function balancedGeometry(maxCount:number) {
  const random=seedRandom(),bands:Array<Particle3D[]>=Array.from({length:72},()=>[]);
  for(const p of generateAIFaceSphere(1,random))bands[p.ribbonIndex].push(p);
  for(const band of bands)for(let i=band.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[band[i],band[j]]=[band[j],band[i]];}
  const result:Particle3D[]=[];
  for(let n=0;n<115;n++)for(const band of bands)if(band[n]&&result.length<maxCount)result.push(band[n]);
  return result;
}

/** Source harmonic/spring simulation, normalized to the existing Clicko component's footprint. */
export class KlicFaceSimulation {
  readonly particles:Particle3D[];
  readonly order:Uint32Array;
  readonly fronts:Float32Array;
  readonly opacities:Float32Array;
  readonly radii:Float32Array;
  readonly screenX:Float32Array;
  readonly screenY:Float32Array;
  readonly depths:Float32Array;
  private activeOrder:Uint32Array;
  private readonly cosPhi:Float64Array;
  private readonly cosPower:Float64Array;
  private readonly cosSpeech:Float64Array;
  private initialized=false;
  private phase=0;
  private rotation=0;
  private shock={active:false,radius:0,x:0,y:0};

  constructor(count=Infinity) {
    this.particles=balancedGeometry(count);
    const n=this.particles.length;
    this.order=Uint32Array.from({length:n},(_,i)=>i);this.activeOrder=this.order;
    this.fronts=new Float32Array(n);this.opacities=new Float32Array(n);this.radii=new Float32Array(n);
    this.screenX=new Float32Array(n);this.screenY=new Float32Array(n);this.depths=new Float32Array(n);
    this.cosPhi=Float64Array.from(this.particles,p=>Math.cos(p.basePhi));
    this.cosPower=Float64Array.from(this.cosPhi,n=>Math.pow(n,1.4));
    this.cosSpeech=Float64Array.from(this.cosPhi,n=>Math.pow(n,1.2));
  }
  reset(){this.initialized=false;this.shock.active=false;for(const p of this.particles){p.vx=0;p.vy=0;p.vz=0;}}
  burst(pointer:HologramPointer){this.shock={active:true,radius:.025,x:pointer.x,y:pointer.y};}

  step(time:number,delta:number,voice:HologramResonance,pointer:HologramPointer,aspect=1,reduced=false,count=this.particles.length) {
    const limit=Math.min(count,this.particles.length),dt=reduced?0:Math.max(0,Math.min(.05,Number.isFinite(delta)?delta:0));
    if(this.activeOrder.length!==limit){for(let i=0;i<limit;i++)this.order[i]=i;this.activeOrder=this.order.subarray(0,limit);}
    const mod=faceVoiceModulation(time,voice),listen=voice.listening,speak=voice.speaking,volume=mod.volume;
    if(!this.initialized){this.phase=time*1.5;this.rotation=time*.132;}
    else {this.phase+=dt*mod.ribbonWaveSpeed;this.rotation+=dt*mod.rotationSpeed;}
    const tilt=.22+Math.sin(time*.35)*.04,cx=Math.cos(tilt),sx=Math.sin(tilt),cy=Math.cos(this.rotation),sy=Math.sin(this.rotation);
    const steps=Math.max(1,Math.ceil(dt*120)),h=dt/steps,friction=Math.pow(.90,h*60);
    const speed=Math.hypot(pointer.vx,pointer.vy),influence=Math.min(.75,.43+speed*.015);
    const shock=this.shock;
    if(shock.active){shock.radius+=dt*4.36;if(shock.radius>1.3||reduced)shock.active=false;}
    for(let i=0;i<limit;i++) {
      const p=this.particles[i],theta=p.theta,phi=p.basePhi,cosPhi=this.cosPhi[i],phase=this.phase;
      const idle=.30*Math.sin(2*theta+phase)*cosPhi+.10*Math.sin(3*theta-phase*.7)*this.cosPower[i];
      const listening=listen ? .28*Math.sin(2*theta+phase)*cosPhi+.08*Math.sin(4*theta-phase)*this.cosPower[i]
        +Math.sin(phi*(4.5+voice.low*.5)-time*(6+voice.low))*(.012+volume*.12) : 0;
      const speaking=speak ? mod.waveAmplitude*Math.sin(2*theta+phase)*cosPhi
        +mod.waveAmplitude*.4*Math.sin(3*theta-phase*.9)*this.cosSpeech[i] : 0;
      const wave=idle*(1-listen-speak)+listening*listen+speaking*speak;
      const dynamicPhi=clamp(phi+wave,Math.PI*.485);
      const jitter=listen*volume*Math.sin(time*(18+voice.high*2)+p.seed*8)*.04;
      const radius=mod.pulseScale*(1+.025*Math.sin(2*theta+time*.8)*cosPhi+jitter
        +speak*Math.sin(theta*3+time*4)*cosPhi*.06*volume);
      const ring=radius*Math.cos(dynamicPhi),tx=ring*Math.cos(theta),ty=radius*Math.sin(dynamicPhi),tz=ring*Math.sin(theta);
      if(!this.initialized||reduced){p.x=tx;p.y=ty;p.z=tz;p.vx=0;p.vy=0;p.vz=0;}
      let fx=0,fy=0,fz=0;
      if((pointer.active||shock.active)&&!reduced){
        const rx=p.x*cy+p.z*sy,z1=-p.x*sy+p.z*cy,ry=p.y*cx-z1*sx,rz=p.y*sx+z1*cx;
        const perspective=4.5/(4.85+rz);
        if(pointer.active){
          const dx=rx-pointer.x*Math.max(1,aspect)/(.76*perspective),dy=ry+pointer.y*Math.max(1,1/aspect)/(.76*perspective);
          const distance=Math.hypot(dx,dy),factor=Math.max(0,1-distance/influence)**1.9;
          const repel=Math.min(90,55*factor),inv=1/Math.max(.015,distance);
          fx=dx*inv*repel+pointer.vx*factor*3;fy=dy*inv*repel-pointer.vy*factor*3;
          fz=(rz>0?1:-1)*repel*.7;
        }
        if(shock.active){
          const dx=rx*perspective*.76-shock.x*Math.max(1,aspect),dy=ry*perspective*.76+shock.y*Math.max(1,1/aspect);
          const distance=Math.hypot(dx,dy),intensity=Math.max(0,1-Math.abs(distance-shock.radius)/.16)*70;
          fx+=dx/Math.max(.015,distance)*intensity;fy+=dy/Math.max(.015,distance)*intensity;fz+=(rz>0?1:-1)*intensity*.7;
        }
        // Inverse camera transform, as in the source component's shatter impulse.
        const unY=fy*cx+fz*sx,unZ=-fy*sx+fz*cx;
        const worldX=fx*cy-unZ*sy,worldZ=fx*sy+unZ*cy;fx=worldX;fy=unY;fz=worldZ;
      }
      if(!reduced)for(let s=0;s<steps;s++) {
        // Original .048 spring / .90 friction at 60 Hz, integrated in seconds with stable substeps.
        p.vx=clamp((p.vx+((tx-p.x)*172.8+fx)/p.mass*h)*friction,6);
        p.vy=clamp((p.vy+((ty-p.y)*172.8+fy)/p.mass*h)*friction,6);
        p.vz=clamp((p.vz+((tz-p.z)*172.8+fz)/p.mass*h)*friction,6);
        p.x+=p.vx*h;p.y+=p.vy*h;p.z+=p.vz*h;
        const distance=Math.hypot(p.x-tx,p.y-ty,p.z-tz);
        if(distance>.72){const factor=.72/distance;p.x=tx+(p.x-tx)*factor;p.y=ty+(p.y-ty)*factor;p.z=tz+(p.z-tz)*factor;p.vx*=.6;p.vy*=.6;p.vz*=.6;}
      }
      const rx=p.x*cy+p.z*sy,z1=-p.x*sy+p.z*cy,ry=p.y*cx-z1*sx,rz=p.y*sx+z1*cx;
      const perspective=4.5/(4.85+rz),front=Math.max(0,Math.min(1,(-rz+1.2)/2.4));
      this.screenX[i]=rx*perspective*.38;this.screenY[i]=ry*perspective*.38;
      this.depths[i]=-rz;this.fronts[i]=front;
      this.opacities[i]=Math.min(.98,.22+front*.74+volume*(listen+speak)*.08);
      this.radii[i]=Math.max(.55,(.7+front*.65+speak*volume*.35)*p.baseRadius*perspective);
    }
    this.initialized=true;
    this.activeOrder.sort((a,b)=>this.depths[a]-this.depths[b]||a-b);
  }
}
