import { expect, test, type Page } from "@playwright/test";

const workspace = {
  id: "workspace-one",
  name: "Marca de teste",
  brandProfile: {},
};
const image = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZlLkAAAAASUVORK5CYII=",
  "base64",
);

async function setup(
  page: Page,
  options: { failure?: boolean; saved?: boolean; conflict?: boolean } = {},
) {
  let project: any = options.saved
    ? {
        id: "project-one",
        workspaceId: workspace.id,
        title: "Origem do café",
        brandName: workspace.name,
        objective: "Explicar como comparar a origem do café.",
        audience: "Pessoas que fazem café em casa",
        evidence: "",
        format: "carousel",
        front: "content",
        revision: 4,
        status: "delivery",
        directionId: "guide",
        directions: [],
        documentId: "document-one",
        postId: "post-one",
        jobId: "job-one",
      }
    : undefined;
  let review: any;
  const requests: { method: string; path: string; body: any }[] = [];
  const document = {
    documentId: "document-one",
    workspaceId: workspace.id,
    title: "Origem do café",
    contentType: "carousel",
    revision: 2,
    version: 2,
    composition: { pages: [{ id: "page-one" }, { id: "page-two" }] },
  };
  await page.addInitScript(() =>
    localStorage.setItem("nexus_access_token", "isolated-interface-fixture"),
  );
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const body = request.postData() ? request.postDataJSON() : undefined;
    requests.push({ method: request.method(), path, body });
    if (path.endsWith("/bootstrap"))
      return route.fulfill({
        json: {
          user: { id: "user-one" },
          workspaces: [workspace],
          suggestions: [],
        },
      });
    if (path.endsWith("/studios/v1/projects")) {
      if (request.method() === "GET")
        return route.fulfill({ json: project ? [project] : [] });
      project = {
        ...body,
        id: "project-one",
        brandName: workspace.name,
        revision: 1,
        documentId: null,
        jobId: null,
        directionId: null,
        status: "direction",
        planningBasis: "Esboço derivado do pedido, sem geração por LLM.",
        directions: ["guide", "demonstrate"].map((id) => ({
          id,
          title: body.title,
          opening: body.title,
          rationale: `Direção para ${body.audience}`,
          beats: [body.objective],
          cta: "Saiba mais",
        })),
      };
      return route.fulfill({ status: 201, json: project });
    }
    if (path.endsWith("/projects/project-one/produce")) {
      if (options.failure) {
        project = {
          ...project,
          revision: project.revision + 2,
          status: "production_failed",
          documentId: "document-one",
        };
        return route.fulfill({
          status: 422,
          json: { detail: "craft_engine_unavailable" },
        });
      }
      project = {
        ...project,
        revision: project.revision + 2,
        status: "delivery",
        documentId: "document-one",
        postId: "post-one",
        jobId: "job-one",
      };
      return route.fulfill({ json: project });
    }
    if (path.endsWith("/projects/project-one")) {
      if (request.method() === "PATCH") {
        if (options.conflict)
          return route.fulfill({
            status: 409,
            json: { detail: "O projeto mudou em outra sessão." },
          });
        project = {
          ...project,
          directionId: body.directionId,
          revision: project.revision + 1,
        };
      }
      return route.fulfill({ json: project });
    }
    if (path.endsWith("/documents/document-one"))
      return route.fulfill({ json: document });
    if (path.endsWith("/documents/document-one/versions"))
      return route.fulfill({
        json: [
          { version: 1, label: "Pedido" },
          { version: 2, label: "Primeira versão" },
        ],
      });
    if (path.endsWith("/documents/document-one/craft/preview")) {
      if (options.failure)
        return route.fulfill({
          status: 503,
          json: { detail: "craft_engine_unavailable" },
        });
      return route.fulfill({ contentType: "image/png", body: image });
    }
    if (path.endsWith("/jobs/job-one"))
      return route.fulfill({
        json: { id: "job-one", status: "succeeded", progress: 100, result: {} },
      });
    if (path.endsWith("/reviews/latest"))
      return review
        ? route.fulfill({ json: review })
        : route.fulfill({ status: 404, json: { detail: "No review" } });
    if (path.endsWith("/documents/document-one/reviews")) {
      review = {
        id: "review-one",
        documentVersion: 2,
        status: "requested",
        snapshot: document,
      };
      return route.fulfill({ json: review });
    }
    if (path.includes("/reviews/review-one/pages/"))
      return route.fulfill({ contentType: "image/png", body: image });
    if (path.endsWith("/reviews/review-one/decisions")) {
      review = {
        ...review,
        status: body.action === "approve" ? "approved" : "changes_requested",
      };
      return route.fulfill({ json: review });
    }
    if (path.endsWith("/capabilities"))
      return route.fulfill({ json: { capabilities: [] } });
    if (path.endsWith("/analytics/summary") || path.endsWith("/radar/state"))
      return route.fulfill({ json: {} });
    return route.fulfill({ json: [] });
  });
  await page.goto(
    options.saved
      ? "/studios?department&project=project-one"
      : "/studios?department",
  );
  await expect(page.getByTestId("department-studio")).toBeVisible();
  await expect(page.getByText("Carregando projetos…")).toHaveCount(0);
  return { requests, getProject: () => project };
}

async function requestDirections(page: Page) {
  await page
    .getByRole("textbox", { name: "Assunto", exact: true })
    .fill("Origem do café");
  await page
    .getByRole("textbox", { name: /O que você quer/ })
    .fill("Explicar como comparar a origem do café.");
  await page
    .getByRole("textbox", { name: "Para quem?", exact: true })
    .fill("Pessoas que fazem café em casa");
  await page.getByRole("button", { name: "Explorar direções" }).click();
  await expect(
    page.getByRole("button", { name: "Escolher direção" }),
  ).toHaveCount(2);
}

test("request → direction → persisted delivery → review decision, with no technical editor", async ({
  page,
}) => {
  const state = await setup(page);
  await requestDirections(page);
  await expect(
    page.getByRole("button", { name: "Preparar primeira versão" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Escolher direção" }).first().click();
  await page.getByRole("button", { name: "Preparar primeira versão" }).click();
  await expect(
    page.getByAltText("Página 1 da entrega Origem do café"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Próxima página" }).click();
  await expect(
    page.getByAltText("Página 2 da entrega Origem do café"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Iniciar revisão" }).click();
  await expect(page.getByTestId("review-snapshot-image")).toBeVisible();
  await page
    .getByRole("textbox", { name: "Seu pedido de ajuste" })
    .fill("Dar mais contexto sobre a origem.");
  await expect(
    page.getByRole("button", { name: "Aprovar entrega" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Enviar pedido de ajuste" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Pedido de ajuste registrado" }),
  ).toBeVisible();
  expect(
    state.requests.find((r) => r.path.endsWith("/decisions"))?.body,
  ).toMatchObject({
    action: "request_changes",
    comment: "[Página 2] Dar mais contexto sobre a origem.",
  });
  expect(
    state.requests.filter((r) => r.path.includes("/ai-commands")),
  ).toHaveLength(0);
  await expect(page.getByText("Operação", { exact: true })).toHaveCount(0);
  await page.reload();
  await page.getByRole("button", { name: /Origem do café Carrossel/ }).click();
  await expect(
    page.getByRole("heading", { name: "Origem do café", exact: true }),
  ).toBeVisible();
});

test("runtime failure preserves the project and shows no fabricated preview", async ({
  page,
}) => {
  await setup(page, { failure: true });
  await requestDirections(page);
  await page.getByRole("button", { name: "Escolher direção" }).first().click();
  await page.getByRole("button", { name: "Preparar primeira versão" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "craft_engine_unavailable",
  );
  await expect(
    page.getByRole("button", { name: "Retomar preparação" }),
  ).toBeVisible();
  await expect(page.locator(".ds-media-stage img")).toHaveCount(0);
});

test("revision conflicts do not pretend a direction was saved", async ({
  page,
}) => {
  await setup(page, { conflict: true });
  await requestDirections(page);
  await page.getByRole("button", { name: "Escolher direção" }).first().click();
  await expect(page.getByRole("alert")).toContainText("outra sessão");
  await expect(
    page.getByRole("button", { name: "Preparar primeira versão" }),
  ).toBeDisabled();
});

test("ads and video are intent and format choices; video requires the brand's material", async ({
  page,
}) => {
  const state = await setup(page);
  await page.getByRole("button", { name: "Criação de anúncios" }).click();
  await page
    .getByRole("button", { name: "Vídeo Uma história em movimento" })
    .click();
  await expect(page.getByLabel("Intenção")).toHaveValue("offer");
  await expect(
    page.getByLabel("Material de origem", { exact: true }),
  ).toHaveAttribute("required", "");
  await expect(
    page.getByText(/A primeira montagem utiliza o vídeo selecionado/),
  ).toBeVisible();
  expect(
    state.requests.filter((r) => r.path.endsWith("/produce")),
  ).toHaveLength(0);
  await page.goto("/content/new?department&type=video");
  await expect(
    page.getByLabel("Material de origem", { exact: true }),
  ).toHaveAttribute("required", "");
  const context = page.getByRole("button", { name: "Ver contexto da marca" });
  await context.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(context).toBeFocused();
});

test("saved deliveries reopen, history uses server versions, and phone layout does not overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await setup(page, { saved: true });
  await expect(
    page.getByAltText("Página 1 da entrega Origem do café"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Versões · 2" }).click();
  await expect(page.getByText("Versão 2 · Primeira versão")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
