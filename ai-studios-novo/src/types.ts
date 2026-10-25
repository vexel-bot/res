export type VoiceState = 'idle' | 'listening' | 'speaking';

export interface Particle3D {
  // Resting coordinates on the central wavy sphere
  baseX: number;
  baseY: number;
  baseZ: number;

  // Dynamic coordinates in 3D
  x: number;
  y: number;
  z: number;

  // Velocities
  vx: number;
  vy: number;
  vz: number;

  // Physical attributes
  mass: number;
  baseRadius: number;
  
  // Wave & ribbon parameters
  ribbonIndex: number;
  theta: number;
  basePhi: number;
  seed: number;

  // Circuit parameters (kept for interface compatibility)
  isCircuit: boolean;
  circuitProgress: number;
  circuitSpeed: number;
  circuitPhaseOffset: number;
  circuitPathId: number;
}
