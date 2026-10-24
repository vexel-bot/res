/** Adapted from vexel-bot/res, ai-studios-novo/src/types.ts (68abe189c3cb). */
export type VoiceState = 'idle' | 'listening' | 'speaking';
export interface Particle3D {
  baseX:number; baseY:number; baseZ:number;
  x:number; y:number; z:number;
  vx:number; vy:number; vz:number;
  mass:number; baseRadius:number;
  ribbonIndex:number; theta:number; basePhi:number; seed:number;
  isCircuit:boolean; circuitProgress:number; circuitSpeed:number;
  circuitPhaseOffset:number; circuitPathId:number;
}
