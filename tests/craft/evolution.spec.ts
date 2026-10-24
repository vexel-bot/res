import { expect, test } from "@playwright/test";

test("evolution filters records, reads exact documents and never executes document HTML", async ({
  page,
}) => {
  const entries = [
    {
      id: "identity-research",
      date: "2026-10-21",
      category: "analysis",
      status: "in_progress",
      title: "Personagens, rosto e voz",
      summary: "Pesquisa de modelos",
      impact: "Escolher identidade",
      document: "identity.md",
      requirements: ["Clonar voz autorizada"],
      evidence: ["https://github.com/meituan-longcat/LongCat-Video"],
    },
    {
      id: "craft",
      date: "2026-10-16",
      category: "update",
      status: "integrated",
      title: "Crafts integrados",
      summary: "Motores completos",
      impact: "Composição",
      document: "craft.md",
      requirements: [],
      evidence: [],
    },
  ];
  await page.addInitScript(() =>
    localStorage.setItem("nexus_access_token", "interface-fixture"),
  );
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/bootstrap"))
      return route.fulfill({ json: { user: { id: "user" }, workspaces: [] } });
    if (path.endsWith("/product-evolution"))
      return route.fulfill({ json: { entries, updatedAt: "2026-10-21" } });
    if (path.endsWith("/identity-research/document"))
      return route.fulfill({
        contentType: "text/markdown",
        body: "# Pesquisa de identidade",
      });
    if (path.endsWith("/identity-research"))
      return route.fulfill({
        json: {
          ...entries[0],
          markdown:
            '# Pesquisa de identidade\n\n## O que falta\n\n- Testar PT-BR\n- Conferir sincronismo\n\n<img src=x onerror="window.pwned=true">',
          checksumSha256: "a".repeat(64),
        },
      });
    return route.fulfill({ json: [] });
  });
  await page.goto("/evolution");
  await expect(
    page.getByRole("heading", { name: "O que estamos construindo juntos." }),
  ).toBeVisible();
  await page.getByLabel("Pesquisar evolução").fill("voz");
  await expect(
    page.getByRole("button", { name: /Crafts integrados/ }),
  ).toHaveCount(0);
  await page.getByLabel("Tipo de registro").selectOption("analysis");
  await page.getByRole("button", { name: /Personagens, rosto e voz/ }).click();
  await expect(
    page.getByRole("heading", { name: "O que falta" }),
  ).toBeVisible();
  await expect(page.getByText("Testar PT-BR", { exact: true })).toBeVisible();
  await expect(page.locator(".ev-document img")).toHaveCount(0);
  expect(await page.evaluate(() => (window as any).pwned)).toBeUndefined();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar .md" }).click();
  expect((await download).suggestedFilename()).toBe("identity.md");
  await page.setViewportSize({ width: 320, height: 800 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("failed evolution requests expose retry without invented records", async ({
  page,
}) => {
  let attempts = 0;
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/product-evolution")) {
      attempts++;
      return route.fulfill({
        status: 503,
        json: { detail: "Histórico temporariamente indisponível" },
      });
    }
    return route.fulfill({ json: { user: { id: "user" }, workspaces: [] } });
  });
  await page.goto("/evolution");
  await expect(page.getByRole("alert")).toContainText(
    "Histórico temporariamente indisponível",
  );
  await page.getByRole("button", { name: "Tentar novamente" }).click();
  await expect.poll(() => attempts).toBeGreaterThan(1);
  await expect(page.locator(".ev-list button")).toHaveCount(0);
});
