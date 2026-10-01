import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("pré-flight autenticado usa arte e legenda aprovadas, baixa pacote e persiste só o agendamento interno", async ({ page, request, context }) => {
  test.setTimeout(90_000);
  const registration = await request.post("/api/v1/auth/register", { data: {
    email: `publication-preflight-${Date.now()}@example.com`,
    name: "Operador de publicação",
    password: "senha-e2e-preflight-123",
    workspaceName: "Handoff verificado",
  }});
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const headers = { Authorization: `Bearer ${accessToken}` };
  const bootstrap = await (await request.get("/api/v1/bootstrap", { headers })).json();
  const workspaceId = bootstrap.workspaces[0].id;
  const postResponse = await request.post("/api/v1/posts", { headers, data: {
    workspaceId,
    title: "UGC natural aprovado",
    platform: "Instagram",
    format: "carousel",
    copy: "Legenda real e aprovada do teste.",
    hashtags: ["#UGC", "#SemNarracao"],
    status: "draft",
    author: "Operador",
  }});
  expect(postResponse.status()).toBe(201);
  const postId = (await postResponse.json()).id;
  const documentResponse = await request.post("/api/v1/studios/v1/documents", { headers, data: {
    workspaceId,
    postId,
    title: "UGC natural aprovado",
    contentType: "carousel",
    brandRevision: 1,
    brief: { objective: "Validar handoff real", audience: "Operadores" },
    composition: { pages: ["#214365", "#547698"].map((background, index) => ({
      id: `page-${index + 1}`,
      role: index ? "payoff" : "hook",
      width: 1080,
      height: 1350,
      safeArea: 48,
      background,
      layers: [{
        id: `title-${index + 1}`,
        kind: "text",
        name: `Cena ${index + 1}`,
        x: 90,
        y: 120,
        width: 900,
        height: 260,
        properties: { text: `Cena natural ${index + 1}`, fontSize: 72, color: "#ffffff" },
      }],
    })) },
  }});
  expect(documentResponse.status()).toBe(201);
  const document = await documentResponse.json();
  const documentUrl = `/api/v1/studios/v1/documents/${document.documentId}`;
  const reviewResponse = await request.post(`${documentUrl}/reviews`, { headers, data: {} });
  expect(reviewResponse.status()).toBe(201);
  const review = await reviewResponse.json();
  expect((await request.post(`/api/v1/studios/v1/reviews/${review.id}/decisions`, {
    headers,
    data: { action: "approve", comment: "Arte e legenda conferidas." },
  })).status()).toBe(200);

  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.addInitScript(token => {
    localStorage.setItem("nexus_access_token", token);
    localStorage.setItem("clicko:splash-seen", "true");
  }, accessToken);
  await page.goto(`/publish/${postId}`);
  await expect(page.getByRole("heading", { name: "Controle de publicação" })).toBeVisible();
  await expect(page.getByText(/Conteúdos \/ UGC natural aprovado \/ Publicação/)).toBeVisible();
  await expect(page.getByText("Café Aurora", { exact: false })).toHaveCount(0);
  await expect(page.getByText("6 slides", { exact: true })).toHaveCount(0);
  const image = page.getByTestId("review-snapshot-image");
  await expect(image).toHaveAttribute("src", /^blob:/);
  expect(await image.evaluate(img => {
    const source = img as HTMLImageElement;
    const canvas = document.createElement("canvas");
    canvas.width = 1080; canvas.height = 1350;
    const context = canvas.getContext("2d")!;
    context.drawImage(source, 0, 0);
    return Array.from(context.getImageData(10, 10, 1, 1).data).slice(0, 3);
  })).toEqual([33, 67, 101]);
  await expect(page.getByRole("button", { name: "Agendar internamente" })).toBeEnabled();

  await page.getByRole("button", { name: "Legenda", exact: true }).click();
  await expect(page.getByText("Legenda real e aprovada do teste.", { exact: false }).first()).toBeVisible();
  await page.getByRole("button", { name: "Copiar legenda" }).click();
  expect((await page.evaluate(() => navigator.clipboard.readText())).replaceAll("\r\n", "\n")).toBe("Legenda real e aprovada do teste.\n\n#UGC #SemNarracao");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar arquivos" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(`clicko-${postId}-v1.zip`);
  expect(await download.failure()).toBeNull();

  const scheduleValue = await page.evaluate(() => {
    const date = new Date(Date.now() + 48 * 60 * 60 * 1000);
    date.setMinutes(0, 0, 0);
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 16);
  });
  await page.getByLabel("Data e horário do agendamento interno").fill(scheduleValue);
  await page.getByRole("button", { name: "Agendar internamente" }).click();
  await expect(page.getByText("Agendamento interno salvo", { exact: true })).toBeVisible();
  const preflight = await (await request.get(
    `/api/v1/studios/v1/reviews/${review.id}/publication-preflight`, { headers },
  )).json();
  expect(preflight.status).toBe("scheduled");
  expect(preflight.scheduledAt).toBeTruthy();
  await page.reload();
  await expect(page.getByRole("button", { name: "Atualizar agendamento interno" })).toBeEnabled();
  expect(await page.getByRole("button", { name: "Atualizar agendamento interno" }).locator("span").evaluate(element => element.getBoundingClientRect().width)).toBeGreaterThan(140);
  const accessibility = await new AxeBuilder({ page }).include(".cx-publisher-approved").analyze();
  expect(accessibility.violations, accessibility.violations.map(item => `${item.id}: ${item.description}`).join("\n")).toEqual([]);

  for (const width of [1440, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    const layout = await page.evaluate(() => ({
      viewport: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      offenders: Array.from(document.querySelectorAll("body *"))
        .map(element => {
          const htmlElement = element as HTMLElement;
          return { className: htmlElement.className, right: Math.round(htmlElement.getBoundingClientRect().right), width: Math.round(htmlElement.getBoundingClientRect().width) };
        })
        .filter(item => item.right > window.innerWidth + 1)
        .slice(0, 8),
    }));
    expect(layout.scrollWidth, JSON.stringify(layout)).toBeLessThanOrEqual(layout.viewport);
    if (width === 360) {
      await expect.poll(() => page.locator(".cx-sidebar").evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(0);
    }
    await page.screenshot({ path: `artifacts/validation/publication-preflight-${width}.png`, fullPage: true });
  }

  expect((await request.patch(`/api/v1/posts/${postId}`, {
    headers,
    data: { copy: "Copy alterada depois da aprovação." },
  })).status()).toBe(200);
  await page.reload();
  await expect(page.getByText("O pré-flight não está disponível", { exact: true })).toBeVisible();
  await expect(page.getByText("O Brasil cabe em uma xícara.", { exact: false })).toHaveCount(0);
});
