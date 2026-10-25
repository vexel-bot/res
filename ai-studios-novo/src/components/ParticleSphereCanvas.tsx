import React, { useEffect, useRef, useState } from 'react';
import { Particle3D, VoiceState } from '../types';
import { generateAIFaceSphere } from '../utils/sphereGenerator';
import { voiceAnalyzer } from '../utils/voiceAnalyzer';

interface ProjectedParticle {
  screenX: number;
  screenY: number;
  rz: number;
  size: number;
  color: string;
}

export const ParticleSphereCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const particlesRef = useRef<Particle3D[]>([]);
  const projectedRef = useRef<ProjectedParticle[]>([]);

  // Voice Interaction State: 'idle' | 'listening' | 'speaking'
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [, setIsMicOn] = useState(false);

  // Mouse interaction state
  const mouseRef = useRef({
    x: -9999,
    y: -9999,
    prevX: -9999,
    prevY: -9999,
    vx: 0,
    vy: 0,
    isHovered: false,
  });

  // Smooth rotation angles
  const rotationRef = useRef({
    rotX: 0.22,
    rotY: 0,
  });

  // Shockwave burst state on click
  const shockwaveRef = useRef<{
    active: boolean;
    radius: number;
    maxRadius: number;
    strength: number;
    cx: number;
    cy: number;
  }>({
    active: false,
    radius: 0,
    maxRadius: 450,
    strength: 0,
    cx: 0,
    cy: 0,
  });

  // Initialize particles based on screen size
  const init = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    const minDim = Math.min(rect.width, rect.height);
    const radius = Math.max(110, minDim * 0.25);

    particlesRef.current = generateAIFaceSphere(radius);
    projectedRef.current = new Array(particlesRef.current.length);
  };

  useEffect(() => {
    init();

    const handleResize = () => {
      init();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Keyboard shortcuts for testing voice modes
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '1') {
        setVoiceState('idle');
      } else if (e.key === '2') {
        setVoiceState('listening');
      } else if (e.key === '3') {
        setVoiceState('speaking');
      } else if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        setVoiceState((prev) => (prev === 'idle' ? 'listening' : prev === 'listening' ? 'speaking' : 'idle'));
      } else if (e.key === 'm' || e.key === 'M') {
        handleToggleMic();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleToggleMic = async () => {
    const active = await voiceAnalyzer.toggleMicrophone();
    setIsMicOn(active);
    if (active) {
      setVoiceState('listening');
    }
  };

  // Mouse / Pointer handlers
  const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const curX = e.clientX - rect.left;
    const curY = e.clientY - rect.top;

    const m = mouseRef.current;
    if (m.prevX !== -9999) {
      m.vx = curX - m.prevX;
      m.vy = curY - m.prevY;
    }
    m.prevX = curX;
    m.prevY = curY;
    m.x = curX;
    m.y = curY;
    m.isHovered = true;
  };

  const handlePointerLeave = () => {
    const m = mouseRef.current;
    m.x = -9999;
    m.y = -9999;
    m.prevX = -9999;
    m.prevY = -9999;
    m.vx = 0;
    m.vy = 0;
    m.isHovered = false;
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    // Only trigger shockwave on direct click
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const curX = e.clientX - rect.left;
    const curY = e.clientY - rect.top;

    shockwaveRef.current = {
      active: true,
      radius: 5,
      maxRadius: Math.max(rect.width, rect.height) * 0.45,
      strength: 28,
      cx: curX,
      cy: curY,
    };
  };

  // Main animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId = 0;
    const startTime = performance.now();

    const render = (currentTime: number) => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = rect.width;
      const height = rect.height;
      const time = (currentTime - startTime) * 0.001;

      const centerX = width / 2;
      const centerY = height / 2;
      const minDim = Math.min(width, height);
      const sphereRadius = Math.max(110, minDim * 0.25);

      // 1. Pure black canvas
      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, width, height);

      // Voice modulation parameters
      const voiceMod = voiceAnalyzer.getVoiceModulation(voiceState, time);

      // Rotation timing: accelerates slightly when speaking, poised when listening
      const rotSpeed = voiceState === 'speaking' ? 0.0035 : voiceState === 'listening' ? 0.0016 : 0.0022;
      rotationRef.current.rotY += rotSpeed;
      rotationRef.current.rotX = 0.22 + Math.sin(time * 0.35) * 0.04;

      const rotX = rotationRef.current.rotX;
      const rotY = rotationRef.current.rotY;

      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);

      const fov = 850;
      const m = mouseRef.current;
      m.vx *= 0.86;
      m.vy *= 0.86;
      const mouseSpeed = Math.sqrt(m.vx * m.vx + m.vy * m.vy);
      const repulsionRadius = Math.min(160, 95 + mouseSpeed * 1.8);

      // Shockwave advancement
      const sw = shockwaveRef.current;
      if (sw.active) {
        sw.radius += 16;
        if (sw.radius >= sw.maxRadius) {
          sw.active = false;
        }
      }

      const particles = particlesRef.current;
      const count = particles.length;

      const spring = 0.048;
      const friction = 0.90;

      // Voice-specific wave parameters
      const wavePhase = time * voiceMod.ribbonWaveSpeed;
      const currentRadius = sphereRadius * voiceMod.pulseScale;

      for (let i = 0; i < count; i++) {
        const p = particles[i];

        // 2. Harmonic wave undulation adapted for voice state
        const theta = p.theta;
        const basePhi = p.basePhi;
        const cosPhi = Math.cos(basePhi);

        let dynamicWave = 0;
        let rMod = currentRadius;

        if (voiceState === 'idle') {
          // Serene resting wave
          dynamicWave =
            0.30 * Math.sin(2 * theta + wavePhase) * cosPhi +
            0.10 * Math.sin(3 * theta - wavePhase * 0.7) * Math.pow(cosPhi, 1.4);
          rMod *= 1 + 0.025 * Math.sin(2 * theta + time * 0.8) * Math.cos(basePhi);
        } else if (voiceState === 'listening') {
          // Listening mode:
          // Attentive acoustic ripples: concentric frequency waves traveling across the ribbons
          // Plus high-frequency micro-vibrations like capturing audio spectrum
          const rippleFrequency = 4.5;
          const ripplePhase = time * 6.0;
          const radialRipple = Math.sin(basePhi * rippleFrequency - ripplePhase) * 0.12 * (1 + voiceMod.volume);

          dynamicWave =
            0.28 * Math.sin(2 * theta + wavePhase) * cosPhi +
            0.08 * Math.sin(4 * theta - wavePhase) * Math.pow(cosPhi, 1.4) +
            radialRipple;

          // Micro-shimmer on individual particles capturing frequencies
          const audioJitter = Math.sin(time * 18.0 + p.seed * 8.0) * (0.015 + voiceMod.volume * 0.04);
          rMod *= 1 + audioJitter;
        } else {
          // Speaking mode:
          // Vocal resonance: expressive undulation flaring with speech syllables
          const speechSwell = voiceMod.waveAmplitude;
          dynamicWave =
            speechSwell * Math.sin(2 * theta + wavePhase) * cosPhi +
            (speechSwell * 0.4) * Math.sin(3 * theta - wavePhase * 0.9) * Math.pow(cosPhi, 1.2);

          // Vocal expansion bursts along equatorial bands
          const vocalExpansion = Math.sin(theta * 3 + time * 4.0) * Math.cos(basePhi) * (0.06 * voiceMod.volume);
          rMod *= 1 + vocalExpansion;
        }

        const currentPhi = Math.max(-Math.PI * 0.485, Math.min(Math.PI * 0.485, basePhi + dynamicWave));

        // Resting 3D coordinate on the voice-animated sphere
        const targetBx = rMod * Math.cos(currentPhi) * Math.cos(theta);
        const targetBy = rMod * Math.sin(currentPhi);
        const targetBz = rMod * Math.cos(currentPhi) * Math.sin(theta);

        // 3. 3D Rotation transform
        const x1 = p.x * cosY + p.z * sinY;
        const y1 = p.y;
        const z1 = -p.x * sinY + p.z * cosY;

        const rx = x1;
        const ry = y1 * cosX - z1 * sinX;
        const rz = y1 * sinX + z1 * cosX;

        // Perspective projection
        const persp = fov / (fov + rz + sphereRadius * 0.35);
        const screenX = centerX + rx * persp;
        const screenY = centerY + ry * persp;

        // 4. Detailed Shatter on mouse hover
        if (m.x !== -9999) {
          const dx = screenX - m.x;
          const dy = screenY - m.y;
          const distSq = dx * dx + dy * dy;
          const radSq = repulsionRadius * repulsionRadius;

          if (distSq < radSq && distSq > 0.01) {
            const dist = Math.sqrt(distSq);
            const normX = dx / dist;
            const normY = dy / dist;

            const factor = Math.pow(1 - dist / repulsionRadius, 1.9);
            const repel = (factor * 22) / p.mass;

            const flickX = m.vx * 0.4;
            const flickY = m.vy * 0.4;

            const camImpulseX = normX * repel + flickX;
            const camImpulseY = normY * repel + flickY;
            const camImpulseZ = (rz > 0 ? 1 : -1) * repel * 0.7 + (Math.random() - 0.5) * 5;

            const unY1 = camImpulseY * cosX + camImpulseZ * sinX;
            const unZ1 = -camImpulseY * sinX + camImpulseZ * cosX;
            const modelImpulseX = camImpulseX * cosY - unZ1 * sinY;
            const modelImpulseY = unY1;
            const modelImpulseZ = camImpulseX * sinY + unZ1 * cosY;

            p.vx += modelImpulseX;
            p.vy += modelImpulseY;
            p.vz += modelImpulseZ;
          }
        }

        // Shockwave on click
        if (sw.active) {
          const sdx = screenX - sw.cx;
          const sdy = screenY - sw.cy;
          const sdist = Math.hypot(sdx, sdy);
          const diff = Math.abs(sdist - sw.radius);

          if (diff < 35 && sdist > 0.1) {
            const intensity = (1 - diff / 35) * (sw.strength / p.mass);
            const snx = sdx / sdist;
            const sny = sdy / sdist;

            const camSx = snx * intensity;
            const camSy = sny * intensity;
            const camSz = (rz > 0 ? 1 : -1) * intensity * 0.7;

            const unY1 = camSy * cosX + camSz * sinX;
            const unZ1 = -camSy * sinX + camSz * cosX;
            const modelSx = camSx * cosY - unZ1 * sinY;
            const modelSy = unY1;
            const modelSz = camSx * sinY + unZ1 * cosY;

            p.vx += modelSx;
            p.vy += modelSy;
            p.vz += modelSz;
          }
        }

        // 5. Elastic Hooke's return (reconstituting smoothly)
        const homeDx = targetBx - p.x;
        const homeDy = targetBy - p.y;
        const homeDz = targetBz - p.z;

        p.vx += (homeDx * spring) / p.mass;
        p.vy += (homeDy * spring) / p.mass;
        p.vz += (homeDz * spring) / p.mass;

        p.vx *= friction;
        p.vy *= friction;
        p.vz *= friction;

        p.x += p.vx;
        p.y += p.vy;
        p.z += p.vz;

        // 6. Dot size & Palette #6EB8F5 with Voice Luminosity
        const normZ = rz / sphereRadius;
        const depth = Math.max(0, Math.min(1, (normZ + 1.2) / 2.4));

        // When speaking, syllables cause dots to pulse slightly in size
        const voiceSizePulse = voiceState === 'speaking' ? voiceMod.volume * 0.35 : 0;
        const dotSize = Math.max(0.55, (0.7 + depth * 0.65 + voiceSizePulse) * p.baseRadius * persp);

        // Color gradation centered on #6EB8F5 (110, 184, 245)
        // Foreground points become more luminous during speaking or listening
        const voiceGlow = voiceState === 'speaking' ? voiceMod.volume * 35 : voiceState === 'listening' ? 15 : 0;
        const rVal = Math.min(255, Math.floor(65 + depth * 85 + voiceGlow));
        const gVal = Math.min(255, Math.floor(140 + depth * 68 + voiceGlow * 0.8));
        const bVal = 245;
        const alpha = Math.min(1.0, 0.22 + depth * 0.74 + (voiceState !== 'idle' ? 0.08 : 0));
        const color = `rgba(${rVal}, ${gVal}, ${bVal}, ${alpha.toFixed(2)})`;

        projectedRef.current[i] = {
          screenX,
          screenY,
          rz,
          size: dotSize,
          color,
        };
      }

      // Depth sorting for correct 3D perspective occlusion
      projectedRef.current.sort((a, b) => a.rz - b.rz);

      // Render fine stippled points with high precision
      const projCount = projectedRef.current.length;
      for (let i = 0; i < projCount; i++) {
        const item = projectedRef.current[i];
        ctx.beginPath();
        ctx.arc(item.screenX, item.screenY, item.size, 0, Math.PI * 2);
        ctx.fillStyle = item.color;
        ctx.fill();
      }

      ctx.restore();
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [voiceState]);

  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
        onPointerDown={handlePointerDown}
        className="fixed inset-0 w-full h-full cursor-crosshair touch-none select-none"
      />
    </div>
  );
};
