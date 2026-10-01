import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';

const root=path.dirname(fileURLToPath(import.meta.url));
const input=process.argv[2], output=process.argv[3];
if(!input||!output)throw new Error('plan_manifest_and_output_required');
const manifest=JSON.parse(await fs.readFile(input,'utf8'));
if(manifest.schemaVersion!=='res.motion-canvas-composition.v1')throw new Error('plan_manifest_schema_unsupported');
if(!Number.isInteger(manifest.width)||!Number.isInteger(manifest.height)||!Number.isInteger(manifest.fps)||
  !Number.isInteger(manifest.durationFrames)||manifest.width<1||manifest.height<1||manifest.fps<1||manifest.durationFrames<1||
  manifest.width>3840||manifest.height>3840||manifest.durationFrames>1800)throw new Error('plan_manifest_dimensions_invalid');
const paths=new Set(['position.x','position.y','scale.x','scale.y','rotation.degrees','opacity','filters.blurPx','fontSize.px','letterSpacing.px','lineHeight.ratio','fontWeight']);
for(const track of manifest.tracks)if(!paths.has(track.propertyPath))throw new Error(`plan_track_unsupported:${track.propertyPath}`);
for(const item of manifest.transitions)if(!['hard_cut','dissolve'].includes(item.kind))throw new Error(`plan_transition_unsupported:${item.kind}`);
for(const layer of manifest.layers){
  if(!['group','image','text','shape'].includes(layer.kind))throw new Error(`plan_layer_unsupported:${layer.kind}`);
  const p=layer.properties;
  if(p.maskAssetId||(p.editorialEffects?.length??0)>0||(p.editorialTextSpans?.length??0)>0||p.editorialShadow||p.editorialBlendMode&&p.editorialBlendMode!=='normal'||
    (p.editorialBorder?.width??0)>0)throw new Error(`plan_effect_unsupported:${layer.id}`);
  if(!['none','words','path'].includes(p.editorialTiming?.reveal??'none'))throw new Error(`plan_reveal_unsupported:${layer.id}`);
}
const assets={};
for(const [id,item] of Object.entries(manifest.assetFiles??{})){
  const bytes=await fs.readFile(item.path);
  if(crypto.createHash('sha256').update(bytes).digest('hex')!==item.sha256)throw new Error(`plan_asset_checksum_conflict:${id}`);
  if(!['image/png','image/jpeg','image/webp','font/ttf','font/otf','font/woff','font/woff2','application/font-woff'].includes(item.mime))
    throw new Error(`plan_asset_mime_unsupported:${id}`);
  assets[id]=`data:${item.mime};base64,${bytes.toString('base64')}`;
}
const inputProps={manifest:{...manifest,assets}};
const started=performance.now();
const serveUrl=await bundle({entryPoint:path.join(root,'src','plan.tsx')});
const composition=await selectComposition({serveUrl,id:'ResPlanComparison',inputProps,logLevel:'error'});
await renderMedia({serveUrl,composition,codec:'h264',outputLocation:path.resolve(output),inputProps,concurrency:1,logLevel:'error'});
const bytes=await fs.readFile(output);
console.log(JSON.stringify({schemaVersion:'res.remotion-plan-comparison-receipt.v1',manifestSha256:crypto.createHash('sha256').update(await fs.readFile(input)).digest('hex'),
  videoSha256:crypto.createHash('sha256').update(bytes).digest('hex'),durationMs:Math.round(performance.now()-started),bytes:bytes.length,
  renderer:'remotion',comparisonOnly:true,humanVisualReview:'pending'}));
