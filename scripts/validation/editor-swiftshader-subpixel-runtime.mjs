// Query a fresh renderer browser, preserving the user's browser/processes.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const study=path.join(root,'docs/studios/research/editor-oss-20261002');
const source=JSON.parse(await fs.readFile(path.join(study,'spatial-effects-browser-sources.json'),'utf8'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
if(sha(await fs.readFile(source.browserPath))!==source.installedBrowserSha256)throw new Error('browser_drift');
const output=path.join(study,'swiftshader-subpixel-runtime.json');
try{await fs.access(output);throw new Error('evidence_exists');}catch(error){if(error.code!=='ENOENT')throw error;}
const require=createRequire(path.join(root,'workers/remotion-benchmark/package.json'));
const {openBrowser}=require('@remotion/renderer');
const browser=await openBrowser('chrome',{browserExecutable:source.browserPath,chromiumOptions:{gl:'swangle'},logLevel:'error'});
try{
  const page=await browser.newPage({context:()=>null,logLevel:'error',indent:false,pageIndex:0,onBrowserLog:null,onLog:()=>{}});
  const values=await page.evaluate(()=>{
    const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl2')??canvas.getContext('webgl');
    if(!gl)throw new Error('webgl_missing');
    const debug=gl.getExtension('WEBGL_debug_renderer_info');
    return {subpixelBits:gl.getParameter(gl.SUBPIXEL_BITS),renderer:gl.getParameter(gl.RENDERER),vendor:gl.getParameter(gl.VENDOR),
      version:gl.getParameter(gl.VERSION),shadingLanguage:gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
      unmaskedRenderer:debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):null,
      unmaskedVendor:debug?gl.getParameter(debug.UNMASKED_VENDOR_WEBGL):null};
  });
  await fs.writeFile(output,JSON.stringify({scope:'fresh_pinned_renderer_browser_webgl_capabilities',
    productionAdmission:'pending',browserVersion:source.installedBrowserVersion,browserSha256:source.installedBrowserSha256,
    gl:'swangle',scriptSha256:sha(await fs.readFile(fileURLToPath(import.meta.url))),values},null,2));
  console.log(JSON.stringify(values));
}finally{await browser.close({silent:true});}
