// Isolated UI validation server. Never imported by the application or production build.
import express from 'express';
import path from 'node:path';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { createServer } from 'vite';
import { createGovernanceRouter } from '../server/governance';
import { createKlicRuntime } from '../server/klic/router';
import { ConversationStore } from '../server/klic/conversations';
import { KlicMemory } from '../server/klic/store';
import { createKlicVoiceRouter } from '../server/voice/router';
process.env.NODE_ENV='development';process.env.CLICKO_DEV_AUTH_BYPASS='true';process.env.DISABLE_HMR='true';
const folder=mkdtempSync(path.join(tmpdir(),'clicko-klic-ui-'));
const app=express();app.use(express.json({limit:'10mb'}));
app.use('/api/governance',createGovernanceRouter({dataFile:path.join(folder,'governance.json')}));
app.use('/api/klic/voice',createKlicVoiceRouter());
const markdown='# Resposta de teste controlado\n\n## Organização\n\nOlá! **Criação**, *ação* e português brasileiro 🧡.\n\n1. Planejar\n2. Criar\n\n- Imagem\n- Vídeo\n\n> Conteúdo fictício para validação da interface.\n\n| Canal | Total |\n|---|---:|\n|Imagem|20|\n|Vídeo|30|\n\n---\n\nCódigo `const ação = true`:\n\n```js\nconst mensagem = "Olá, KLIC!";\nconsole.log(mensagem);\n```\n\n[Documentação](https://example.com)\n\n<script>alert("XSS")</script>\n\n[inseguro](javascript:alert(1))';
app.use('/api/klic',createKlicRuntime({memory:new KlicMemory(null),conversations:new ConversationStore(path.join(folder,'conversations')),conversationProvider:{
  async *stream(_system,prompt,_files,signal){
    const parsed=JSON.parse(prompt);const last=parsed.conversation.recent.at(-1)?.content||'';
    if(last.includes('ERRO_CONTROLADO'))throw new Error('Fixture failure');
    const text=markdown+(last.includes('LONGA')?'\n\n'+Array.from({length:70},(_,i)=>`Parágrafo ${i+1}: contexto, criação e conteúdo.\n\n`).join(''):'');
    for(const part of text.match(/.{1,12}|\n/g)||[]){signal.throwIfAborted();yield part;await new Promise(r=>setTimeout(r,30));}
  },async transcribe(){return 'Transcrição fictícia exclusiva do teste de interface.';}
}}).router);
app.use('/api',(_req,res)=>res.status(503).json({error:'Serviço fora do escopo desta fixture.'}));
const vite=await createServer({server:{middlewareMode:true,hmr:{host:'127.0.0.1',port:24679}},appType:'spa'});app.use(vite.middlewares);
const server=app.listen(3101,'127.0.0.1',()=>console.log('KLIC UI FIXTURE — somente testes controlados — http://127.0.0.1:3101/klic'));
const stop=()=>{server.close();void vite.close();if(path.dirname(folder)===path.resolve(tmpdir())&&path.basename(folder).startsWith('clicko-klic-ui-'))rmSync(folder,{recursive:true,force:true});process.exit(0);};
process.once('SIGINT',stop);process.once('SIGTERM',stop);
