import { chromium, request } from "@playwright/test";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";

// This script targets the dedicated QA server and database, never the user's
// running app. Its account and auth state live only in ignored runtime output.
const origin = process.env.CRAFT_QA_ORIGIN || "http://127.0.0.1:3018";
if (origin !== "http://127.0.0.1:3018") throw new Error("Use the dedicated Craft QA frontend on port 3018.");
const output = resolve(".codex-runtime/craft");
await mkdir(output, { recursive: true });
const api = await request.newContext({ baseURL: origin });
const authFile = resolve(output, "frontend-qa-auth.json");
let auth;
try { auth = JSON.parse(await readFile(authFile, "utf8")); } catch {}
if (!auth) {
  const registration = await api.post("/api/v1/auth/register", { data: { email: `craft-${randomUUID()}@example.com`, name: "Validação Craft", password: randomUUID() + randomUUID(), workspaceName: "Craft QA isolado" } });
  if (registration.status() !== 201) throw new Error(`QA registration failed (${registration.status()}).`);
  auth = { token: (await registration.json()).accessToken };
  await writeFile(authFile, JSON.stringify(auth), { mode: 0o600 });
}
const enginesResponse = await api.get("/api/v1/studios/v1/craft/engines", { headers: { Authorization: `Bearer ${auth.token}` } });
if (!enginesResponse.ok()) throw new Error(`Engine inventory failed (${enginesResponse.status()}).`);
const engines = (await enginesResponse.json()).engines;
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
await context.addInitScript((token) => localStorage.setItem("nexus_access_token", token), auth.token);
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
for (const [mode, engine] of [["visual", "photocraft"], ["video", "filmcraft"], ["effects", "effectcraft"]]) {
  await page.goto(`${origin}/content/draft/edit?mode=${mode}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator(".craft-studio").waitFor({ state: "visible", timeout: 60000 });
  const capability = engines.find((item) => item.engine === engine);
  if (capability?.available) await page.locator(".craft-create,.craft-workspace").first().waitFor({ state: "visible", timeout: 60000 });
  else await page.getByRole("heading", { name: "Studio aguardando o motor de edição" }).waitFor({ state: "visible", timeout: 60000 });
  await page.screenshot({ path: resolve(output, `frontend-${engine}-real.png`), fullPage: true });
  if (await page.locator("iframe,canvas,.vs-shell,.cx-visual-canvas,.cx-carousel-stage").count()) throw new Error("A retired or upstream UI surfaced in the customer Studio.");
  console.log(JSON.stringify({ engine, available: Boolean(capability?.available), screenshot: `frontend-${engine}-real.png` }));
}
if (errors.length) throw new Error(`Frontend runtime errors: ${errors.join(" | ")}`);
await context.close(); await browser.close(); await api.dispose();
