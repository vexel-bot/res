import { expect, test, type Page } from "@playwright/test";
import type { CraftCommand, CraftInspection } from "../../src/studios/craft/craftApi";

const native = { schemaVersion: "studio.native-editor-state.v1", engine: "photocraft", formatVersion: "1", buildId: "native-test-build", upstreamRevision: "revision", projectAssetId: "native-one", checksumSha256: "a".repeat(64), sizeBytes: 42, assetManifest: [], fontManifest: [], dependencies: [], migrationWarnings: [], pageProjects: [
  { pageId: "page-one", title: "Abertura", width: 1080, height: 1350, projectAssetId: "p1", checksumSha256: "a".repeat(64), sizeBytes: 21 },
  { pageId: "page-two", title: "Desenvolvimento", width: 1080, height: 1350, projectAssetId: "p2", checksumSha256: "b".repeat(64), sizeBytes: 21 },
] };
const capabilities = [
  { id: "type.setText", label: "Editar texto", inputSchema: { type: "object", properties: { layer: { type: "string", title: "Elemento" }, text: { type: "string", title: "Texto" } }, required: ["layer", "text"] } },
  ...["undo", "redo"].map((kind) => ({ id: `host.history.${kind}`, label: kind === "undo" ? "Desfazer" : "Refazer", inputSchema: { type: "object", properties: {} } })),
  ...["add", "move", "delete"].map((kind) => ({ id: `host.pages.${kind}`, label: kind, inputSchema: { type: "object", properties: {} } })),
];
const record = { documentId: "document-one", workspaceId: "workspace-one", title: "Carrossel Clicko", contentType: "carousel", revision: 1, version: 1, nativeEditorState: native, assets: [], composition: { pages: [] }, brief: { objective: "Criar direção" }, postRef: { id: "post-one" } };
const workspace = { id: "workspace-one", name: "Clicko test", brandProfile: { targetAudience: ["Criadores"] } };
const onePixelPng = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZlLkAAAAASUVORK5CYII=", "base64");
type RequestReceipt = { expectedRevision: number; commands: CraftCommand[]; pageId?: string; key: string };

async function setup(page: Page, options: { available?: boolean; conflict?: boolean; interruptCommit?: boolean; interruptAI?: boolean; recovery?: unknown } = {}) {
  let current = structuredClone(record);
  let activePageId = "page-one";
  const requests: RequestReceipt[] = [];
  const previewPages: string[] = [];
  const ai: Record<string, unknown>[] = [];
  let aiReceipt: unknown;
  const cached = new Map<string, unknown>();
  let cancelled = false;
  let renders = 0;
  const inspect = () => ({ schemaVersion: "studio.craft-inspection.v1", documentId: current.documentId, revision: current.revision, engine: "photocraft", nativeEditorState: current.nativeEditorState, activePageId, pages: current.nativeEditorState.pageProjects.map((page) => ({ ...page, id: page.pageId })), capabilities, project: { width: 1080, height: 1350, layers: [{ id: `title-${activePageId}`, name: "Título", kind: "text", properties: { text: "Projeto nativo" } }], timeline: [], warnings: [] } });
  await page.addInitScript((recovery) => {
    localStorage.setItem("nexus_access_token", "interface-test-token");
    if (recovery) localStorage.setItem("clicko:craft:v1:user-one:workspace-one:document-one:photocraft", JSON.stringify(recovery));
  }, options.recovery);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request(); const url = new URL(request.url()); const endpoint = url.pathname;
    if (endpoint.endsWith("/bootstrap")) return route.fulfill({ json: { user: { id: "user-one" }, workspaces: [workspace], posts: [], suggestions: [] } });
    if (endpoint.endsWith("/capabilities")) return route.fulfill({ json: { capabilities: [] } });
    if (endpoint.endsWith("/craft/llm-catalog")) return route.fulfill({ json: { providers: [], credentialStorageReady: true, legacyPlanningAvailable: true } });
    if (endpoint.endsWith("/craft/llm-connections")) return route.fulfill({ json: { connections: [], canManage: false } });
    if (endpoint.includes("/craft/ai-requests/")) return route.fulfill({ json: aiReceipt ? { status: "committed", receipt: aiReceipt } : { status: "not_found" } });
    if (endpoint.endsWith("/craft/engines")) return route.fulfill({ json: { schemaVersion: "studio.craft-engines.v1", engines: [{ engine: "photocraft", available: options.available !== false, buildId: "native-test-build", formatVersion: "1", upstreamRevision: "revision", commands: capabilities, formats: ["png", "pcraft"], reason: "Motor em preparação" }] } });
    if (endpoint.endsWith("/documents")) return route.fulfill({ json: [current] });
    if (endpoint.endsWith("/documents/document-one")) return route.fulfill({ json: current });
    if (endpoint.endsWith("/craft/inspection")) { activePageId = url.searchParams.get("pageId") || activePageId; return route.fulfill({ json: inspect() }); }
    if (endpoint.endsWith("/craft/preview")) { const value = request.postDataJSON(); previewPages.push(value.pageId); return route.fulfill({ contentType: "image/png", body: onePixelPng }); }
    if (endpoint.endsWith("/craft/commands")) {
      const body = request.postDataJSON(); const key = request.headers()["idempotency-key"];
      requests.push({ ...body, key });
      if (cached.has(key)) return route.fulfill({ json: cached.get(key) });
      if (options.conflict) return route.fulfill({ status: 409, json: { detail: { code: "studio_document_conflict" } } });
      activePageId = body.pageId || activePageId;
      for (const command of body.commands) {
        if (command.id === "host.pages.add") { current.nativeEditorState.pageProjects.push({ ...native.pageProjects[0], pageId: command.params.pageId, title: command.params.title }); activePageId = command.params.pageId; }
        if (command.id === "host.pages.move") { const index = current.nativeEditorState.pageProjects.findIndex((page) => page.pageId === command.params.pageId); const [item] = current.nativeEditorState.pageProjects.splice(index, 1); current.nativeEditorState.pageProjects.splice(command.params.index, 0, item); }
        if (command.id === "host.pages.delete") { current.nativeEditorState.pageProjects = current.nativeEditorState.pageProjects.filter((page) => page.pageId !== command.params.pageId); activePageId = current.nativeEditorState.pageProjects[0].pageId; }
      }
      current = { ...current, revision: current.revision + 1, version: current.version + 1 };
      const receipt = { document: current, inspection: inspect(), receiptId: `r-${current.revision}` }; cached.set(key, receipt);
      if (options.interruptCommit && requests.length === 1) return route.abort("failed");
      return route.fulfill({ json: receipt });
    }
    if (endpoint.endsWith("/craft/ai-commands")) {
      const body = request.postDataJSON(); ai.push(body); activePageId = body.pageId;
      current = { ...current, revision: current.revision + 1 };
      aiReceipt = { document: current, inspection: inspect(), receiptId: "ai-one" };
      if (options.interruptAI) return route.abort("failed");
      return route.fulfill({ json: aiReceipt });
    }
    if (endpoint.endsWith("/craft/render-jobs")) { renders++; return route.fulfill({ json: { id: "job-one", provider: "craft.photocraft", status: "queued", progress: 0, request: { documentRevision: current.revision } } }); }
    if (endpoint.endsWith("/jobs/job-one/cancel")) { cancelled = true; return route.fulfill({ json: { id: "job-one", provider: "craft.photocraft", status: "cancelled", progress: 0 } }); }
    if (endpoint.endsWith("/jobs/job-one")) return route.fulfill({ json: { id: "job-one", provider: "craft.photocraft", status: cancelled ? "cancelled" : "running", progress: 45 } });
    if (endpoint.endsWith("/native-project")) return route.fulfill({ contentType: "application/octet-stream", body: "native-fixture-for-interface-test" });
    if (endpoint.endsWith("/analytics/summary")) return route.fulfill({ json: {} });
    if (endpoint.endsWith("/radar/state")) return route.fulfill({ json: {} });
    return route.fulfill({ json: [] });
  });
  await page.goto("/content/post-one/edit?mode=carousel&document=document-one");
  await expect(page.getByRole("heading", { name: "Carrossel Clicko" })).toBeVisible();
  return { requests, previewPages, ai, getCurrent: () => current, getRenders: () => renders };
}

test("manual editing persists native page and revision; unsaved changes do not claim a new preview", async ({ page }) => {
  const state = await setup(page);
  await expect(page.getByAltText(/Prévia do projeto/)).toBeVisible();
  await page.getByRole("button", { name: /Desenvolvimento/ }).click();
  await expect.poll(() => state.previewPages.includes("page-two")).toBe(true);
  await page.getByRole("button", { name: "Título text" }).click();
  await page.getByLabel("Operação").selectOption("type.setText");
  await expect(page.getByLabel("Elemento *")).toHaveValue("title-page-two");
  await page.getByLabel("Texto *").fill("Direção Clicko");
  await page.getByRole("button", { name: "Aplicar ajuste" }).click();
  await expect(page.getByText(/1 ajustes pendentes/)).toBeVisible();
  await expect(page.getByText(/Prévia da revisão 1 · salve para atualizar/)).toBeVisible();
  await page.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(page.getByText("Salvo · revisão 2", { exact: true })).toBeVisible();
  expect(state.requests[0].pageId).toBe("page-two"); expect(state.requests[0].expectedRevision).toBe(1);
  expect(state.requests[0].commands).toEqual([{ id: "type.setText", params: { layer: "title-page-two", text: "Direção Clicko" } }]);
  expect(state.requests[0].key.length).toBeGreaterThan(8);
  expect(await page.evaluate(() => localStorage.getItem("clicko:craft:v1:user-one:workspace-one:document-one:photocraft"))).toBeNull();
});

test("autosave waits five seconds and uses a single immutable batch", async ({ page }) => {
  const state = await setup(page);
  await page.getByLabel("Operação").selectOption("type.setText");
  await page.getByLabel("Elemento *").fill("title-page-one"); await page.getByLabel("Texto *").fill("Salvamento automático");
  await page.getByRole("button", { name: "Aplicar ajuste" }).click();
  expect(state.requests.length).toBe(0);
  await expect(page.getByText("Salvo · revisão 2", { exact: true })).toBeVisible({ timeout: 12000 });
  expect(state.requests.length).toBe(1);
});

test("page creation, order and removal operate through native host commands", async ({ page }) => {
  const state = await setup(page);
  await page.getByRole("button", { name: "Adicionar página", exact: true }).click();
  await expect(page.getByRole("button", { name: /Página 3/ })).toBeVisible();
  await page.getByRole("button", { name: "Mover página para cima" }).click();
  expect(state.getCurrent().nativeEditorState.pageProjects[1].title).toBe("Página 3");
  await page.getByRole("button", { name: "Remover página", exact: true }).click();
  await expect(page.getByRole("button", { name: /Página 3/ })).toHaveCount(0);
  expect(state.requests.map((item) => item.commands[0].id)).toEqual(["host.pages.add", "host.pages.move", "host.pages.delete"]);
});

test("IA and undo share native command persistence, and jobs expose cancellation", async ({ page }) => {
  const state = await setup(page);
  await page.getByRole("button", { name: /Desenvolvimento/ }).click();
  await page.getByLabel("Pedido de edição com IA").fill("Deixe o título mais direto");
  await page.getByRole("button", { name: "Aplicar direção" }).click();
  await expect(page.getByText("Salvo · revisão 2", { exact: true })).toBeVisible();
  expect(state.ai[0]).toEqual({ expectedRevision: 1, instruction: "Deixe o título mais direto", pageId: "page-two" });
  await page.getByRole("button", { name: "Desfazer", exact: true }).click();
  await expect(page.getByText("Salvo · revisão 3", { exact: true })).toBeVisible();
  expect(state.requests[0].commands[0].id).toBe("host.history.undo");
  await page.getByRole("button", { name: "Exportar", exact: true }).click();
  await expect(page.getByRole("button", { name: "Cancelar", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await expect(page.getByText("Exportação · cancelada")).toBeVisible();
  expect(state.getRenders()).toBe(1);
});

test("conflict keeps recovery and never reports successful saving", async ({ page }) => {
  await setup(page, { conflict: true });
  await page.getByLabel("Operação").selectOption("type.setText");
  await page.getByLabel("Elemento *").fill("title-page-one"); await page.getByLabel("Texto *").fill("Conflito");
  await page.getByRole("button", { name: "Aplicar ajuste" }).click(); await page.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(page.getByText("Conflito de revisão", { exact: true })).toBeVisible();
  await expect(page.getByText("Salvo · revisão 2")).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("clicko:craft:v1:user-one:workspace-one:document-one:photocraft"))).toContain('"attempted":true');
});

test("retry after an interrupted committed save keeps the original idempotency key", async ({ page }) => {
  const state = await setup(page, { interruptCommit: true });
  await page.getByLabel("Operação").selectOption("type.setText");
  await page.getByLabel("Elemento *").fill("title-page-one"); await page.getByLabel("Texto *").fill("Uma vez");
  await page.getByRole("button", { name: "Aplicar ajuste" }).click(); await page.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(page.getByText("Sincronização interrompida")).toBeVisible();
  await expect(page.getByRole("button", { name: "Aplicar ajuste" })).toBeDisabled();
  await page.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(page.getByText("Salvo · revisão 2", { exact: true })).toBeVisible();
  expect(state.requests).toHaveLength(2); expect(state.requests[1]).toEqual(state.requests[0]);
  expect(state.getCurrent().revision).toBe(2);
});

test("unavailable engine and responsive layout never expose a legacy editor", async ({ page }) => {
  await setup(page, { available: false });
  await expect(page.getByRole("heading", { name: "Studio aguardando o motor de edição" })).toBeVisible();
  await expect(page.getByLabel("Operação")).toHaveCount(0); await expect(page.locator("iframe,canvas,.vs-shell,.cx-visual-canvas,.cx-carousel-stage")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Exportar", exact: true })).toBeDisabled();
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.locator(".craft-studio").evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  }
});

test("an interrupted AI result is recovered without a second paid submission", async ({ page }) => {
  const state = await setup(page, { interruptAI: true });
  await page.getByLabel("Pedido de edição com IA").fill("Ajuste uma vez");
  await page.getByRole("button", { name: "Aplicar direção" }).click();
  await expect(page.getByRole("button", { name: "Verificar pedido de IA" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Aplicar direção" })).toBeDisabled();
  const stored = await page.evaluate(() => localStorage.getItem("clicko:craft:v1:user-one:workspace-one:document-one:photocraft:ai"));
  expect(stored).toContain('"instruction":"Ajuste uma vez"');
  await page.reload();
  await page.getByRole("button", { name: "Verificar pedido de IA" }).click();
  await expect(page.getByRole("button", { name: "Verificar pedido de IA" })).toHaveCount(0);
  await expect(page.getByText("Salvo · revisão 2", { exact: true })).toBeVisible();
  expect(state.ai).toHaveLength(1);
});
