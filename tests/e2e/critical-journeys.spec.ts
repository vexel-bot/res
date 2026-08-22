import { expect, test } from "@playwright/test";
import { STITCH_SCREENS } from "../../src/product/screenManifest";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("clicko:splash-seen", "true"),
  );
});

async function navigateSpa(
  page: import("@playwright/test").Page,
  route: string,
) {
  await page.evaluate((target) => {
    history.pushState({}, "", target);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, route);
  await expect(page.locator("main").first()).toBeVisible();
}

const canonicalRoutes = [
  "/dashboard",
  "/dashboard?create=open",
  "/radar",
  "/radar/opportunities/op-festival",
  "/campaigns/new?opportunity=op-festival",
  "/campaigns/campaign-aurora",
  "/content",
  "/content/post-ritual/edit?mode=editorial",
  "/content/post-ritual/edit?mode=visual",
  "/approvals/post-ritual?view=creative",
  "/calendar",
  "/publish/post-ritual",
  "/content/post-ritual",
  "/content/post-ritual/remix",
  "/campaigns/campaign-aurora/world",
  "/campaigns/campaign-aurora/moodboard",
  "/content/post-ritual/edit?mode=carousel",
  "/brand-memory",
  "/library/assets",
  "/analytics/learning",
  "/factory",
  "/dashboard?spotlight=open",
  "/projects",
  "/dashboard?activity=open",
  "/dashboard?workspace=menu",
  "/apps",
];

const approvedPhase5Routes = [
  "/content/post-ritual/edit?mode=presenter",
  "/apps/instagram",
  "/apps/facebook",
  "/apps/tiktok",
  "/apps/youtube",
  "/apps/x",
  "/apps/linkedin",
  "/apps/pinterest",
  "/apps/threads",
  "/apps/twitch",
  "/apps/google-business-profile",
];

test("Home canônica é a entrada e mantém os quatro destinos globais aprovados", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("heading", { name: "O que vamos criar hoje?" }),
  ).toBeVisible();
  for (const destination of ["Home", "Projetos", "Biblioteca", "Publicar"]) {
    await expect(
      page.getByRole("button", { name: destination, exact: true }),
    ).toBeVisible();
  }
  await expect(page.getByRole("button", { name: /Criar C/ })).toBeVisible();
  await expect(page.locator(".cx-demo-banner")).toContainText(
    "Workspace demonstrativo",
  );
  await expect(page.locator("iframe")).toHaveCount(0);
});

test("jornada criativa vai de projeto a revisão e calendário", async ({
  page,
}) => {
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Projetos", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Projetos", exact: true }),
  ).toBeVisible();
  await page.locator(".cx-project-resume > button").first().click();
  await expect(
    page.getByRole("heading", { name: "Ritual Café Aurora" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Criar peça", exact: true }).click();
  await expect(page).toHaveURL(/\/content\/draft\/edit\?mode=visual/);
  await expect(page.locator(".cx-visual-stage")).toBeVisible();
  await page
    .getByRole("button", { name: "Enviar para revisão", exact: true })
    .click();
  await expect(page).toHaveURL(/\/approvals\/post-ritual\?view=creative/);
  await page
    .getByRole("button", { name: /Aprovar esta versão/, exact: false })
    .click();
  await expect(page).toHaveURL(/\/calendar$/);
  await expect(
    page.getByRole("heading", { name: "Calendário editorial" }),
  ).toBeVisible();
});

test("Spotlight abre por teclado, filtra e devolve o foco", async ({
  page,
}) => {
  await page.goto("/dashboard");
  const trigger = page.getByRole("button", { name: /Buscar projetos/ });
  await trigger.focus();
  await page.keyboard.press("Control+K");
  const dialog = page.getByRole("dialog", { name: "Busca global" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("textbox").fill("Radar");
  await expect(dialog.getByRole("button", { name: /Radar/ })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("produção aprovada conecta hub, editores, revisão, biblioteca e fábrica", async ({
  page,
}) => {
  await page.goto("/content");
  await expect(
    page.getByRole("heading", { name: "Criar e organizar conteúdo" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Retomar/ }).click();
  await expect(page).toHaveURL(/mode=carousel/);
  await expect(page.locator(".cx-carousel-approved")).toBeVisible();
  await page.getByRole("button", { name: "Adicionar slide" }).click();
  await expect(page.getByText("7 slides · 48s de leitura")).toBeVisible();

  await navigateSpa(page, "/content/post-ritual/edit?mode=editorial");
  await page.getByRole("button", { name: "Abrir no Visual" }).click();
  await expect(page).toHaveURL(/mode=visual/);
  await page.getByRole("button", { name: "Enviar para revisão" }).click();
  await expect(page).toHaveURL(/\/approvals\/post-ritual/);
  await page
    .getByPlaceholder(/Explique o que deve mudar/)
    .fill("Reforçar o contraste do CTA.");
  await page.getByRole("button", { name: /Solicitar ajustes/ }).click();
  await expect(page.getByText("Ajustes solicitados")).toBeVisible();

  await navigateSpa(page, "/library/assets");
  await page.getByRole("button", { name: "Inserir no editor" }).click();
  await expect(page).toHaveURL(/mode=visual/);
  await navigateSpa(page, "/factory");
  await page.getByRole("button", { name: "Iniciar nova rodada" }).click();
  await expect(
    page.getByText("Nova rodada iniciada com contexto preservado."),
  ).toBeVisible();
});

test("publicação e aprendizado preservam handoff, evidência e linhagem", async ({
  page,
}) => {
  await page.goto("/calendar");
  await expect(
    page.getByRole("heading", { name: "Calendário editorial" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Abrir Publisher Control" }).click();
  await expect(page).toHaveURL(/\/publish\/post-ritual$/);
  await expect(
    page.getByRole("button", { name: /Publicar agora/ }),
  ).toBeDisabled();
  await page.getByRole("button", { name: /Agendar internamente/ }).click();
  await expect(
    page.getByRole("button", { name: /Agendamento salvo/ }),
  ).toBeVisible();

  await navigateSpa(page, "/content/post-ritual");
  await expect(
    page.getByRole("heading", { name: "Ritual de foco" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Abrir no Reuse Lab/ })
    .first()
    .click();
  await expect(page).toHaveURL(/\/content\/post-ritual\/remix$/);
  await page.getByRole("button", { name: "Criar derivação" }).click();
  await expect(page.getByText("Nova derivação v1 criada")).toBeVisible();

  await navigateSpa(page, "/analytics/learning");
  await page.getByRole("button", { name: "Criar rodada" }).click();
  await expect(
    page.getByRole("button", { name: "Rodada criada" }),
  ).toBeVisible();
});

test("Apps e Presenter preservam permissões, gates e estados honestos", async ({
  page,
}) => {
  await page.goto("/apps");
  await page.getByPlaceholder("Buscar integração").fill("TikTok");
  await page.getByRole("button", { name: /TikTok/ }).click();
  await expect(page).toHaveURL(/\/apps\/tiktok$/);
  await page.getByRole("button", { name: "Testar conexão" }).click();
  await expect(page.locator(".cx-social-health")).toContainText(
    "Conexão verificada",
  );
  await page.getByRole("button", { name: "Publicação", exact: true }).click();
  await expect(page.getByText("Publicação de TikTok")).toBeVisible();

  await navigateSpa(page, "/content/post-ritual/edit?mode=presenter");
  await expect(
    page.getByRole("heading", { name: "Mariana × Café Aurora" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Gerar primeiro teste" }).click();
  await expect(page.getByText("TESTES 1/3")).toBeVisible();
  await page.getByRole("button", { name: "Abrir captura" }).click();
  await expect(page.getByRole("button", { name: "Capturado" })).toBeVisible();
  await page.getByRole("button", { name: "Sim", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sim", exact: true }),
  ).toHaveClass(/is-active/);
});

test("os 11 alvos adicionais aprovados montam sem iframe ou erro", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/apps");
  for (const route of approvedPhase5Routes) {
    await navigateSpa(page, route);
    await expect(page.locator(".cx-product"), route).toBeVisible();
    await expect(page.locator("iframe"), route).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});

test("Radar preserva o contexto até a direção e o moodboard da campanha", async ({
  page,
}) => {
  await page.goto("/radar");
  await expect(page.locator(".cx-radar-queue > button").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Transformar em campanha", exact: true })
    .click();
  await expect(page).toHaveURL(/\/campaigns\/new\?opportunity=/);
  await expect(
    page.getByRole("heading", {
      name: "Transforme a oportunidade em campanha",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Refinar direção" }).click();
  await expect(page.getByText(/Direção inicial refinada/)).toBeVisible();
  await page.getByRole("button", { name: "Criar campanha" }).click();
  await expect(page).toHaveURL(/\/campaigns\/campaign-aurora$/);

  await navigateSpa(page, "/campaigns/campaign-aurora/world");
  await page.getByRole("button", { name: "Explorar outro ângulo" }).click();
  await expect(
    page.getByRole("button", { name: "Novo ângulo aplicado" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Moodboard", exact: true }).click();
  await expect(page).toHaveURL(/\/campaigns\/campaign-aurora\/moodboard$/);
  await page.getByPlaceholder("Buscar referências").fill("produto");
  await expect(page.locator(".cx-masonry figure")).toHaveCount(2);
  await page.getByRole("button", { name: "Adicionar" }).click();
  await page.getByRole("button", { name: "Compartilhar" }).click();
  await expect(
    page.getByRole("button", { name: "Link copiado" }),
  ).toBeVisible();
});

test("as 26 superfícies canônicas montam sem iframe, erro ou rota vazia", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/dashboard");
  for (const route of canonicalRoutes) {
    await navigateSpa(page, route);
    await expect(page.locator(".cx-product"), route).toBeVisible();
    await expect(page.locator("iframe"), route).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});

test("matriz legada mantém os dois projetos válidos em 38 + 19", async ({
  page,
}) => {
  await page.goto("/reference/screens");
  await expect(
    page.getByRole("heading", { name: "57 telas implementadas no sistema" }),
  ).toBeVisible();
  await expect(
    page
      .locator("main")
      .getByRole("button")
      .filter({ hasText: /^A\d{2}/ }),
  ).toHaveCount(38);
  await expect(
    page
      .locator("main")
      .getByRole("button")
      .filter({ hasText: /^B\d{2}/ }),
  ).toHaveCount(19);
  await expect(page.getByText("Creative OS Redesign")).toHaveCount(0);
});

test("as 57 referências continuam navegáveis ao lado do produto canônico", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/reference/screens");
  for (const screen of STITCH_SCREENS) {
    await navigateSpa(page, screen.route);
    await expect(
      page.locator(".cx-product, .clicko-lab-shell").first(),
      screen.id,
    ).toBeVisible();
    await expect(page.locator("iframe"), screen.id).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});

test("feedback de acabamento elimina recortes e reforça a inteligência criativa", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/dashboard");
  for (const route of [
    "/content",
    "/library/assets",
    "/calendar",
    "/content/post-ritual/edit?mode=editorial",
    "/content/post-ritual/edit?mode=visual",
  ]) {
    await navigateSpa(page, route);
    const widths = await page.locator(".cx-product").evaluate((element) => ({
      client: element.clientWidth,
      scroll: element.scrollWidth,
    }));
    expect(widths.scroll, route).toBeLessThanOrEqual(widths.client + 1);
  }

  const selection = page.locator(".cx-selection");
  const headline = selection.locator("strong");
  await expect(headline).toContainText("O BRASIL");
  const [selectionBox, headlineBox] = await Promise.all([
    selection.boundingBox(),
    headline.boundingBox(),
  ]);
  expect(selectionBox).not.toBeNull();
  expect(headlineBox).not.toBeNull();
  expect(headlineBox!.x).toBeGreaterThanOrEqual(selectionBox!.x);
  expect(headlineBox!.x + headlineBox!.width).toBeLessThanOrEqual(
    selectionBox!.x + selectionBox!.width + 1,
  );
  await page.getByRole("button", { name: "Recolher" }).click();
  await expect(page.locator(".cx-slide-strip-approved > div")).toBeHidden();

  await navigateSpa(page, "/factory");
  await expect(page.getByText("ENTRADAS VIVAS")).toBeVisible();
  await expect(page.getByText("RECEITA ESTRATÉGICA APLICADA")).toBeVisible();
  await expect(page.getByText("MOTOR CLICKO · PROCESSANDO")).toBeVisible();
  await expect(page.getByText("GATES HUMANOS")).toBeVisible();

  await navigateSpa(page, "/projects");
  await expect(
    page.getByRole("heading", { name: /Universos criativos em movimento/ }),
  ).toBeVisible();
  await expect(page.locator(".cx-project-table")).toHaveCount(0);

  await navigateSpa(page, "/apps");
  expect(await page.locator(".cx-brand-icon").count()).toBeGreaterThanOrEqual(
    15,
  );
  await navigateSpa(page, "/content/post-ritual/edit?mode=presenter");
  await expect(page.getByText("PRODUÇÃO APROVADA")).toBeVisible();
  await expect(page.getByText("EXPLORATION")).toHaveCount(0);
  await expect(page.locator(".cx-presenter-focusbar article")).toHaveCount(3);
});

test("workspace Horizonte prova o produto com uma segunda marca", async ({
  page,
}) => {
  await page.goto("/dashboard?brand=horizonte");
  await expect(
    page.getByRole("button", { name: /Trocar workspace: Clínica Horizonte/ }),
  ).toBeVisible();
  await expect(page.getByText("4 oportunidades de prevenção")).toBeVisible();
  await expect(page.getByText(/Clínica Horizonte/).first()).toBeVisible();

  await page.getByRole("button", { name: "Projetos", exact: true }).click();
  await expect(page).toHaveURL(/\/projects\?brand=horizonte/);
  await expect(
    page.getByRole("heading", { name: "Cuidar antes da urgência" }).first(),
  ).toBeVisible();

  await navigateSpa(page, "/factory?brand=horizonte");
  await expect(page.getByText("Clareza clínica sem alarmismo")).toBeVisible();
  await expect(page.getByText("Check-up integrado")).toBeVisible();
});

test("API funcional permanece disponível junto ao produto", async ({
  request,
}) => {
  const health = await request.get("/health/live");
  expect(health.ok()).toBeTruthy();
});
