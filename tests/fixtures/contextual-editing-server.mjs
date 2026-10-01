import { createServer } from "node:http";
import { build } from "esbuild";

// Serve the real React component as an isolated bundle. The API is mocked by
// Playwright, so the application server, database and HMR are unnecessary here.
const result = await build({
  entryPoints: ["tests/fixtures/contextual-editing-harness.tsx"],
  bundle: true,
  format: "esm",
  platform: "browser",
  outfile: "contextual-harness.js",
  write: false,
  define: { "process.env.NODE_ENV": '"development"' },
});
const javascript = result.outputFiles.find(file => file.path.endsWith(".js")).contents;
const stylesheet = result.outputFiles.find(file => file.path.endsWith(".css"))?.contents ?? "";
createServer((request, response) => {
  const url = new URL(request.url, "http://127.0.0.1:3012");
  if (url.pathname === "/tests/fixtures/contextual-editing-harness.tsx") {
    response.writeHead(200, { "Content-Type": "text/javascript" });
    return response.end(javascript);
  }
  if (url.pathname === "/contextual.css") {
    response.writeHead(200, { "Content-Type": "text/css" });
    return response.end(stylesheet);
  }
  response.writeHead(url.pathname === "/" ? 200 : 404, { "Content-Type": "text/plain" });
  response.end("Contextual editing component test");
}).listen(3012, "127.0.0.1");
