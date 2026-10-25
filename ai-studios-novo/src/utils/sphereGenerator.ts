import { Particle3D } from '../types';

export function generateAIFaceSphere(radius: number): Particle3D[] {
  const particles: Particle3D[] = [];
  
  // High resolution: 72 ribbons and ~5,200 fine stippled dots for ultra-detailed texture
  const ribbonCount = 72;

  for (let r = 0; r < ribbonCount; r++) {
    // Distribute from south to north with slight cosine density
    const v = -0.94 + (1.88 * (r + 0.5)) / ribbonCount;
    const basePhi = Math.asin(v);

    const cosPhi = Math.cos(basePhi);
    // Number of dots proportional to circumference for uniform spacing
    const dotsOnRibbon = Math.max(16, Math.floor(115 * cosPhi));

    for (let i = 0; i < dotsOnRibbon; i++) {
      const u = i / dotsOnRibbon;
      const theta = u * Math.PI * 2;

      // The signature harmonic wave contour visible in the reference image
      // Sinusoidal saddle-wave that curves gently across the sphere
      const waveElevation =
        0.30 * Math.sin(2 * theta + 0.4) * cosPhi +
        0.10 * Math.sin(3 * theta - 0.2) * Math.pow(cosPhi, 1.4);

      const phi = Math.max(-Math.PI * 0.485, Math.min(Math.PI * 0.485, basePhi + waveElevation));
      
      // Radius modulation for organic contour depth
      const rMod = radius * (1 + 0.025 * Math.sin(2 * theta) * Math.cos(phi));

      const bx = rMod * Math.cos(phi) * Math.cos(theta);
      const by = rMod * Math.sin(phi);
      const bz = rMod * Math.cos(phi) * Math.sin(theta);

      // Fine, detailed stippling: tiny dot radius (0.75px to 1.35px)
      const baseRadius = 0.75 + Math.random() * 0.45;
      const mass = 0.7 + Math.random() * 0.4;

      particles.push({
        baseX: bx,
        baseY: by,
        baseZ: bz,
        x: bx,
        y: by,
        z: bz,
        vx: 0,
        vy: 0,
        vz: 0,
        mass,
        baseRadius,
        ribbonIndex: r,
        theta,
        basePhi,
        seed: Math.random() * Math.PI * 2,
        isCircuit: false,
        circuitProgress: 0,
        circuitSpeed: 0,
        circuitPhaseOffset: 0,
        circuitPathId: 0,
      });
    }
  }

  return particles;
}
