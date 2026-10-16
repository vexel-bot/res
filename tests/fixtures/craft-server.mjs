import { createServer } from "node:http";
import { build } from "esbuild";

// Only the API-contract tests intercept server responses. This host bundles the
// real React Studio and providers; it does not qualify native engine rendering.
const output = await build({ entryPoints: ["tests/fixtures/craft-harness.tsx"], bundle: true, format: "esm", platform: "browser", outfile: "craft-harness.js", write: false, define: { "process.env.NODE_ENV": '"development"' } });
const js = output.outputFiles.find((file) => file.path.endsWith(".js")).contents;
const css = output.outputFiles.find((file) => file.path.endsWith(".css"))?.contents ?? "";
createServer((request, response) => {
  if (request.url === "/craft-harness.js") { response.writeHead(200, { "Content-Type": "application/javascript" }); response.end(js); return; }
  if (request.url === "/craft-harness.css") { response.writeHead(200, { "Content-Type": "text/css" }); response.end(css); return; }
  if (request.url.startsWith("/api/")) { response.writeHead(503); response.end("API interception required by tests"); return; }
  response.writeHead(200, { "Content-Type": "text/html" }); response.end('<!doctype html><html lang="pt-BR"><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Clicko Craft interface contract test</title><link rel="stylesheet" href="/craft-harness.css"></head><body style="margin:0;background:#101114"><div id="root"></div><script type="module" src="/craft-harness.js"></script></body></html>');
}).listen(3016, "127.0.0.1");
