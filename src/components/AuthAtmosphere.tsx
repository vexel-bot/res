import React from 'react';
import { Image, Lightbulb, Play, Send } from 'lucide-react';
import './AuthAtmosphere.css';

type PanelKind = 'landscape' | 'leaves' | 'video' | 'calendar' | 'results' | 'idea' | 'publication' | 'far';
const panels: { kind: PanelKind; className: string }[] = [
  { kind: 'far', className: 'gallery-far-left' },
  { kind: 'publication', className: 'gallery-publication' },
  { kind: 'landscape', className: 'gallery-landscape' },
  { kind: 'idea', className: 'gallery-idea' },
  { kind: 'video', className: 'gallery-video' },
  { kind: 'far', className: 'gallery-far-right' },
  { kind: 'calendar', className: 'gallery-calendar' },
  { kind: 'leaves', className: 'gallery-leaves' },
  { kind: 'results', className: 'gallery-results' },
];

function PanelContent({ kind }: { kind: PanelKind }) {
  if (kind === 'landscape' || kind === 'leaves') return <>
    <img src={kind === 'leaves' ? '/auth/clicko-leaves.jpg' : '/auth/clicko-mountain.jpg'} alt="" width={kind === 'leaves' ? 1024 : 1448} height={kind === 'leaves' ? 1536 : 1086} decoding="async" />
    <span className="gallery-caption">{kind === 'leaves' ? 'Conteúdo' : 'Ideia'}</span>
  </>;
  if (kind === 'video') return <div className="gallery-video-content">
    <div className="gallery-video-preview"><Play size={22} fill="currentColor" strokeWidth={0} /><span /></div>
    <div className="gallery-timeline">{[0, 1, 2, 3, 4].map(i => <i key={i} style={{ backgroundPosition: `${i * 24}% center` }} />)}<b /></div>
    <span className="gallery-caption">Vídeo</span>
  </div>;
  if (kind === 'calendar') return <div className="gallery-mini-content">
    <span className="gallery-heading">Planejamento</span>
    <div className="gallery-week">{['S', 'T', 'Q', 'Q', 'S', 'S', 'D'].map((day, i) => <span key={i}>{day}</span>)}</div>
    <div className="gallery-days">{Array.from({ length: 28 }, (_, i) => <span key={i} className={i === 17 ? 'is-scheduled' : ''}>{i + 1}{[4, 11, 23].includes(i) && <i />}</span>)}</div>
  </div>;
  if (kind === 'results') return <div className="gallery-mini-content">
    <span className="gallery-heading">Resultados</span>
    <div className="gallery-bars">{[24, 38, 32, 57, 46, 72, 88].map((height, i) => <i key={i} style={{ height: `${height}%` }} />)}</div>
    <div className="gallery-chart-baseline"><span>Criação</span><span>Alcance</span></div>
  </div>;
  if (kind === 'idea') return <div className="gallery-symbol"><Lightbulb size={29} strokeWidth={1.3} /></div>;
  if (kind === 'publication') return <div className="gallery-mini-content gallery-publication-content"><Send size={18} strokeWidth={1.2} /><span className="gallery-heading">Publicação</span><div className="gallery-draft"><i /><i /><i /></div><span className="gallery-draft-status" /></div>;
  return <div className="gallery-far-content"><Image size={24} strokeWidth={1} /><span /><span /></div>;
}

/** Decorative CSS 3D gallery. It never receives focus, events, account data or analytics. */
export const AuthAtmosphere = React.memo(function AuthAtmosphere({ mode = 'login' }: { mode?: string }) {
  const sceneRef = React.useRef<HTMLDivElement>(null);
  const modeRef = React.useRef(mode);
  React.useEffect(() => { modeRef.current = mode; }, [mode]);

  React.useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const compact = matchMedia('(max-width: 700px), (pointer: coarse)');
    const host = scene.closest('main');
    const card = host?.querySelector<HTMLElement>('.clicko-auth-card');
    let width = innerWidth, height = innerHeight;
    let targetX = 0, targetY = 0, x = 0, y = 0, vx = 0, vy = 0;
    let route = modeRef.current === 'signup' ? 1 : 0, scroll = 0;
    let frame = 0, last = 0, pointerTime = 0;
    let lightX = 50, lightY = 50, illumination = 0;
    // Avoid invalidating inherited scene styles once the damped camera settles.
    const writeStyle = (element: HTMLElement, property: string, value: string) => {
      if (element.style.getPropertyValue(property) !== value) element.style.setProperty(property, value);
    };
    let bounds = card?.getBoundingClientRect();
    const economical = navigator.hardwareConcurrency <= 4;
    const measure = () => { width = innerWidth; height = innerHeight; bounds = card?.getBoundingClientRect(); };
    const observer = new ResizeObserver(measure);
    if (card) observer.observe(card);
    const move = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse' || reduced.matches || compact.matches) return;
      targetX = (event.clientX / width - 0.5) * 2;
      targetY = (event.clientY / height - 0.5) * 2;
      pointerTime = performance.now();
      if (bounds) {
        lightX = Math.max(0, Math.min(100, (event.clientX - bounds.left) / bounds.width * 100));
        lightY = Math.max(0, Math.min(100, (event.clientY - bounds.top) / bounds.height * 100));
      }
    };
    const leave = () => { targetX = 0; targetY = 0; pointerTime = 0; };
    const reset = () => {
      scene.style.setProperty('--camera-x', '0');
      scene.style.setProperty('--camera-y', '0');
      scene.style.setProperty('--scroll-depth', '0px');
      card?.style.removeProperty('--auth-proximity');
    };
    const render = (time: number) => {
      frame = 0;
      if (document.hidden || reduced.matches) return;
      frame = requestAnimationFrame(render);
      if (time - last < (compact.matches || economical ? 50 : 32)) return;
      const dt = Math.min((time - (last || time)) / 16.67, 3);
      last = time;
      const active = time - pointerTime < 2800;
      const tx = active ? targetX : 0, ty = active ? targetY : 0;
      // Critically damped, bounded camera response. No React renders per frame.
      vx = (vx + (tx - x) * 0.025 * dt) * Math.pow(0.76, dt);
      vy = (vy + (ty - y) * 0.025 * dt) * Math.pow(0.76, dt);
      x += vx * dt; y += vy * dt;
      route += ((modeRef.current === 'signup' ? 1 : 0) - route) * (1 - Math.exp(-dt / 23));
      scroll += (Math.min(window.scrollY, height) * 0.035 - scroll) * 0.055;
      illumination += ((active ? 0.7 : 0) - illumination) * 0.07;
      writeStyle(scene, '--camera-x', x.toFixed(4));
      writeStyle(scene, '--camera-y', y.toFixed(4));
      writeStyle(scene, '--gallery-route', route.toFixed(4));
      writeStyle(scene, '--scroll-depth', `${scroll.toFixed(2)}px`);
      if (card) {
        writeStyle(card, '--auth-light-x', `${lightX.toFixed(1)}%`);
        writeStyle(card, '--auth-light-y', `${lightY.toFixed(1)}%`);
        writeStyle(card, '--auth-proximity', illumination.toFixed(3));
      }
    };
    const resume = () => {
      cancelAnimationFrame(frame); frame = 0; last = 0;
      scene.dataset.still = String(reduced.matches || document.hidden);
      if (reduced.matches) reset();
      if (!document.hidden && !reduced.matches) frame = requestAnimationFrame(render);
    };
    window.addEventListener('pointermove', move, { passive: true });
    document.documentElement.addEventListener('pointerleave', leave);
    window.addEventListener('blur', leave);
    window.addEventListener('resize', measure, { passive: true });
    window.addEventListener('scroll', measure, { passive: true });
    document.addEventListener('visibilitychange', resume);
    reduced.addEventListener('change', resume);
    resume();
    return () => {
      cancelAnimationFrame(frame); observer.disconnect();
      window.removeEventListener('pointermove', move);
      document.documentElement.removeEventListener('pointerleave', leave);
      window.removeEventListener('blur', leave);
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure);
      document.removeEventListener('visibilitychange', resume);
      reduced.removeEventListener('change', resume);
      reset();
    };
  }, []);

  return <div ref={sceneRef} className="clicko-auth-gallery" aria-hidden="true">
    <div className="gallery-perspective"><div className="gallery-world">
      {panels.map(({ kind, className }, index) => <div key={className} className={`gallery-position ${className}`} style={{ '--float-delay': `${-index * 2.9}s`, '--float-duration': `${19 + index * 1.7}s` } as React.CSSProperties}>
        <div className="gallery-float"><div className="gallery-panel"><PanelContent kind={kind} /></div></div>
      </div>)}
      <div className="gallery-micro gallery-micro--layers"><div className="gallery-micro-drift"><i /><i /><i /></div></div>
      <div className="gallery-micro gallery-micro--lens"><div className="gallery-micro-drift"><i /><i /></div></div>
      <div className="gallery-micro gallery-micro--fold"><div className="gallery-micro-drift"><i /><i /></div></div>
      <div className="gallery-micro gallery-micro--spark"><div className="gallery-micro-drift"><i /></div></div>
    </div></div>
    <div className="gallery-center-shade" />
    <div className="gallery-edge-shade" />
  </div>;
});
