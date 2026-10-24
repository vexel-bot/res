import { Worker } from 'node:worker_threads';
import path from 'node:path';
import type { ChatFile } from '../../src/klic/conversation';
let active=0;

/** Parser work is isolated from HTTP/UI traffic, bounded in time and heap, and cancellable. */
export async function processAttachments(input: unknown, signal: AbortSignal): Promise<ChatFile[]> {
  if(Array.isArray(input)&&input.length===0)return [];
  signal.throwIfAborted();
  if(active>=4)throw new Error('Aguarde um momento para processar os anexos.');
  active++;
  try {
    return await new Promise<ChatFile[]>((resolve,reject)=>{
      const production=process.env.NODE_ENV==='production'||process.argv[1]?.replace(/\\/g,'/').endsWith('/dist/server.js');
      const worker=production
        ? new Worker(path.resolve('dist/attachmentWorker.cjs'),{workerData:input,resourceLimits:{maxOldGenerationSizeMb:128,stackSizeMb:4}})
        : new Worker(`require('tsx/cjs'); require(${JSON.stringify(path.resolve('server/klic/attachmentWorker.ts'))});`,{eval:true,workerData:input,resourceLimits:{maxOldGenerationSizeMb:128,stackSizeMb:4}});
      let settled=false;
      const finish=(error?:Error,files?:ChatFile[])=>{
        if(settled)return;settled=true;clearTimeout(timer);signal.removeEventListener('abort',abort);
        void worker.terminate().finally(()=>{if(error)reject(error);else resolve(files!);});
      };
      const abort=()=>finish(new DOMException('Processamento interrompido.','AbortError'));
      const timer=setTimeout(()=>finish(new Error('O arquivo demorou demais para ser processado. Divida-o em partes menores.')),15000);
      signal.addEventListener('abort',abort,{once:true});
      if(signal.aborted){abort();return;}
      worker.once('message',message=>finish(message.error?new Error(message.error):undefined,message.files));
      worker.once('error',()=>finish(new Error('Não foi possível processar o arquivo com segurança.')));
      worker.once('exit',code=>{if(code!==0)finish(new Error('O arquivo excedeu os recursos disponíveis para processamento.'));});
    });
  } finally {active--;}
}
