import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const worker = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(worker,'..','..');
const outputDir = path.resolve(process.argv[2] ?? path.join(repo,'output','remotion-native-scene-pilot'));
await fs.mkdir(outputDir,{recursive:true});
const sampleRate = 48000;
const seconds = 9;
const samples = sampleRate * seconds;
const pcm = Buffer.alloc(samples * 2);
const accents = [0, 74/30, 166/30, 226/30];
for (let i=0;i<samples;i++) {
  const t = i / sampleRate;
  const pad = (Math.sin(2*Math.PI*110*t)*.07 + Math.sin(2*Math.PI*164.8*t)*.036) * Math.min(1,t/.5) * Math.min(1,(seconds-t)/.8);
  let percussion = 0;
  for (const at of accents) {
    const d=t-at;
    if (d>=0 && d<.3) percussion += Math.sin(2*Math.PI*(62+90*Math.exp(-d*25))*d)*.27*Math.exp(-d*18);
  }
  pcm.writeInt16LE(Math.round(Math.max(-1,Math.min(1,pad+percussion))*32767),i*2);
}
const wav=Buffer.alloc(44+pcm.length);
wav.write('RIFF',0); wav.writeUInt32LE(wav.length-8,4); wav.write('WAVEfmt ',8); wav.writeUInt32LE(16,16);
wav.writeUInt16LE(1,20); wav.writeUInt16LE(1,22); wav.writeUInt32LE(sampleRate,24);
wav.writeUInt32LE(sampleRate*2,28); wav.writeUInt16LE(2,32); wav.writeUInt16LE(16,34);
wav.write('data',36); wav.writeUInt32LE(pcm.length,40); pcm.copy(wav,44);
const audioPath=path.join(outputDir,'sample-sound.wav');
await fs.writeFile(audioPath,wav);
const files={
  beans:{path:path.join(repo,'public','canonical','figma','s01','hero-coffee-atmosphere.png'),mime:'image/png'},
  ritual:{path:path.join(repo,'public','canonical','figma','phase2','s16-texture.png'),mime:'image/png'},
  product:{path:path.join(repo,'public','canonical','figma','phase2','s16-product.png'),mime:'image/png'},
  sound:{path:audioPath,mime:'audio/wav'},
};
const assetFiles={};
for(const [id,item] of Object.entries(files)){
  const bytes=await fs.readFile(item.path);
  assetFiles[id]={path:path.relative(outputDir,item.path),mime:item.mime,
    sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
}
const manifest={schemaVersion:'res.remotion-native-scene.v1',component:'product-story-v1',
  width:720,height:1280,fps:30,durationFrames:270,brand:'CAFÉ AURORA',accent:'#e7b966',background:'#100e0b',
  beats:[
    {startFrame:0,durationFrames:74,imageId:'beans',eyebrow:'O começo',headline:'Tudo começa no grão.',subline:'Uma pausa para sentir mais.',focusX:50,focusY:48},
    {startFrame:74,durationFrames:92,imageId:'ritual',eyebrow:'O ritual',headline:'Quatro origens.',subline:'Uma experiência em cada detalhe.',focusX:54,focusY:50},
    {startFrame:166,durationFrames:104,imageId:'product',eyebrow:'Café Aurora',headline:'Encontre o seu momento.',subline:'Conheça o kit degustação.',focusX:50,focusY:40},
  ],audioId:'sound',assetFiles};
const manifestPath=path.join(outputDir,'manifest.json');
await fs.writeFile(manifestPath,JSON.stringify(manifest,null,2),'utf8');
const videoPath=path.join(outputDir,'product-story.mp4');
const result=spawnSync(process.execPath,[path.join(worker,'render-native-scene.mjs'),manifestPath,videoPath],
  {cwd:worker,encoding:'utf8',stdio:['ignore','pipe','inherit']});
if(result.error)throw result.error;
if(result.status!==0)process.exit(result.status??1);
const receipt=JSON.parse(result.stdout.trim().split(/\r?\n/).at(-1));
await fs.writeFile(path.join(outputDir,'render-receipt.json'),JSON.stringify(receipt,null,2),'utf8');
console.log(JSON.stringify(receipt));
console.log(videoPath);
