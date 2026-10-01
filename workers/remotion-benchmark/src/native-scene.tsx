import React from 'react';
import {Audio, Composition, Img, interpolate, registerRoot, useCurrentFrame} from 'remotion';

type Beat = {
  startFrame: number;
  durationFrames: number;
  imageId: string;
  eyebrow: string;
  headline: string;
  subline: string;
  focusX?: number;
  focusY?: number;
};

export type NativeSceneManifest = {
  schemaVersion: 'res.remotion-native-scene.v1';
  component: 'product-story-v1';
  width: number;
  height: number;
  fps: number;
  durationFrames: number;
  brand: string;
  accent: string;
  background: string;
  beats: Beat[];
  assets: Record<string, string>;
  audioId?: string;
};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = (x: number) => 1 - Math.pow(1 - x, 3);

function Story({manifest}: {manifest: NativeSceneManifest}) {
  const frame = useCurrentFrame();
  const beatIndex = manifest.beats.findIndex((beat) => frame >= beat.startFrame && frame < beat.startFrame + beat.durationFrames);
  const beat = manifest.beats[Math.max(0, beatIndex)];
  const local = Math.max(0, frame - beat.startFrame);
  const exitStart = Math.max(beat.durationFrames - 11, 1);
  const enter = ease(interpolate(local, [0, 12], [0, 1], clamp));
  const leave = interpolate(local, [exitStart, beat.durationFrames], [1, 0], clamp);
  const fade = Math.min(enter, leave);
  const imageScale = interpolate(local, [0, beat.durationFrames], beatIndex === 2 ? [1.02, 1.12] : [1.13, 1.02], clamp);
  const imageDrift = interpolate(local, [0, beat.durationFrames], beatIndex === 1 ? [-18, 22] : [0, -32], clamp);
  const headlineRise = interpolate(local, [0, 15], [62, 0], clamp);
  const ruleWidth = interpolate(local, [2, 19], [0, 140], clamp);
  const isEnd = beatIndex === manifest.beats.length - 1;
  const image = manifest.assets[beat.imageId];
  if (!image) throw new Error(`native_scene_image_missing:${beat.imageId}`);

  return <div style={{position:'absolute', inset:0, background:manifest.background, overflow:'hidden', color:'#f8f3e9', fontFamily:'Arial, sans-serif'}}>
    <Img src={image} style={{position:'absolute', width:'100%', height:'100%', objectFit:'cover',
      objectPosition:`${beat.focusX ?? 50}% ${beat.focusY ?? 50}%`,
      transform:`translateY(${imageDrift}px) scale(${imageScale})`, filter:'saturate(.9) contrast(1.08)'}} />
    <div style={{position:'absolute', inset:0, background:isEnd
      ? 'linear-gradient(180deg,rgba(12,9,6,.28),rgba(12,9,6,.26) 32%,rgba(12,9,6,.88) 79%)'
      : 'linear-gradient(180deg,rgba(12,9,6,.65),rgba(12,9,6,.12) 40%,rgba(12,9,6,.85) 85%)'}} />
    <div style={{position:'absolute', top:78, left:62, right:62, display:'flex', alignItems:'center', justifyContent:'space-between', opacity:Math.min(1, local / 8)}}>
      <span style={{fontSize:22, fontWeight:700, letterSpacing:5, color:manifest.accent}}>{manifest.brand}</span>
      <span style={{fontSize:18, letterSpacing:3, fontWeight:700}}>0{beatIndex + 1} / 0{manifest.beats.length}</span>
    </div>
    <div style={{position:'absolute', left:62, right:58, bottom:isEnd ? 192 : 164, opacity:fade}}>
      <div style={{width:ruleWidth, height:5, background:manifest.accent, marginBottom:24}} />
      <div style={{fontSize:22, letterSpacing:5, fontWeight:700, color:manifest.accent, marginBottom:17}}>{beat.eyebrow.toUpperCase()}</div>
      <div style={{fontFamily:'Georgia, serif', fontSize:isEnd ? 90 : 84, lineHeight:1.02, letterSpacing:-3,
        transform:`translateY(${headlineRise}px)`, maxWidth:600, textShadow:'0 3px 20px #0008'}}>{beat.headline}</div>
      <div style={{fontSize:29, lineHeight:1.35, marginTop:24, maxWidth:560, transform:`translateY(${headlineRise * .65}px)`}}>{beat.subline}</div>
    </div>
    <div style={{position:'absolute', bottom:68, left:62, right:62, height:3, background:'#ffffff55'}}>
      <div style={{height:'100%', width:`${((frame + 1) / manifest.durationFrames) * 100}%`, background:manifest.accent}} />
    </div>
    {manifest.audioId ? <Audio src={manifest.assets[manifest.audioId]} volume={1} /> : null}
  </div>;
}

const example: NativeSceneManifest = {
  schemaVersion:'res.remotion-native-scene.v1', component:'product-story-v1', width:720, height:1280,
  fps:30, durationFrames:270, brand:'CAFÉ AURORA', accent:'#e7b966', background:'#100e0b',
  beats:[{startFrame:0,durationFrames:90,imageId:'beans',eyebrow:'01 / origem',headline:'Começa no grão.',subline:'Uma pausa para sentir mais.'}], assets:{}
};

registerRoot(() => <Composition id="ResNativeProductStory" component={Story} width={720} height={1280} fps={30} durationInFrames={270}
  defaultProps={{manifest:example}} calculateMetadata={({props}) => ({width:props.manifest.width,height:props.manifest.height,
    fps:props.manifest.fps,durationInFrames:props.manifest.durationFrames})} />);
