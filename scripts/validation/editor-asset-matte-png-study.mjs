import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {validateMattePngHeader} from '../../workers/remotion-benchmark/src/asset-matte-png.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const results=[];
function header(width,height){const bytes=Buffer.alloc(33);Buffer.from([137,80,78,71,13,10,26,10]).copy(bytes);
  bytes.writeUInt32BE(13,8);bytes.write('IHDR',12);bytes.writeUInt32BE(width,16);bytes.writeUInt32BE(height,20);return bytes;}
for(const [id,width,height,previous] of [['fixture',128,128,0],['source-max',4096,4096,0],['aggregate-max',4096,4096,16777216]]){
  assert.equal(validateMattePngHeader(header(width,height),'image/png',previous).totalPixels,width*height+previous);
  results.push({id,status:'passed'});
}
for(const [id,bytes,mime,previous,expected] of [
  ['short',Buffer.alloc(8),'image/png',0,'png_required'],
  ['signature',Buffer.alloc(33),'image/png',0,'png_required'],
  ['mime',header(128,128),'image/jpeg',0,'png_required'],
  ['zero-width',header(0,128),'image/png',0,'decode_pixel_limit'],
  ['source-too-large',header(4097,4096),'image/png',0,'decode_pixel_limit'],
  ['aggregate-too-large',header(4096,4096),'image/png',16777217,'decode_pixel_limit'],
  ['negative-budget',header(128,128),'image/png',-1,'decode_pixel_limit'],
  ['nonfinite-budget',header(128,128),'image/png',Infinity,'decode_pixel_limit'],
]){
  assert.throws(()=>validateMattePngHeader(bytes,mime,previous),new RegExp(expected));results.push({id,status:'passed'});
}
const malformed=header(128,128);malformed.writeUInt32BE(12,8);
assert.throws(()=>validateMattePngHeader(malformed,'image/png'),/png_required/);results.push({id:'ihdr-length',status:'passed'});
function chunk(type,data){const bytes=Buffer.alloc(data.length+12);bytes.writeUInt32BE(data.length);
  bytes.write(type,4);data.copy(bytes,8);return bytes;}
const animation=Buffer.concat([header(8,8),chunk('acTL',Buffer.alloc(8))]);
assert.throws(()=>validateMattePngHeader(animation,'image/png'),/animated_png_pending/);
results.push({id:'animation-control-before-IDAT',status:'passed'});
const truncated=chunk('tEXt',Buffer.alloc(0));truncated.writeUInt32BE(100);
assert.throws(()=>validateMattePngHeader(Buffer.concat([header(8,8),truncated]),'image/png'),/png_required/);
results.push({id:'truncated-pre-IDAT-chunk',status:'passed'});
const namedData=Buffer.concat([header(8,8),chunk('tEXt',Buffer.from('note\0acTL')),chunk('IDAT',Buffer.alloc(0))]);
assert.equal(validateMattePngHeader(namedData,'image/png').pixels,64);
results.push({id:'animation-name-in-text-is-not-animation',status:'passed'});
const fixture='docs/studios/research/editor-oss-20261002/original-animated-matte-negative.png';
const originalAnimation=await fs.readFile(path.join(root,fixture));
assert.throws(()=>validateMattePngHeader(originalAnimation,'image/png'),/animated_png_pending/);
results.push({id:'original-two-frame-APNG-rejected',status:'passed',fixture,
  sha256:crypto.createHash('sha256').update(originalAnimation).digest('hex')});
const staticFixture=await fs.readFile(path.join(root,'docs/studios/research/editor-oss-20261002/asset-matte-render/alpha-normal/original-matte.png'));
assert.equal(validateMattePngHeader(staticFixture,'image/png').pixels,16384);
results.push({id:'original-static-PNG-accepted',status:'passed'});
const source='workers/remotion-benchmark/src/asset-matte-png.mjs';
const report={scope:'actual_worker_PNG_header_validator_not_decoder',passed:results.length,cases:results,
  source,sourceSha256:crypto.createHash('sha256').update(await fs.readFile(path.join(root,source))).digest('hex')};
const output=path.join(root,'docs/studios/research/editor-oss-20261002/asset-matte-png-study.json');
await fs.writeFile(output,JSON.stringify(report,null,2));console.log(JSON.stringify({output,passed:report.passed}));
