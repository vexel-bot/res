import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

function voiceFixture() {
  const pcmBytes = 128000;
  const wav = Buffer.alloc(44 + pcmBytes);
  wav.write("RIFF", 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write("WAVEfmt ", 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(16000, 24); wav.writeUInt32LE(32000, 28); wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34); wav.write("data", 36); wav.writeUInt32LE(pcmBytes, 40);
  for (let index = 0; index < pcmBytes / 2; index++) wav.writeInt16LE(Math.round(2000 * Math.sin(index * 0.17)), 44 + index * 2);
  return wav;
}

async function setup(request: APIRequestContext, page: Page, inStudio = false) {
  const registration = await request.post("/api/v1/auth/register", { data: {
    email: `editorial-${randomUUID()}@example.com`, name: "Revisor técnico", password: "editorial-test-password",
    workspaceName: "Editorial isolated test",
  } });
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const headers = { Authorization: `Bearer ${accessToken}` };
  const bootstrap = await (await request.get("/api/v1/bootstrap", { headers })).json();
  const workspaceId = bootstrap.workspaces[0].id;
  let postId: string | undefined;
  if (inStudio) {
    const post = await request.post("/api/v1/posts", { headers, data: {
      workspaceId, title: "Controle editorial integrado", platform: "Instagram", format: "video",
      copy: "Fixture de interface, não anúncio real.", status: "draft", author: "Revisor técnico",
      objective: "Verificar a inscrição no Studio", origin: "manual",
    } });
    expect(post.status()).toBe(201);
    postId = (await post.json()).id;
  }
  const upload = await request.post("/api/v1/assets/upload", { headers, multipart: {
    workspace_id: workspaceId, title: "Sinal técnico, não uma voz humana",
    file: { name: "technical.wav", mimeType: "audio/wav", buffer: voiceFixture() },
  } });
  expect(upload.status()).toBe(201);
  const asset = await upload.json();
  const created = await request.post("/api/v1/studios/v1/documents", { headers, data: {
    workspaceId, postId, title: "Editorial fixture", contentType: "video", brandRevision: 1,
    brief: { objective: "Verificar o controle editorial", audience: "Agências" },
    assets: [{ id: asset.id, mediaType: "audio/wav", checksum: asset.checksumSha256 }],
    composition: { pages: [{ id: "scene-1", width: 720, height: 1280, layers: [] }],
      mediaTimeline: { durationFrames: 15, frameRate: { numerator: 30, denominator: 1 },
        tracks: [{ id: "audio-1", kind: "audio", clips: [{ id: "clip-1", assetId: asset.id,
          timeline: { startFrame: 0, durationFrames: 15 }, source: { startMicroseconds: 0, durationMicroseconds: 500000 } }] }] } },
  } });
  expect(created.status()).toBe(201);
  const document = await created.json();
  await page.addInitScript((token) => localStorage.setItem("nexus_access_token", token), accessToken);
  if (inStudio) {
    await page.goto(`/content/${postId}/edit?mode=video`);
    await expect(page.locator(".vs-shell")).toBeVisible();
    await page.getByRole("button", { name: "Revisão", exact: true }).click();
  } else {
    await page.goto("/login");
    await page.evaluate(async (record) => {
      const modulePath = "/tests/fixtures/editorial-harness.tsx";
      const { mountEditorialHarness } = await import(modulePath);
      (window as any).__editorialHarness = mountEditorialHarness(record);
    }, document);
  }
  const panel = page.getByRole("region", { name: "Controle editorial UGC/avatar" });
  await expect(panel.getByText("Fluxo editorial não inscrito", { exact: true })).toBeVisible();
  return { panel, document, asset, headers, base: `/api/v1/studios/v1/documents/${document.documentId}` };
}

async function registerInPanel(panel: ReturnType<Page["getByRole"]>, assetId: string) {
  await panel.getByRole("button", { name: "Preparar inscrição UGC/avatar" }).click();
  await panel.getByLabel("CTA", { exact: true }).fill("Solicitar acesso ao piloto");
  await panel.getByRole("button", { name: "Adicionar beat" }).click();
  await panel.getByLabel("Mensagem", { exact: true }).fill("Demonstração da alteração");
  await panel.getByLabel("Ação visual", { exact: true }).fill("Comparar antes e depois");
  await panel.getByLabel("Motivo do corte", { exact: true }).fill("Tornar a consequência visível");
  await panel.getByRole("group", { name: "Evidências do beat 1", exact: true }).getByRole("checkbox").check();
  await panel.getByRole("button", { name: "Registrar plano editorial", exact: true }).click();
  await expect(panel.getByText("Render completo bloqueado", { exact: true })).toBeVisible();
}

test("painel registra plano e decisões explícitas; prévia confere bytes privados", async ({ page, request }) => {
  test.setTimeout(100_000);
  const { panel, base, headers, asset } = await setup(request, page);
  await registerInPanel(panel, asset.id);
  await panel.getByLabel("Arquivo da prévia").selectOption(asset.id);
  await panel.getByRole("button", { name: "Carregar prévia verificada" }).click();
  await expect(panel.locator("audio")).toHaveAttribute("src", /^blob:/);
  await panel.getByRole("button", { name: "Comparar referência e candidata" }).click();
  await panel.getByLabel("Arquivo de comparação").selectOption(asset.id);
  await panel.getByRole("button", { name: "Carregar comparação verificada" }).click();
  const original = panel.getByLabel("Evidência vocal", { exact: true });
  const comparison = panel.getByLabel("Comparação vocal", { exact: true });
  await expect(comparison).toHaveAttribute("src", /^blob:/);
  await original.evaluate(async (audio: HTMLAudioElement) => { audio.playbackRate = 2; await audio.play(); });
  expect(await original.evaluate((audio: HTMLAudioElement) => audio.playbackRate)).toBe(1);
  await comparison.evaluate(async (audio: HTMLAudioElement) => { await audio.play(); });
  await expect.poll(() => original.evaluate((audio: HTMLAudioElement) => audio.paused)).toBe(true);
  expect(await comparison.evaluate((audio: HTMLAudioElement) => audio.paused)).toBe(false);
  await comparison.evaluate((audio: HTMLAudioElement) => audio.pause());
  const approve = panel.getByRole("button", { name: "Aprovar etapa", exact: true });
  await expect(approve).toBeDisabled();
  await panel.getByRole("group", { name: "Evidências desta decisão", exact: true }).getByRole("checkbox").check();
  await panel.getByLabel("Observações e timestamps").fill("Fixture técnica sem fala humana: rejeitar como voz do anúncio.");
  await expect(approve).toBeDisabled();
  await panel.getByLabel("Examinei as evidências selecionadas").check();
  await panel.getByRole("button", { name: "Rejeitar etapa", exact: true }).click();
  await expect(panel.getByText("Voz: rejeitado na revisão vigente.", { exact: true })).toBeVisible();
  const state = await (await request.get(`${base}/editorial-readiness`, { headers })).json();
  expect(state.reviews[0].review.decision).toBe("rejected");
  expect(state.fullRenderEligible).toBe(false);
  expect(state.publicationAuthorized).toBe(false);
  await expect(panel.getByLabel("Examinei as evidências selecionadas")).not.toBeChecked();
  for (const width of [1024, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.locator("#editorial-harness").evaluate((host) => host.scrollWidth <= host.clientWidth)).toBe(true);
    await page.screenshot({ path: `artifacts/validation/editorial-review-${width}.png` });
  }
});

test("mudança de versão limpa confirmação e plano novo não herda aprovação", async ({ page, request }) => {
  test.setTimeout(100_000);
  const { panel, document, base, headers, asset } = await setup(request, page);
  await registerInPanel(panel, asset.id);
  await panel.getByRole("group", { name: "Evidências desta decisão", exact: true }).getByRole("checkbox").check();
  await panel.getByLabel("Observações e timestamps").fill("Rascunho de decisão ainda não enviado.");
  await panel.getByLabel("Examinei as evidências selecionadas").check();
  const changed = { ...document, title: "Nova versão não revisada" };
  const response = await request.put(base, { headers, data: { expectedRevision: document.revision, document: changed } });
  expect(response.status()).toBe(200);
  const next = await response.json();
  await page.evaluate((record) => (window as any).__editorialHarness.update(record), next);
  await expect(panel.getByText("O documento mudou. Registre um novo plano e revise suas evidências.")).toBeVisible();
  await expect(panel.getByLabel("Observações e timestamps")).toHaveValue("");
  await expect(panel.getByLabel("Examinei as evidências selecionadas")).not.toBeChecked();
  await expect(panel.getByRole("button", { name: "Aprovar etapa", exact: true })).toBeDisabled();
  expect(await page.evaluate(() => (window as any).__editorialHarness.getGate().blocked)).toBe(true);
  await panel.getByRole("button", { name: "Preparar nova versão do plano" }).click();
  await expect(panel.getByRole("button", { name: "Registrar plano editorial", exact: true })).toBeDisabled();
  await panel.getByLabel("Entendo que um novo plano exige novamente as sete revisões.").check();
  await panel.getByRole("button", { name: "Registrar plano editorial", exact: true }).click();
  await expect(panel.getByText("Plano registrado. As sete revisões começam pendentes.")).toBeVisible();
  const state = await (await request.get(`${base}/editorial-readiness`, { headers })).json();
  expect(state.blockers).toHaveLength(7);
  expect(state.reviews).toEqual([]);
});

test("resposta de mídia adulterada não vira uma prévia aprovada", async ({ page, request }) => {
  test.setTimeout(100_000);
  const { panel, asset } = await setup(request, page);
  await page.route(`**/api/v1/assets/${asset.id}/content`, (route) => route.fulfill({ status: 200, body: "tampered", contentType: "audio/wav" }));
  await panel.getByLabel("Arquivo da prévia").selectOption(asset.id);
  await panel.getByRole("button", { name: "Carregar prévia verificada" }).click();
  await expect(panel.getByText("Checksum divergente: a prévia foi bloqueada.")).toBeVisible();
  await expect(panel.locator("audio")).toHaveCount(0);
  await expect(panel.getByRole("button", { name: "Aprovar etapa", exact: true })).toBeDisabled();
});

test("falha de consulta fecha os controles e exige recuperação do estado do servidor", async ({ page, request }) => {
  test.setTimeout(100_000);
  const { panel, base, asset } = await setup(request, page);
  await registerInPanel(panel, asset.id);
  await panel.getByRole("group", { name: "Evidências desta decisão", exact: true }).getByRole("checkbox").check();
  await panel.getByLabel("Observações e timestamps").fill("Rascunho de teste, ainda sem decisão.");
  await panel.getByLabel("Examinei as evidências selecionadas").check();
  await expect(panel.getByRole("button", { name: "Aprovar etapa", exact: true })).toBeEnabled();
  await page.route(`**${base}/editorial-readiness`, (route) => route.abort("failed"));
  await panel.getByRole("button", { name: "Atualizar revisões", exact: true }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(panel.getByRole("button", { name: "Aprovar etapa", exact: true })).toBeDisabled();
  await expect(panel.getByRole("button", { name: "Preparar inscrição UGC/avatar", exact: true })).toBeDisabled();
  expect(await page.evaluate(() => (window as any).__editorialHarness.getGate().blocked)).toBe(true);
  await page.unroute(`**${base}/editorial-readiness`);
  await panel.getByRole("button", { name: "Atualizar revisões", exact: true }).click();
  await expect(panel.getByText("Render completo bloqueado", { exact: true })).toBeVisible();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await expect(panel.getByLabel("Examinei as evidências selecionadas")).not.toBeChecked();
  await expect(panel.getByRole("button", { name: "Aprovar etapa", exact: true })).toBeDisabled();
});

test("inscrição na aba Revisão bloqueia o botão de render no Video Studio e persiste após recarga", async ({ page, request }) => {
  test.setTimeout(100_000);
  const { panel, asset } = await setup(request, page, true);
  await registerInPanel(panel, asset.id);
  await panel.getByLabel("Arquivo da prévia").selectOption(asset.id);
  await panel.getByRole("button", { name: "Carregar prévia verificada" }).click();
  await expect(panel.locator("audio")).toHaveAttribute("src", /^blob:/);
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({ path: "artifacts/validation/editorial-review-studio.png", fullPage: true });
  await page.getByRole("button", { name: "Saída", exact: true }).click();
  await expect(panel).toBeHidden();
  const render = page.getByRole("button", { name: "Renderizar prova privada", exact: true });
  await expect(render).toBeDisabled();
  await page.reload();
  await page.getByRole("button", { name: "Saída", exact: true }).click();
  await expect(render).toBeDisabled();
  await page.getByRole("button", { name: "Revisão", exact: true }).click();
  await expect(panel.getByText("Render completo bloqueado", { exact: true })).toBeVisible();
  await expect(panel.getByLabel("Arquivo da prévia")).toHaveValue("");
  await expect(panel.locator("audio")).toHaveCount(0);
});
