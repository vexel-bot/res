import { expect, test, type Page } from "@playwright/test";

const workspace = {
  id: "workspace-cast",
  name: "Marca de teste",
  brandProfile: {},
};
const identity = {
  profile: {
    id: "person",
    displayName: "Ana",
    identityType: "natural_person",
    status: "active",
  },
  versions: [{ id: "face-v1", version: 1, status: "active" }],
  selectedVersionId: "face-v1",
  previewAssetId: "photo",
  unavailableReason: null,
};
const voice = {
  profile: {
    id: "voice",
    displayName: "Voz Ana",
    voiceType: "cloned",
    status: "active",
  },
  versions: [{ id: "voice-v1", version: 1, status: "active" }],
  selectedVersionId: "voice-v1",
  previewAssetId: "audio",
  unavailableReason: null,
};

async function fixture(page: Page, failFirst = false) {
  let project: any;
  const enrollments: any[] = [],
    requests: any[] = [];
  let uploads = 0;
  await page.addInitScript(() =>
    localStorage.setItem("nexus_access_token", "interface-fixture"),
  );
  await page.route("**/api/**", async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname;
    if (path.endsWith("/bootstrap"))
      return route.fulfill({
        json: {
          user: { id: "user" },
          workspaces: [workspace],
          suggestions: [],
        },
      });
    if (path.endsWith("/identity-library"))
      return route.fulfill({
        json: {
          workspaceId: workspace.id,
          identities: [
            identity,
            {
              ...identity,
              profile: {
                ...identity.profile,
                id: "draft",
                displayName: "Em avaliação",
              },
              selectedVersionId: null,
              versions: [{ id: "draft-v1", version: 1, status: "draft" }],
              unavailableReason: "Avaliação pendente",
            },
          ],
          voices: [voice],
          consents: [],
        },
      });
    if (path.endsWith("/assets/upload")) {
      uploads++;
      return route.fulfill({ status: 201, json: { id: `upload-${uploads}` } });
    }
    if (path.endsWith("/enrollments")) {
      enrollments.push(request.postDataJSON());
      if (failFirst && enrollments.length === 1)
        return route.fulfill({
          status: 503,
          json: {
            detail: "Não foi possível confirmar o cadastro. Tente novamente.",
          },
        });
      return route.fulfill({
        status: 201,
        json: {
          status: "draft",
          identityProfileId: "new-person",
          voiceProfileId: "new-voice",
        },
      });
    }
    if (path.endsWith("/studios/v1/projects")) {
      if (request.method() === "GET")
        return route.fulfill({ json: project ? [project] : [] });
      const input = request.postDataJSON();
      requests.push(input);
      project = {
        ...input,
        id: "project-one",
        brandName: workspace.name,
        revision: 1,
        directionId: null,
        documentId: null,
        jobId: null,
        status: "direction",
        directions: [
          {
            id: "guide",
            title: input.title,
            opening: input.title,
            rationale: "Direção para a marca",
            beats: [input.objective],
            cta: "Conheça",
          },
        ],
      };
      return route.fulfill({ status: 201, json: project });
    }
    if (path.endsWith("/assets/catalog"))
      return route.fulfill({
        json: [
          {
            id: "source-video",
            title: "Vídeo da marca",
            mediaType: "video/mp4",
          },
        ],
      });
    if (path.endsWith("/capabilities"))
      return route.fulfill({ json: { capabilities: [] } });
    if (path.endsWith("/analytics/summary") || path.endsWith("/radar/state"))
      return route.fulfill({ json: {} });
    return route.fulfill({ json: [] });
  });
  return { enrollments, requests, uploads: () => uploads };
}

test("voice-only enrollment retries the same request without uploading or creating twice", async ({
  page,
}) => {
  const state = await fixture(page, true);
  await page.goto("/library/identities");
  await page.getByRole("button", { name: "Adicionar à biblioteca" }).click();
  await page.getByRole("button", { name: "Minha voz", exact: true }).click();
  await expect(page.getByLabel("Imagem de referência")).toHaveCount(0);
  await page.getByLabel("Nome", { exact: true }).fill("Minha voz autorizada");
  await page
    .getByLabel("Amostra de voz")
    .setInputFiles({
      name: "voice.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("fixture-audio"),
    });
  await page
    .getByLabel("Documento de autorização")
    .setInputFiles({
      name: "consent.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Autorização de uso para avaliação privada"),
    });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Salvar para avaliação" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Não foi possível confirmar",
  );
  await page.getByRole("button", { name: "Salvar para avaliação" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Cadastro salvo" }),
  ).toBeVisible();
  expect(state.enrollments).toHaveLength(2);
  expect(state.enrollments[1]).toEqual(state.enrollments[0]);
  expect(state.enrollments[0]).toMatchObject({
    mode: "voice",
    audioAssetId: "upload-2",
    evidenceAssetId: "upload-1",
  });
  expect(state.enrollments[0].imageAssetId).toBeUndefined();
  expect(state.uploads()).toBe(2);
});

for (const format of ["image", "video"])
  test(`independent appearance and voice choices are included in a ${format} request`, async ({
    page,
  }) => {
    const state = await fixture(page);
    await page.goto(
      `/studios?department&format=${format}&identityVersion=face-v1`,
    );
    await page
      .getByRole("textbox", { name: "Assunto", exact: true })
      .fill("Como escolher um café");
    await page
      .getByRole("textbox", { name: /O que você quer/ })
      .fill("Explicar os critérios de origem do café.");
    await page
      .getByRole("textbox", { name: "Para quem?", exact: true })
      .fill("Pessoas que fazem café em casa");
    await expect(page.getByLabel("Pessoa ou personagem")).toHaveValue(
      "face-v1",
    );
    await expect(
      page
        .getByLabel("Pessoa ou personagem")
        .getByRole("option", { name: "Em avaliação" }),
    ).toHaveCount(0);
    await page.getByLabel("Voz do projeto").selectOption("voice-v1");
    if (format === "video")
      await page.getByLabel("Material de origem").selectOption("source-video");
    else await expect(page.getByText(/imagens não contêm áudio/)).toBeVisible();
    await page.getByRole("button", { name: "Explorar direções" }).click();
    await expect(
      page.getByRole("button", { name: "Escolher direção" }),
    ).toBeVisible();
    expect(state.requests[0]).toMatchObject({
      format,
      identityVersionId: "face-v1",
      voiceVersionId: "voice-v1",
    });
  });

test("library separates draft and selectable identities and stays within a mobile viewport", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/library/identities");
  await expect(
    page.getByRole("heading", { name: "Quem dá vida às suas ideias." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Usar em imagem" }),
  ).toHaveCount(1);
  await expect(page.getByText("Em preparação", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Vozes/ }).click();
  await expect(page.getByRole("heading", { name: "Voz Ana" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Ouvir amostra" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 320, height: 800 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
