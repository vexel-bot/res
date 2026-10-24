// Development-only visual/audio fixture, never imported by the application build.
import { mountKlicHologram } from '../../src/klic/hologramRenderer';
import { analyseKlicAudio, startKlicPlaybackAnalysis } from '../../src/klic/audioAnalysis';
import { SILENT_AUDIO } from '../../src/klic/hologramDynamics';
import '../../src/components/KlicHologram.css';

if (!(import.meta as ImportMeta & {env:{DEV:boolean}}).env.DEV) throw new Error('Development fixture only');
document.body.innerHTML = `<style>
body{margin:0;background:#090909;color:#eee;font:14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:24px;box-sizing:border-box}body.light{background:#fff;color:#111}
nav{display:flex;flex-wrap:wrap;gap:10px}button{padding:10px 16px;border:1px solid #80808055;background:transparent;color:inherit;border-radius:10px;cursor:pointer}
.stage{position:relative;width:min(100%,360px);aspect-ratio:1;margin:50px auto}.orb{position:absolute;inset:0;padding:0;border:0;background:transparent}.klic-hologram{position:absolute;inset:0}output{display:block;text-align:center;font-variant-numeric:tabular-nums}
</style><h1>KLIC — validação local</h1><p>Áudio sintético de teste. Não usa microfone nem serviços externos. Não integra a interface do produto.</p>
<nav><button id="idle">Idle</button><button id="listen">Escuta · sinal de teste</button><button id="speak">Fala · áudio de teste</button><button id="silence">Silêncio</button><button id="theme">Tema claro/escuro</button></nav>
<div class="stage"><button class="orb klic-plasma" aria-label="Interagir com partículas"><span class="klic-hologram" data-active="true"><canvas class="klic-hologram__canvas"></canvas></span></button></div><output id="signal"></output>`;
let signal = SILENT_AUDIO, light = false, stopAudio = () => {}, context:AudioContext | undefined, measuring:number | undefined;
let metrics = 'Aguardando amostra de 120 frames';
const host = document.querySelector<HTMLSpanElement>('.klic-hologram')!, canvas = document.querySelector<HTMLCanvasElement>('canvas')!;
const entity = mountKlicHologram(host, canvas, 'dark', {signal:()=>signal,background:'transparent',onMetrics:value=>{
  metrics=`Canvas 2D · desenho: ${value.drawMs.toFixed(2)} ms · intervalo RAF: ${value.frameMs.toFixed(2)} ms (${(1000/value.frameMs).toFixed(1)} FPS) · ${value.particles} pontos`;
}});
const resetAudio = () => { stopAudio(); stopAudio=()=>{}; if(measuring!==undefined)cancelAnimationFrame(measuring);measuring=undefined;void context?.close();context=undefined;signal=SILENT_AUDIO; };
document.querySelector('#idle')!.addEventListener('click',()=>{resetAudio();entity.setState('idle');});
document.querySelector('#silence')!.addEventListener('click',resetAudio);
document.querySelector('#theme')!.addEventListener('click',()=>{light=!light;document.body.classList.toggle('light',light);entity.setTheme(light?'light':'dark');});
document.querySelector('#listen')!.addEventListener('click',async()=>{
  resetAudio();entity.setState('listening');context=new AudioContext();const active=context;await active.resume();
  const oscillator=active.createOscillator(), gain=active.createGain(), analyser=active.createAnalyser(), mute=active.createGain();
  analyser.fftSize=1024;oscillator.frequency.value=240;gain.gain.value=.06;mute.gain.value=0;
  oscillator.connect(gain);gain.connect(analyser);analyser.connect(mute);mute.connect(active.destination);oscillator.start();
  const samples=new Uint8Array(analyser.fftSize),bins=new Uint8Array(analyser.frequencyBinCount);const start=active.currentTime;
  const measure=()=>{if(context!==active)return;const elapsed=active.currentTime-start;gain.gain.value=.015+.05*(.5+.5*Math.sin(elapsed*3.7));oscillator.frequency.value=240+Math.sin(elapsed*.8)*130;
    analyser.getByteTimeDomainData(samples);analyser.getByteFrequencyData(bins);signal=analyseKlicAudio(samples,bins,active.sampleRate,'microphone',performance.now());measuring=requestAnimationFrame(measure);};measure();
});
document.querySelector('#speak')!.addEventListener('click',()=>{
  resetAudio();entity.setState('speaking');
  const rate=24000,length=rate*6,buffer=new ArrayBuffer(44+length*2),view=new DataView(buffer);
  const text=(offset:number,value:string)=>[...value].forEach((character,i)=>view.setUint8(offset+i,character.charCodeAt(0)));
  text(0,'RIFF');view.setUint32(4,36+length*2,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,length*2,true);
  for(let i=0;i<length;i++){const t=i/rate,envelope=Math.max(0,Math.sin(t*8))**2*(.5+.5*Math.sin(t*2));view.setInt16(44+i*2,Math.sin(t*2*Math.PI*280)*envelope*.38*32767,true);}
  const url=URL.createObjectURL(new Blob([buffer],{type:'audio/wav'})),audio=new Audio(url);audio.loop=true;audio.volume=.3;
  const stop=startKlicPlaybackAnalysis(audio,value=>{signal=value;});stopAudio=()=>{audio.pause();stop();URL.revokeObjectURL(url);};void audio.play();
});
const timer=setInterval(()=>{document.querySelector('output')!.textContent=`Fonte: ${signal.source} · amplitude real medida: ${signal.level.toFixed(3)} · ${metrics}`;},150);
window.addEventListener('pagehide',()=>{resetAudio();entity.dispose();clearInterval(timer);},{once:true});
