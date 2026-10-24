import { parentPort, workerData } from 'node:worker_threads';
import { prepareFiles } from './attachments';
import { publicAttachmentError } from './attachmentErrors';
void prepareFiles(workerData).then(files=>parentPort?.postMessage({files})).catch(error=>parentPort?.postMessage({error:publicAttachmentError(error)||'Não foi possível processar o arquivo com segurança.'}));
