import { expect, test } from "@playwright/test";

test("Review autenticado exibe páginas fixadas e recupera conflito sem aprovar conteúdo novo", async ({ page, request }) => {
  test.setTimeout(90_000);
  const registration = await request.post("/api/v1/auth/register", { data: {
    email: `review-snapshot-${Date.now()}@example.com`, name: "Revisor real do teste", password: "senha-e2e-review-123", workspaceName: "Review binding",
  }});
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const headers = { Authorization: `Bearer ${accessToken}` };
  const bootstrap = await (await request.get("/api/v1/bootstrap", { headers })).json();
  const workspaceId = bootstrap.workspaces[0].id;
  const postResponse = await request.post("/api/v1/posts", { headers, data: { workspaceId, title: "Peça real de revisão", platform: "Instagram", format: "carousel", copy: "Copy congelada", status: "draft", author: "Revisor" }});
  expect(postResponse.status()).toBe(201);
  const postId = (await postResponse.json()).id;
  const docResponse = await request.post("/api/v1/studios/v1/documents", { headers, data: {
    workspaceId, postId, title: "Composição fixada", contentType: "carousel", brandRevision: 1,
    brief: { objective: "Validar revisão real", audience: "Operadores" },
    composition: { pages: ["#112233", "#334455"].map((background, i) => ({
      id: `page-${i + 1}`, role: i ? "content" : "hook", width: 1080, height: 1350, safeArea: 48, background,
      layers: [{ id: `text-${i}`, kind: "text", name: `Copy fixada ${i + 1}`, x: 90, y: 120, width: 900, height: 300, properties: { text: `Copy fixada ${i + 1}`, fontSize: 76, color: "#ffffff" } }],
    })) },
  }});
  expect(docResponse.status()).toBe(201);
  const document = await docResponse.json();
  const docUrl = `/api/v1/studios/v1/documents/${document.documentId}`;
  expect((await request.post(`${docUrl}/reviews`, { headers, data: {} })).status()).toBe(201);
  await page.addInitScript(token => {
    localStorage.setItem("nexus_access_token", token);
    localStorage.setItem("clicko:splash-seen", "true");
  }, accessToken);
  await page.goto(`/approvals/${postId}`);
  const image = page.getByTestId("review-snapshot-image");
  const approve = page.getByRole("button", { name: /Aprovar esta versão/ });
  await expect(approve).toBeEnabled();
  await expect(image).toHaveAttribute("src", /^blob:/);
  await expect(page.locator(".cx-review-thumbs [data-action-id='REVIEW-SELECT-SLIDE']")).toHaveCount(2);
  await expect(page.getByText("Contraste aprovado", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Reduzi o texto do slide 3 e reforcei a origem.")).toHaveCount(0);
  const pixel = async () => image.evaluate(img => {
    const source = img as HTMLImageElement;
    const canvas = document.createElement("canvas"); canvas.width = 1080; canvas.height = 1350;
    const ctx = canvas.getContext("2d")!; ctx.drawImage(source, 0, 0);
    return Array.from(ctx.getImageData(10, 10, 1, 1).data).slice(0, 3);
  });
  expect(await pixel()).toEqual([17, 34, 51]);
  await page.getByRole("button", { name: "Revisar slide 2" }).click();
  await expect(page.getByTestId("review-studio-headline")).toHaveText("Copy fixada 2");
  await expect(approve).toBeEnabled();
  expect(await pixel()).toEqual([51, 68, 85]);
  for (const width of [1440, 1024, 768, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({ path: `artifacts/validation/review-snapshot-${width}.png`, fullPage: true });
  }
  await page.getByRole("button", { name: "Editar", exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole("button", { name: "Editar", exact: true })).toBeVisible();
  await page.getByRole("textbox", { name: "Comentário da decisão" }).fill("Revisão do snapshot e da oferta.");
  const changed = await (await request.get(docUrl, { headers })).json();
  changed.title = "Nova direção não revisada";
  changed.composition.pages[1].background = "#ff0000";
  expect((await request.put(docUrl, { headers, data: { expectedRevision: changed.revision, document: changed } })).status()).toBe(200);
  await approve.click();
  await expect(page.getByText("Esta revisão não pode aprovar o documento atual", { exact: true })).toBeVisible();
  await expect(approve).toBeDisabled();
  expect((await (await request.get(docUrl, { headers })).json()).status).toBe("draft");
  expect(await pixel()).toEqual([51, 68, 85]);
  expect((await request.post(`${docUrl}/reviews`, { headers, data: {} })).status()).toBe(201);
  await page.reload();
  await expect(approve).toBeEnabled();
  await page.getByRole("button", { name: "Revisar slide 2" }).click();
  await expect(approve).toBeEnabled();
  expect(await pixel()).toEqual([255, 0, 0]);
  await approve.click();
  await expect(page).toHaveURL(new RegExp(`/publish/${postId}$`));
  expect((await (await request.get(docUrl, { headers })).json()).status).toBe("approved");
});
