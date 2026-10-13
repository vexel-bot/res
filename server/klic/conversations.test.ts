import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import express from 'express';
import ExcelJS from 'exceljs';
import { zipSync, strToU8 } from 'fflate';
import { ConversationStore, modelWindow, publicConversation } from './conversations';
import { prepareFiles, selectExcerpts } from './attachments';
import { processAttachments } from './attachmentProcessing';
import { publicAttachmentError } from './attachmentErrors';
import { createKlicRuntime } from './router';
import { KlicMemory } from './store';
import { createGovernanceRouter } from '../governance';
import { createKlicVoiceRouter } from '../voice/router';
import type { ChatMessage } from '../../src/klic/conversation';

const scope={workspaceId:'ws-1',userId:'usr-master',clientId:null};
const file=(name:string,type:string,value:Buffer|string)=>{const bytes=typeof value==='string'?Buffer.from(value):value;return{name,type,size:bytes.length,dataUrl:`data:${type};base64,${bytes.toString('base64')}`};};
const temporary=()=>mkdtempSync(path.join(tmpdir(),'clicko-conversations-'));
const remove=(folder:string)=>{if(path.dirname(folder)===path.resolve(tmpdir())&&path.basename(folder).startsWith('clicko-conversations-'))rmSync(folder,{recursive:true,force:true});};

test('a provider that returns normally after cancellation cannot save partial output as complete',async t=>{
  const folder=temporary();const store=new ConversationStore(folder);let started!:()=>void;
  const ready=new Promise<void>(resolve=>{started=resolve;});
  const runtime=createKlicRuntime({memory:new KlicMemory(null),conversations:store,conversationProvider:{
    async *stream(_s,_p,_f,signal){
      yield 'Parcial';started();
      await new Promise<void>(resolve=>signal.addEventListener('abort',()=>resolve(),{once:true}));
      return;
    },async transcribe(){return '';},
  }});
  const app=express();app.use(express.json());app.use('/api/governance',createGovernanceRouter({dataFile:null}));app.use('/api/klic',runtime.router);
  const server=app.listen(0,'127.0.0.1');await new Promise<void>(resolve=>server.once('listening',resolve));
  t.after(async()=>{await new Promise<void>(resolve=>server.close(()=>resolve()));remove(folder);});
  const base='http://127.0.0.1:'+(server.address() as {port:number}).port;
  const post=(route:string,body:object={})=>fetch(base+'/api/klic/conversations/'+route,{method:'POST',headers:{'Content-Type':'application/json','x-workspace-id':'ws-1','x-user-id':'usr-master'},body:JSON.stringify({workspaceId:'ws-1',source:'ai-chat',...body})});
  const conversation=await(await post('create')).json();const requestId=randomUUID();
  const response=post('send',{conversationId:conversation.id,requestId,message:'Cancelamento controlado'});await ready;
  await post('cancel',{requestId});
  const events=(await(await response).text()).trim().split('\n').map(line=>JSON.parse(line));
  assert.ok(!events.some(event=>event.type==='done'));
  assert.equal(store.read(scope,conversation.id).messages.at(-1)!.status,'cancelled');
});

test('conversation storage persists UTF-8 and files, hides payloads, isolates user/workspace/client and deletes backups',()=>{
  const folder=temporary();try{
    const store=new ConversationStore(folder);const c=store.create(scope);
    store.update(scope,c.id,c=>c.messages.push({id:'m',requestId:'r',role:'user',module:'ai-chat',status:'complete',content:'Olá, ação! 🧡 日本語',createdAt:new Date().toISOString(),attachments:[{...file('dados.txt','text/plain','conteúdo privado'),id:'f',text:'conteúdo privado'}]}));
    const restored=new ConversationStore(folder).read(scope,c.id);assert.match(restored.messages[0].content,/ação/);
    assert.equal(publicConversation(restored).messages[0].attachments![0].dataUrl,undefined);
    assert.equal(publicConversation(restored).messages[0].attachments![0].text,undefined);
    for(const other of [{...scope,userId:'other'},{...scope,workspaceId:'other'},{...scope,clientId:'other'}])assert.throws(()=>store.read(other,c.id));
    assert.throws(()=>store.read(scope,'../../secret'));assert.equal(store.list(scope).length,1);store.clear(scope);assert.equal(store.list(scope).length,0);
  }finally{remove(folder);}
});
test('context has bounded recent history, relevant earlier excerpts and no failed assistant output',()=>{
  const messages:ChatMessage[]=Array.from({length:160},(_,i)=>({id:String(i),requestId:String(i),role:i%2?'assistant':'user',content:`Turno ${i}: `+'ação '.repeat(800),createdAt:'',module:'ai-chat',status:i===159?'error':'complete'}));
  const window=modelWindow(messages,10000);assert.ok(JSON.stringify(window).length<18000);assert.ok(window.omitted>0);assert.ok(!window.recent.some(m=>m.content.startsWith('Turno 159:')));
  const document='Introdução\n'+'sem informação. '.repeat(3000)+'\nReceita exclusiva: R$ 1234';
  assert.match(selectExcerpts(document,'Receita exclusiva',8000),/1234/);assert.ok(selectExcerpts(document,'Receita',8000).length<9000);
});
test('summary cache observes external updates and parser errors never expose internals',async()=>{
  const folder=temporary();try{
    const first=new ConversationStore(folder);const c=first.create(scope);assert.equal(first.list(scope)[0].title,'Nova conversa');
    new ConversationStore(folder).update(scope,c.id,value=>{value.title='Título alterado por outra instância';});
    assert.equal(first.list(scope)[0].title,'Título alterado por outra instância');
    assert.equal(publicAttachmentError(new Error('PDF parser secret-path /private/document')),undefined);
    assert.equal(publicAttachmentError(new Error('Formato de arquivo não suportado.')),'Formato de arquivo não suportado.');
    await assert.rejects(()=>processAttachments([file('bad.pdf','application/pdf','%PDF-corrupt')],new AbortController().signal),/Não foi possível processar o arquivo com segurança/);
  }finally{remove(folder);}
});
test('validates attachments, rejects corrupt/binary/oversized/unsupported files, reads CSV and DOCX',async()=>{
  const csv=await prepareFiles([file('vendas.csv','text/csv','Produto;Receita\nCriação;20\nVídeo;30')]);assert.match(csv[0].text!,/Criação/);assert.match(csv[0].text!,/Receita/);
  const doc=zipSync({'[Content_Types].xml':strToU8('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'),'word/document.xml':strToU8('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Criação contextual</w:t></w:r></w:p></w:body></w:document>')});
  const docs=await prepareFiles([file('briefing.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document',Buffer.from(doc))]);assert.match(docs[0].text!,/Criação contextual/);
  for(const invalid of [file('fake.png','image/png','not png'),file('empty.txt','text/plain',''),file('bad.txt','text/plain',Buffer.from([0xff,0xfe])),file('bad.pdf','application/pdf','%PDF-corrupt'),file('run.exe','application/octet-stream','code'),file('bad.txt','image/png','text'),{...file('large.txt','text/plain','x'),size:7*1024*1024}])await assert.rejects(()=>prepareFiles([invalid]));
  await assert.rejects(()=>prepareFiles(Array.from({length:5},()=>file('a.txt','text/plain','a'))));
});
test('XLSX processes multiple sheets, headers, numbers, dates and saved formula results',async()=>{
  const book=new ExcelJS.Workbook();const a=book.addWorksheet('Receitas');a.addRow(['Nome','Total','Data']);a.addRow(['Vídeo',20,new Date('2026-01-01')]);a.addRow(['Imagem',30,null]);book.addWorksheet('Resumo').addRow([{formula:'SUM(20,30)',result:50}]);
  const bytes=Buffer.from(await book.xlsx.writeBuffer());const [result]=await prepareFiles([file('dados.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',bytes)]);
  assert.match(result.text!,/Receitas/);assert.match(result.text!,/Resumo/);assert.match(result.text!,/"sum":50/);assert.match(result.text!,/Vídeo/);
});
function pdf(text:string){
  const stream=`BT /F1 12 Tf 50 750 Td (${text}) Tj ET`;
  const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`];
  let output='%PDF-1.4\n';const offsets=[0];objects.forEach((o,i)=>{offsets.push(Buffer.byteLength(output));output+=`${i+1} 0 obj\n${o}\nendobj\n`;});const xref=Buffer.byteLength(output);output+=`xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;return Buffer.from(output);
}
test('PDF text extraction, empty PDF rejection, worker processing and cancellation',async()=>{
  const [parsed]=await prepareFiles([file('brief.pdf','application/pdf',pdf('Clicko operational document 1234'))]);assert.match(parsed.text!,/1234/);
  await assert.rejects(()=>prepareFiles([file('empty.pdf','application/pdf',pdf(''))]));
  const [worker]=await processAttachments([file('utf8.txt','text/plain','ação 🧡')],new AbortController().signal);assert.equal(worker.text,'ação 🧡');
  const controller=new AbortController();controller.abort();await assert.rejects(()=>processAttachments([file('a.txt','text/plain','a')],controller.signal));
});
test('simultaneous requests are rejected, cancellation terminates one stream, and retries preserve message IDs',async t=>{
  const folder=temporary();const store=new ConversationStore(folder);let started!:()=>void;let completed!:()=>void;
  const start=new Promise<void>(r=>started=r);const complete=new Promise<void>(r=>completed=r);let count=0;
  const runtime=createKlicRuntime({memory:new KlicMemory(null),conversations:store,conversationProvider:{async *stream(_s,_p,_f,signal){count++;started();yield 'Parcial';try{await new Promise<void>((_r,reject)=>signal.addEventListener('abort',()=>reject(signal.reason),{once:true}));}finally{completed();}},async transcribe(){return 'voz';}}});
  const app=express();app.use(express.json());app.use('/api/governance',createGovernanceRouter({dataFile:null}));app.use('/api/klic',runtime.router);const server=app.listen(0,'127.0.0.1');await new Promise<void>(r=>server.once('listening',r));
  t.after(async()=>{await new Promise<void>(r=>server.close(()=>r()));remove(folder);});const base='http://127.0.0.1:'+(server.address() as {port:number}).port;
  const post=(route:string,body:object={})=>fetch(base+'/api/klic/conversations/'+route,{method:'POST',headers:{'Content-Type':'application/json','x-workspace-id':'ws-1','x-user-id':'usr-master'},body:JSON.stringify({workspaceId:'ws-1',source:'ai-chat',...body})});
  const c=await(await post('create')).json();const requestId=randomUUID();const first=post('send',{conversationId:c.id,requestId,message:'Responda lentamente'});await start;
  assert.equal((await post('send',{conversationId:c.id,requestId,message:'Responda lentamente'})).status,429);
  assert.equal((await post('clear')).status,429);await post('cancel');await complete;
  const events=(await(await first).text()).trim().split('\n').map(line=>JSON.parse(line));assert.equal(events.at(-1).type,'error');assert.equal(events.at(-1).data.conversation.messages.at(-1).status,'cancelled');assert.equal(count,1);assert.equal(store.read(scope,c.id).messages.length,2);
});
test('authenticated conversation integration: streaming UTF-8, deduplication, context, retry, attachments, restart, access and voice authorization',async t=>{
  const previous=process.env.NODE_ENV;process.env.NODE_ENV='test';
  const folder=temporary();const store=new ConversationStore(folder);let calls=0;let fail=false;let prompts:string[]=[];let transcriptions=0;const transcriptionRequestIds:Array<string | undefined>=[];const binaryInputs:Array<Array<{mimeType:string;data:string}>>=[];
  const runtime=createKlicRuntime({memory:new KlicMemory(null),conversations:store,conversationProvider:{
    async *stream(_system,prompt,files,signal){calls++;prompts.push(prompt);binaryInputs.push(files);if(fail)throw new Error('SECRET_PROVIDER_ERROR');signal.throwIfAborted();yield 'Olá, ';yield '**ação** 🧡\n\n';yield '| A | B |\n|---|---|\n|1|2|';},
    async transcribe(_mimeType,_data,_signal,requestId){transcriptions++;transcriptionRequestIds.push(requestId);return 'Transcrição de teste controlado';},
  }});
  const app=express();app.use(express.json({limit:'10mb'}));app.use('/api/governance',createGovernanceRouter({dataFile:null}));app.use('/api/klic/voice',createKlicVoiceRouter());app.use('/api/klic',runtime.router);
  const server=app.listen(0,'127.0.0.1');await new Promise<void>(r=>server.once('listening',r));
  t.after(async()=>{await new Promise<void>(r=>server.close(()=>r()));remove(folder);process.env.NODE_ENV=previous;});
  const base='http://127.0.0.1:'+(server.address() as {port:number}).port;
  const headers={'Content-Type':'application/json','x-workspace-id':'ws-1','x-user-id':'usr-master'};
  const post=(route:string,body:object={},extra:Record<string,string>=headers)=>fetch(base+'/api/klic/'+route,{method:'POST',headers:extra,body:JSON.stringify({workspaceId:'ws-1',clientId:null,source:'ai-chat',...body})});
  assert.equal((await post('conversations/list',{}, {'Content-Type':'application/json'})).status,401);
  assert.equal((await post('voice/synthesize',{text:'Teste',voice:'female'},{'Content-Type':'application/json'})).status,401);
  assert.equal((await post('conversations/list',{}, {...headers,origin:'https://attacker.invalid'})).status,403);
  const c=await(await post('conversations/create')).json();const requestId=randomUUID();
  const response=await post('conversations/send',{conversationId:c.id,requestId,message:'Minha referência é girassol. Ação!'});
  const events=(await response.text()).trim().split('\n').map(line=>JSON.parse(line));
  assert.equal(events[0].type,'accepted');assert.equal(events.at(-1).type,'done');
  assert.equal(events.filter(e=>e.type==='delta').map(e=>e.data).join(''),'Olá, **ação** 🧡\n\n| A | B |\n|---|---|\n|1|2|');
  await post('conversations/send',{conversationId:c.id,requestId,message:'duplicada'});assert.equal(calls,1);
  await(await post('conversations/send',{conversationId:c.id,requestId:randomUUID(),message:'Explique isso'})).text();assert.match(prompts.at(-1)!,/girassol/);
  const c2=await(await post('conversations/create')).json();await(await post('conversations/send',{conversationId:c2.id,requestId:randomUUID(),message:'Conversa independente'})).text();assert.ok(!prompts.at(-1)!.includes('girassol'));
  fail=true;const failedId=randomUUID();const errorEvents=(await(await post('conversations/send',{conversationId:c.id,requestId:failedId,message:'Falha controlada',attachments:[file('nota.txt','text/plain','conteúdo do anexo')]})).text()).trim().split('\n').map(line=>JSON.parse(line));assert.equal(errorEvents.at(-1).type,'error');assert.ok(!JSON.stringify(errorEvents).includes('SECRET_PROVIDER_ERROR'));
  fail=false;await(await post('conversations/send',{conversationId:c.id,requestId:failedId,retry:true})).text();const restored=store.read(scope,c.id);assert.equal(restored.messages.filter(m=>m.requestId===failedId).length,2);assert.equal(restored.messages.at(-1)!.status,'complete');assert.match(prompts.at(-1)!,/conteúdo do anexo/);
  const attachment=restored.messages.flatMap(m=>m.attachments||[])[0];const download=await post('conversations/file',{conversationId:c.id,fileId:attachment.id});assert.equal(await download.text(),'conteúdo do anexo');
  assert.equal((await post('conversations/read',{workspaceId:'ws-other',conversationId:c.id})).status,403);
  assert.equal((await post('conversations/file',{conversationId:c2.id,fileId:attachment.id})).status,404);
  assert.equal(new ConversationStore(folder).read(scope,c.id).messages.length,6);
  const wav=Buffer.concat([Buffer.from('RIFF0000WAVEfmt '),Buffer.alloc(48)]);await(await post('conversations/send',{conversationId:c2.id,requestId:randomUUID(),message:'Resuma o áudio',attachments:[file('audio.wav','audio/wav',wav)]})).text();assert.equal(transcriptions,1);assert.match(prompts.at(-1)!,/Transcrição de teste/);
  const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64');
  const c3=await(await post('conversations/create')).json();
  await(await post('conversations/send',{conversationId:c3.id,requestId:randomUUID(),message:'Compare os quatro anexos',attachments:[file('imagem.png','image/png',png),file('dados.csv','text/csv','Nome,Total\nCriação,42'),file('nota.txt','text/plain','Referência girassol'),file('brief.pdf','application/pdf',pdf('Documento 1234'))]})).text();
  assert.equal(binaryInputs.at(-1)!.length,1);assert.equal(binaryInputs.at(-1)![0].data,png.toString('base64'));assert.match(prompts.at(-1)!,/1234/);assert.match(prompts.at(-1)!,/dados.csv/);
  await(await post('conversations/send',{conversationId:c3.id,requestId:randomUUID(),message:'Explique a imagem anterior'})).text();
  assert.equal(binaryInputs.at(-1)![0].data,png.toString('base64'));assert.equal(store.read(scope,c3.id).messages.at(-2)!.attachments?.length,0);
  const stt=await post('conversations/transcribe',{attachment:file('fala.wav','audio/wav',wav)});assert.equal(stt.status,200);assert.equal((await stt.json()).transcript,'Transcrição de teste controlado');assert.equal(transcriptions,2);assert.ok(transcriptionRequestIds.every(id=>/^[a-f0-9-]{36}$/.test(id || '')));
});
