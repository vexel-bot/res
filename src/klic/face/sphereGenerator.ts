import type { Particle3D } from './types';

/** Original 72-ribbon geometry from ai-studios-novo/src/utils/sphereGenerator.ts.
 * The optional random source makes regression tests reproducible, not the animation random.
 */
export function generateAIFaceSphere(radius:number, random:()=>number=Math.random):Particle3D[] {
  const particles:Particle3D[]=[];
  const ribbonCount=72;
  for(let r=0;r<ribbonCount;r++) {
    const v=-.94+(1.88*(r+.5))/ribbonCount,basePhi=Math.asin(v),cosPhi=Math.cos(basePhi);
    const dotsOnRibbon=Math.max(16,Math.floor(115*cosPhi));
    for(let i=0;i<dotsOnRibbon;i++) {
      const theta=i/dotsOnRibbon*Math.PI*2;
      const waveElevation=.30*Math.sin(2*theta+.4)*cosPhi+.10*Math.sin(3*theta-.2)*Math.pow(cosPhi,1.4);
      const phi=Math.max(-Math.PI*.485,Math.min(Math.PI*.485,basePhi+waveElevation));
      const rMod=radius*(1+.025*Math.sin(2*theta)*Math.cos(phi));
      const bx=rMod*Math.cos(phi)*Math.cos(theta),by=rMod*Math.sin(phi),bz=rMod*Math.cos(phi)*Math.sin(theta);
      particles.push({baseX:bx,baseY:by,baseZ:bz,x:bx,y:by,z:bz,vx:0,vy:0,vz:0,
        baseRadius:.75+random()*.45,mass:.7+random()*.4,ribbonIndex:r,theta,basePhi,seed:random()*Math.PI*2,
        isCircuit:false,circuitProgress:0,circuitSpeed:0,circuitPhaseOffset:0,circuitPathId:0});
    }
  }
  return particles;
}
