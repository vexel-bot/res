import { request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { Readable } from 'node:stream';

/** Keep a synchronous editing response open until completion or client cancellation. */
export function longStudioRequest(target: URL, init: RequestInit): Promise<Response> {
  if (init.body !== undefined && typeof init.body !== 'string') {
    return Promise.reject(new Error('Long editing requests require a JSON body.'));
  }
  return new Promise((resolve, reject) => {
    const send = target.protocol === 'https:' ? httpsRequest : httpRequest;
    const request = send(target, {
      method: init.method,
      headers: Object.fromEntries(new Headers(init.headers)),
      signal: init.signal ?? undefined,
    }, incoming => {
      const headers = new Headers();
      for (const [name, value] of Object.entries(incoming.headers)) {
        for (const item of Array.isArray(value) ? value : value === undefined ? [] : [value]) {
          headers.append(name, item);
        }
      }
      const status = incoming.statusCode ?? 502;
      const empty = init.method === 'HEAD' || [204, 205, 304].includes(status);
      if (empty) incoming.resume();
      resolve(new Response(empty ? null : Readable.toWeb(incoming) as ReadableStream<Uint8Array>, {
        status, headers,
      }));
    });
    request.on('error', reject);
    request.end(init.body);
  });
}
