import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { STITCH_SCREENS } from "../../src/product/screenManifest";

function extractRgbCrop(
  videoPath: string,
  frame: number,
  x: number,
  y: number,
  width: number,
  height: number,
) {
  return execFileSync(
    "ffmpeg",
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      videoPath,
      "-vf",
      `select=eq(n\\,${frame}),crop=${width}:${height}:${x}:${y},format=rgb24`,
      "-frames:v",
      "1",
      "-f",
      "rawvideo",
      "pipe:1",
    ],
    { maxBuffer: width * height * 3 + 1024 },
  );
}

function countRgbPixels(
  pixels: Buffer,
  predicate: (red: number, green: number, blue: number) => boolean,
) {
  let count = 0;
  for (let index = 0; index < pixels.length; index += 3) {
    if (predicate(pixels[index], pixels[index + 1], pixels[index + 2])) count += 1;
  }
  return count;
}

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
  "/content/post-ritual/edit?mode=video",
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

test("controles nativos e compartilhados emitem um único Action Contract", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const events: Array<{ actionId?: string; event: string }> = [];
    (window as unknown as { __clickoExperienceEvents: typeof events }).__clickoExperienceEvents = events;
    window.addEventListener("clicko:experience", (event) => {
      events.push((event as CustomEvent).detail);
    });
  });
  await page.goto("/dashboard");
  await page.getByRole("button", { name: /Ver radar completo/ }).click();
  await expect(page).toHaveURL(/\/radar$/);
  const nativeEvents = await page.evaluate(() =>
    (
      window as unknown as {
        __clickoExperienceEvents: Array<{ actionId?: string; event: string }>;
      }
    ).__clickoExperienceEvents
      .filter((event) => event.actionId === "HOME-OPEN-RADAR")
      .map(({ actionId, event }) => ({ actionId, event })),
  );
  expect(nativeEvents).toEqual([
    { actionId: "HOME-OPEN-RADAR", event: "home.radar_opened" },
  ]);

  await navigateSpa(page, "/content/post-ritual/edit?mode=carousel");
  await page.getByRole("button", { name: "Visualizar conjunto" }).click();
  const sharedEvents = await page.evaluate(() =>
    (
      window as unknown as {
        __clickoExperienceEvents: Array<{ actionId?: string; event: string }>;
      }
    ).__clickoExperienceEvents.filter(
      (event) => event.actionId === "CAROUSEL-VISUALIZE-SET",
    ),
  );
  expect(sharedEvents).toHaveLength(1);
  expect(sharedEvents[0].event).toBe("carousel.set_previewed");
});

test("jornada criativa vai de projeto a revisão e preflight", async ({
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
  await expect(page).toHaveURL(/\/publish\/post-ritual$/);
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
  await page.addInitScript(() => {
    const events: Array<{ actionId?: string; event: string }> = [];
    (window as unknown as { __clickoExperienceEvents: typeof events }).__clickoExperienceEvents = events;
    window.addEventListener("clicko:experience", (event) => {
      events.push((event as CustomEvent).detail);
    });
  });
  await page.goto("/content");
  await expect(
    page.getByRole("heading", { name: "Criar e organizar conteúdo" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Retomar/ }).click();
  await expect(page).toHaveURL(/mode=carousel/);
  await expect(page.locator(".cx-carousel-approved")).toBeVisible();
  await page.getByRole("button", { name: "Adicionar slide" }).click();
  await expect(page.getByText("7 slides · 48s de leitura")).toBeVisible();
  await page.getByRole("button", { name: "Visualizar conjunto" }).click();
  const carouselPreview = page.getByRole("dialog", { name: "Carrossel completo" });
  await expect(carouselPreview).toBeVisible();
  const previewEventCaptured = await page.evaluate(() =>
    (
      window as unknown as {
        __clickoExperienceEvents: Array<{ actionId?: string; event: string }>;
      }
    ).__clickoExperienceEvents.some(
      (event) =>
        event.actionId === "CAROUSEL-VISUALIZE-SET" &&
        event.event === "carousel.set_previewed",
    ),
  );
  expect(previewEventCaptured).toBeTruthy();
  await expect(carouselPreview.getByRole("button")).toHaveCount(8);
  await carouselPreview
    .getByRole("button", { name: "Fechar preview do carrossel" })
    .click();
  await expect(carouselPreview).toBeHidden();

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
  await expect(page).toHaveURL(/\/factory\/round-demo$/);
  await expect(
    page.getByText("Rodada persistida com documentos, versões e jobs rastreáveis."),
  ).toBeVisible();
});

test("Motion Inspector é contextual, reversível e respeita movimento reduzido", async ({
  page,
}) => {
  await page.goto("/content/post-ritual/edit?mode=visual&tool=motion");
  await expect(page.getByTestId("motion-inspector")).toBeVisible();
  await expect(page.getByText("Motion Inspector", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Ênfase" }).click();
  await page.getByLabel("Duração do movimento em frames").fill("72");
  await page.getByLabel("Respeitar movimento reduzido").check();
  await page.getByRole("button", { name: /Pré-visualizar localmente/ }).click();
  await expect(page.getByText(/preferência de movimento reduzido respeitada/)).toBeVisible();
  await page.getByRole("button", { name: "Salvar sugestão" }).click();
  await expect(page.getByText(/Sugestão demonstrativa criada/)).toBeVisible();
  await expect(page.locator(".cx-motion-record")).toContainText("SUGESTÃO");
  await page.getByRole("button", { name: "Revisar e aplicar" }).click();
  await expect(page.locator(".cx-motion-record")).toContainText("APLICADO");
});

test("Image Lab autenticado cria derivação privada e preserva o retorno", async ({
  page,
  request,
}) => {
  test.setTimeout(60_000);
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const registration = await request.post("/api/v1/auth/register", {
    data: {
      email: `image-lab-e2e-${suffix}@example.com`,
      name: "Image Lab E2E",
      password: "senha-image-lab-e2e-123",
      workspaceName: `Image Lab ${suffix}`,
    },
  });
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const bootstrap = await request.get("/api/v1/bootstrap", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const workspaceId = (await bootstrap.json()).workspaces[0].id;
  const directory = mkdtempSync(join(tmpdir(), "clicko-image-lab-"));
  const imagePath = join(directory, "source.png");
  try {
    execFileSync("ffmpeg", [
      "-hide_banner",
      "-loglevel",
      "error",
      "-f",
      "lavfi",
      "-i",
      "color=c=0x506478:s=320x400:d=0.1",
      "-frames:v",
      "1",
      imagePath,
    ]);
    const upload = await request.post("/api/v1/assets/upload", {
      headers: { Authorization: `Bearer ${accessToken}` },
      multipart: {
        workspace_id: workspaceId,
        title: "Produto protegido",
        tags: "image-lab,e2e",
        file: {
          name: "source.png",
          mimeType: "image/png",
          buffer: readFileSync(imagePath),
        },
      },
    });
    expect(upload.status()).toBe(201);
    const source = await upload.json();
    await page.addInitScript(
      ({ token }) => localStorage.setItem("nexus_access_token", token),
      { token: accessToken },
    );
    await page.goto(
      `/library/assets/${source.id}/edit?mode=image&returnTo=${encodeURIComponent("/content/post-ritual/edit?mode=visual")}`,
    );
    await expect(page.getByRole("heading", { name: "Produto protegido" })).toBeVisible();
    await expect(page.getByText("ORIGINAL IMUTÁVEL")).toBeVisible();
    await page.getByLabel(/Brilho/).fill("1.25");
    await page.getByLabel("Limitar ajuste a uma região").check();
    await page.getByRole("button", { name: "Criar derivação privada" }).click();
    await expect(page.getByText("Derivação pronta para revisão")).toBeVisible();
    const listed = await request.get("/api/v1/assets", {
      headers: { Authorization: `Bearer ${accessToken}` },
      params: { workspace_id: workspaceId },
    });
    const assets = await listed.json();
    const derivative = assets.find((item: any) => item.metadata?.sourceAssetId === source.id);
    expect(derivative).toBeTruthy();
    expect(derivative.checksumSha256).not.toBe(source.checksumSha256);
    expect(derivative.metadata.reviewRequired).toBe("true");
    await page.getByRole("button", { name: "Voltar com derivação" }).click();
    await expect(page).toHaveURL(
      new RegExp(`/content/post-ritual/edit\\?mode=visual&derivedAsset=${derivative.id}`),
    );
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("Motion e Image Lab mantêm tarefa e scroll no viewport móvel", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/content/post-ritual/edit?mode=visual&tool=motion");
  await expect(page.getByTestId("motion-inspector")).toBeVisible();
  await page.getByRole("button", { name: "Sutil", exact: true }).click();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
    )
    .toBeTruthy();

  await navigateSpa(
    page,
    "/library/assets/demo-0/edit?mode=image&returnTo=%2Flibrary%2Fassets",
  );
  await expect(page.getByRole("heading", { name: "Imagem demonstrativa" })).toBeVisible();
  await page.getByLabel("Limitar ajuste a uma região").check();
  await page.getByTestId("image-compare").fill("35");
  await page.getByRole("button", { name: "Criar derivação privada" }).click();
  await expect(page.getByText("Derivação pronta para revisão")).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
    )
    .toBeTruthy();
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
  await page.getByRole("button", { name: "Gerar derivações" }).click();
  await expect(page.getByText("3 derivações criadas com lineage")).toBeVisible();

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
  await page.getByRole("button", { name: "Gerar demonstração local" }).click();
  await expect(page.getByText("TESTES 1/3")).toBeVisible();
  await page.getByRole("button", { name: "Abrir captura" }).click();
  await expect(page.getByRole("button", { name: "Capturado" })).toBeVisible();
  await page.getByRole("button", { name: "Sim", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sim", exact: true }),
  ).toHaveClass(/is-active/);
});

test("Presenter autenticado expõe readiness e bloqueia identidade sem provider aprovado", async ({
  page,
  request,
}) => {
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const registration = await request.post("/api/v1/auth/register", {
    data: {
      email: `presenter-gate-${suffix}@example.com`,
      name: "Presenter Gate",
      password: "senha-presenter-gate-123",
      workspaceName: `Presenter Gate ${suffix}`,
    },
  });
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const headers = { Authorization: `Bearer ${accessToken}` };
  const bootstrap = await request.get("/api/v1/bootstrap", { headers });
  expect(bootstrap.status()).toBe(200);
  const workspaceId = (await bootstrap.json()).workspaces[0].id;
  const capabilitiesResponse = await request.get(
    "/api/v1/studios/v1/capabilities",
    { headers, params: { workspace_id: workspaceId } },
  );
  expect(capabilitiesResponse.status()).toBe(200);
  const presenter = (await capabilitiesResponse.json()).capabilities.find(
    (item: { capability: string }) => item.capability === "presenter",
  );
  expect(presenter).toMatchObject({
    providerReady: false,
    captureReady: false,
    publicationAllowed: false,
  });

  await page.addInitScript(
    ({ token }) => localStorage.setItem("nexus_access_token", token),
    { token: accessToken },
  );
  await page.goto("/content/post-ritual/edit?mode=presenter");
  await expect(
    page.getByRole("heading", { name: "Mariana × Café Aurora" }),
  ).toBeVisible();
  await expect(page.getByText("PRÉVIA SEM PROVIDER")).toBeVisible();
  await expect(
    page.getByText(
      "interface preparada; provider, consentimento e benchmark ainda não estão ativos.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Direitos ou provider pendentes" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Abrir captura governada" }),
  ).toHaveAttribute("data-action-id", "PRESENTER-OPEN-IDENTITIES");
  await expect(
    page.getByText("Nenhum teste gerado · provider pendente"),
  ).toBeVisible();
});

test("Identity Library separa seis avatares stock da captura consentida", async ({
  page,
}) => {
  await page.goto("/library/identities");
  await expect(
    page.getByRole("heading", { name: "Escolha presença sem perder o controle" }),
  ).toBeVisible();
  await expect(page.locator(".cx-stock-avatar-grid article")).toHaveCount(6);
  await expect(page.getByRole("button", { name: "Ver prévia local" })).toHaveCount(6);
  await page.getByRole("button", { name: "Ver prévia local" }).first().click();
  await expect(page).toHaveURL(/mode=presenter&avatar=lia&preview=1/);
  await expect(page.getByRole("heading", { name: "Lia × Café Aurora" })).toBeVisible();
  await page.getByRole("button", { name: "Identidades" }).click();
  await page.getByRole("button", { name: "Cadastrar identidade própria" }).click();
  await expect(page.getByText("Candidato privado, nunca ativação automática")).toBeVisible();
  await expect(page.getByText(/não é publicado/)).toBeVisible();
});

test("Identity Library cria rascunho consentido e revogação bloqueia uso futuro", async ({
  page,
  request,
}) => {
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const registration = await request.post("/api/v1/auth/register", {
    data: {
      email: `identity-library-${suffix}@example.com`,
      name: "Identity Owner",
      password: "senha-identity-123",
      workspaceName: `Identity Library ${suffix}`,
    },
  });
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const headers = { Authorization: `Bearer ${accessToken}` };
  const bootstrap = await request.get("/api/v1/bootstrap", { headers });
  const workspaceId = (await bootstrap.json()).workspaces[0].id;
  await page.addInitScript(
    ({ token }) => localStorage.setItem("nexus_access_token", token),
    { token: accessToken },
  );
  await page.goto("/library/identities");
  await expect(page.getByRole("button", { name: "Ativação pendente" })).toHaveCount(6);
  await page.getByRole("button", { name: "Cadastrar identidade própria" }).click();
  await page.getByLabel("Nome da pessoa").fill("Ana Consentida");
  await page.locator("#identity-purpose").fill("Amostras privadas da campanha de agosto");
  const expiry = new Date();
  expiry.setDate(expiry.getDate() + 30);
  await page.getByLabel("Válido até").fill(expiry.toISOString().slice(0, 10));
  const privateCapture = execFileSync(
    "ffmpeg",
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-f",
      "lavfi",
      "-i",
      "color=c=0x201a36:s=160x284:r=12",
      "-t",
      "0.5",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "frag_keyframe+empty_moov",
      "-f",
      "mp4",
      "pipe:1",
    ],
    { maxBuffer: 2 * 1024 * 1024 },
  );
  await page.getByLabel("Vídeo privado de consentimento e captura").setInputFiles({
    name: "consent-capture.mp4",
    mimeType: "video/mp4",
    buffer: privateCapture,
  });
  const privateVoice = execFileSync(
    "ffmpeg",
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-f",
      "lavfi",
      "-i",
      "sine=frequency=330:sample_rate=24000",
      "-t",
      "0.5",
      "-c:a",
      "pcm_s16le",
      "-f",
      "wav",
      "pipe:1",
    ],
    { maxBuffer: 2 * 1024 * 1024 },
  );
  await page.getByLabel("Áudio privado para matrícula de voz").setInputFiles({
    name: "voice-enrollment.wav",
    mimeType: "audio/wav",
    buffer: privateVoice,
  });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Criar candidato para revisão" }).click();
  await expect(page.getByText(/Candidato privado criado/)).toBeVisible();
  await expect(page.getByText("Ana Consentida", { exact: true })).toBeVisible();
  await expect(page.getByText(/Consentimento: active/)).toBeVisible();

  const identities = await request.get("/api/v1/studios/v1/identities", {
    headers,
    params: { workspace_id: workspaceId },
  });
  expect(identities.status()).toBe(200);
  expect((await identities.json())[0]).toMatchObject({
    displayName: "Ana Consentida",
    status: "draft",
  });
  const consents = await request.get("/api/v1/studios/v1/consents", {
    headers,
    params: { workspace_id: workspaceId },
  });
  expect(consents.status()).toBe(200);
  expect((await consents.json())[0]).toMatchObject({
    status: "active",
    scopes: ["identity.enroll", "avatar.generate", "voice.enroll", "voice.clone"],
  });
  const voices = await request.get("/api/v1/studios/v1/voices", {
    headers,
    params: { workspace_id: workspaceId },
  });
  expect(voices.status()).toBe(200);
  expect((await voices.json())[0]).toMatchObject({
    displayName: "Ana Consentida · PT-BR",
    status: "draft",
    voiceType: "cloned",
  });

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Revogar consentimento" }).click();
  await expect(page.getByText(/Consentimento: revoked/)).toBeVisible();
  const revoked = await request.get("/api/v1/studios/v1/consents", {
    headers,
    params: { workspace_id: workspaceId },
  });
  expect((await revoked.json())[0].status).toBe("revoked");
});

test("Post Factory passa por direção antes do Editorial e preserva o handoff", async ({
  page,
}) => {
  await page.goto("/content/new?type=post");
  await expect(page.locator('[data-screen-id="SCREEN-CREATE-HUB"]')).toHaveAttribute(
    "data-shell",
    "decision",
  );

  await page.locator('[data-action-id="CREATE-START-DIRECTION"]').first().click();
  await expect(page).toHaveURL(/\/campaigns\/new\?intent=content&mode=editorial&type=post/);
  await expect(page.locator('[data-screen-id="SCREEN-DIRECTION"]')).toHaveAttribute(
    "data-shell",
    "decision",
  );
  await expect(page.locator('[data-action-id="DIRECTION-APPROVE"]')).toBeVisible();

  await page.getByRole("button", { name: /Aprovar direção e abrir Editorial/ }).click();
  await expect(page).toHaveURL(/\/content\/draft\/edit\?mode=editorial&campaign=/);
  await expect(page.locator('[data-screen-id="SCREEN-EDITORIAL"]')).toHaveAttribute(
    "data-shell",
    "studio",
  );
  await expect(page.locator(".cx-editorial-approved")).toBeVisible();
});

test("Reuse autenticado cria lineage e inicia uma rodada persistente com jobs idempotentes", async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const registration = await request.post("/api/v1/auth/register", {
    data: {
      email: `reuse-factory-${suffix}@example.com`,
      name: "Reuse Factory E2E",
      password: "senha-reuse-factory-123",
      workspaceName: `Reuse Factory ${suffix}`,
    },
  });
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const headers = { Authorization: `Bearer ${accessToken}` };
  const bootstrap = await request.get("/api/v1/bootstrap", { headers });
  const workspaceId = (await bootstrap.json()).workspaces[0].id;
  const createdPost = await request.post("/api/v1/posts", {
    headers,
    data: {
      workspaceId,
      title: "Vencedor rastreável",
      platform: "instagram",
      format: "post",
      copy: "Uma promessa que merece novas formas.",
      status: "published",
      author: "Reuse Factory E2E",
      objective: "Validar a linhagem da produção",
      origin: "manual",
    },
  });
  expect(createdPost.status()).toBe(201);
  const sourcePostId = (await createdPost.json()).id;

  await page.addInitScript(
    ({ token }) => localStorage.setItem("nexus_access_token", token),
    { token: accessToken },
  );
  await page.goto(`/content/${sourcePostId}/remix`);
  await expect(
    page.getByRole("heading", { name: "Transforme o que funcionou em uma nova peça" }),
  ).toBeVisible();
  await expect(page.getByText("Sem campanha vinculada").first()).toBeVisible();
  await expect(page.getByText("Sem dado observado").first()).toBeVisible();
  await expect(page.getByText("3× mais salvamentos que a média da campanha")).toHaveCount(0);
  await page.locator('[data-action-id="REUSE-GENERATE-DERIVATIONS"]').click();
  await expect(page.getByText("3 derivações criadas com lineage")).toBeVisible();

  const postsResponse = await request.get("/api/v1/posts", {
    headers,
    params: { workspace_id: workspaceId },
  });
  expect(postsResponse.status()).toBe(200);
  const posts = await postsResponse.json();
  const derivatives = posts.filter(
    (post: { versions?: Array<{ lineage?: { sourcePostId?: string } }> }) =>
      post.versions?.[0]?.lineage?.sourcePostId === sourcePostId,
  );
  expect(derivatives).toHaveLength(3);
  expect(derivatives.every((post: { metrics?: object }) => Object.keys(post.metrics || {}).length === 0)).toBeTruthy();
  expect(
    derivatives.map(
      (post: { versions?: Array<{ lineage?: { derivationKey?: string } }> }) =>
        post.versions?.[0]?.lineage?.derivationKey,
    ).sort(),
  ).toEqual(["post", "square", "story"]);

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Transforme o que funcionou em uma nova peça" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Derivações salvas" })).toBeDisabled();
  await expect(page.getByRole("button", { name: /Abrir derivado no editor/ })).toHaveCount(3);
  await expect(page.locator('[data-action-id="REUSE-SEND-FACTORY"]')).toBeEnabled();

  await page.locator('[data-action-id="REUSE-SEND-FACTORY"]').click();
  await expect(page).toHaveURL(/\/factory\?source=/);
  await expect(page.getByText("Vencedor rastreável").first()).toBeVisible();
  await expect(page.getByText("COERÊNCIA 92%")).toHaveCount(0);
  await expect(page.getByText(/5 peças prontas hoje/)).toHaveCount(0);
  const factoryIntakeUrl = page.url();
  await page.locator('[data-action-id="FACTORY-START-ROUND"]').click();
  await expect(page).toHaveURL(/\/factory\/round-/);
  await expect(
    page.getByText("Rodada persistida com documentos, versões e jobs rastreáveis."),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "3 decisões antes da saída" })).toBeVisible();

  const roundsResponse = await request.get("/api/v1/workspace-resources", {
    headers,
    params: { workspace_id: workspaceId, kind: "factory_round" },
  });
  expect(roundsResponse.status()).toBe(200);
  const rounds = await roundsResponse.json();
  expect(rounds).toHaveLength(1);
  expect(rounds[0].payload.cells).toHaveLength(3);
  expect(
    rounds[0].payload.cells.every(
      (cell: { documentId?: string; versionNumber?: number; jobId?: string }) =>
        cell.documentId && cell.versionNumber && cell.jobId,
    ),
  ).toBeTruthy();

  const roundId = rounds[0].resourceKey;
  const firstCells = rounds[0].payload.cells as Array<{
    documentId: string;
    versionNumber: number;
    jobId: string;
  }>;
  const versionsBefore = new Map<string, number>();
  for (const cell of firstCells) {
    const documentResponse = await request.get(
      `/api/v1/studios/v1/documents/${cell.documentId}`,
      { headers },
    );
    expect(documentResponse.status()).toBe(200);
    versionsBefore.set(cell.documentId, (await documentResponse.json()).version);
  }
  const jobsBeforeResponse = await request.get("/api/v1/studios/v1/jobs", {
    headers,
    params: {
      workspace_id: workspaceId,
      job_type: "document_snapshot",
      limit: 100,
    },
  });
  expect(jobsBeforeResponse.status()).toBe(200);
  const jobIdsBefore = (await jobsBeforeResponse.json())
    .map((job: { id: string }) => job.id)
    .sort();

  await page.goto(factoryIntakeUrl);
  await expect(page.locator('[data-action-id="FACTORY-START-ROUND"]')).toBeEnabled();
  await page.locator('[data-action-id="FACTORY-START-ROUND"]').click();
  await expect(page).toHaveURL(new RegExp(`/factory/${roundId}$`));
  await expect(
    page.getByText("Rodada existente recuperada sem duplicar versões ou jobs"),
  ).toBeVisible();

  const roundsAfterResponse = await request.get("/api/v1/workspace-resources", {
    headers,
    params: { workspace_id: workspaceId, kind: "factory_round" },
  });
  expect(roundsAfterResponse.status()).toBe(200);
  const roundsAfter = await roundsAfterResponse.json();
  expect(roundsAfter).toHaveLength(1);
  expect(roundsAfter[0].resourceKey).toBe(roundId);
  expect(
    roundsAfter[0].payload.cells.map((cell: { jobId: string }) => cell.jobId),
  ).toEqual(firstCells.map((cell) => cell.jobId));

  for (const cell of firstCells) {
    const documentResponse = await request.get(
      `/api/v1/studios/v1/documents/${cell.documentId}`,
      { headers },
    );
    expect(documentResponse.status()).toBe(200);
    expect((await documentResponse.json()).version).toBe(
      versionsBefore.get(cell.documentId),
    );
  }
  const jobsAfterResponse = await request.get("/api/v1/studios/v1/jobs", {
    headers,
    params: {
      workspace_id: workspaceId,
      job_type: "document_snapshot",
      limit: 100,
    },
  });
  expect(jobsAfterResponse.status()).toBe(200);
  expect(
    (await jobsAfterResponse.json())
      .map((job: { id: string }) => job.id)
      .sort(),
  ).toEqual(jobIdsBefore);
});

test("shell de produção permanece rolável no viewport móvel", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  // The visual surface contains optional media; assert the application shell
  // after DOM readiness instead of waiting on third-party image load events.
  await page.goto("/content/post-ritual/edit?mode=visual", {
    waitUntil: "domcontentloaded",
  });

  const shell = page.locator('[data-screen-id="SCREEN-VISUAL"]');
  await expect(shell).toHaveAttribute("data-shell", "studio");
  const main = page.locator("#cx-main");
  await expect(main).toBeVisible();
  const metrics = await main.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      overflowY: style.overflowY,
      scrollHeight: element.scrollHeight,
      clientHeight: element.clientHeight,
    };
  });
  expect(metrics.overflowY).toBe("auto");
  expect(metrics.scrollHeight).toBeGreaterThanOrEqual(metrics.clientHeight);
  await expect(page.getByRole("button", { name: "Enviar para revisão", exact: true })).toBeVisible();
});

test("Reuse e Fábrica mantêm rolagem e ação principal no viewport móvel", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const surface of [
    {
      path: "/content/post-ritual/remix",
      screenId: "SCREEN-REUSE",
      actionId: "REUSE-GENERATE-DERIVATIONS",
    },
    {
      path: "/factory",
      screenId: "SCREEN-FACTORY",
      actionId: "FACTORY-START-ROUND",
    },
  ]) {
    await page.goto(surface.path, { waitUntil: "domcontentloaded" });
    await expect(page.locator(`[data-screen-id="${surface.screenId}"]`)).toBeVisible();
    const scrollState = await page.evaluate(() => {
      const main = document.querySelector<HTMLElement>("#cx-main");
      if (!main) throw new Error("Área principal ausente");
      const overflowY = getComputedStyle(main).overflowY;
      const element = ["auto", "scroll"].includes(overflowY)
        ? main
        : document.scrollingElement;
      if (!element) throw new Error("Contêiner de rolagem ausente");
      element.scrollTop = element.scrollHeight;
      return {
        overflowY,
        scrollTop: element.scrollTop,
        scrollHeight: element.scrollHeight,
        clientHeight: element.clientHeight,
      };
    });
    expect(["auto", "visible"]).toContain(scrollState.overflowY);
    expect(scrollState.scrollHeight).toBeGreaterThan(scrollState.clientHeight);
    expect(scrollState.scrollTop).toBeGreaterThan(0);
    const primaryAction = page.locator(`[data-action-id="${surface.actionId}"]`).first();
    await primaryAction.scrollIntoViewIfNeeded();
    await expect(primaryAction).toBeVisible();
  }
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
  await expect(page.getByText("MOTOR CLICKO · PRÉ-FLIGHT")).toBeVisible();
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
  // The guest surface is explicitly a local, non-publishable demonstration;
  // never regress to presenting synthetic identity output as approved production.
  await expect(
    page.getByText(/VIDEO STUDIO.*FACTORY CELL.*DEMONSTRAÇÃO LOCAL/),
  ).toBeVisible();
  await expect(
    page.getByText("pronta para gerar exemplos locais, não para publicar."),
  ).toBeVisible();
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

test("Video Studio monta o laboratório UGC e mantém cortes não destrutivos honestos", async ({
  page,
}) => {
  await page.goto("/content/draft/edit?mode=video");
  await expect(page.locator(".vs-shell")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Novo vídeo UGC" }),
  ).toBeVisible();
  await expect(page.getByText("Modo demonstração · sem persistência")).toBeVisible();
  await expect(page.getByText("OpenCut como referência de UX")).toBeVisible();
  await expect(page.getByText("CreativeDocument como fonte de verdade")).toBeVisible();
  await page.evaluate(() => {
    (window as any).__videoExperienceEvents = [];
    window.addEventListener("clicko:experience", (event) => {
      (window as any).__videoExperienceEvents.push((event as CustomEvent).detail);
    });
  });
  await page.getByRole("button", { name: "Cortes" }).click();
  await page.getByRole("button", { name: "Aplicar corte" }).click();
  await expect(
    page.getByText("Corte demonstrativo aplicado sem alterar o original."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Saída" }).click();
  await expect(page.getByText("builtin.ffmpeg-ugc-v1", { exact: true })).toBeVisible();
  await expect(page.getByText("media_cpu", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Renderizar prova privada" }).click();
  const actionIds = await page.evaluate(() =>
    (window as any).__videoExperienceEvents.map((event: any) => event.actionId),
  );
  expect(actionIds).toEqual(
    expect.arrayContaining(["VIDEO-APPLY-CUT", "VIDEO-RENDER-PREVIEW"]),
  );
  await expect(page.locator("iframe")).toHaveCount(0);
  const widths = await page.locator(".cx-product").evaluate((element) => ({
    client: element.clientWidth,
    scroll: element.scrollWidth,
  }));
  expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("button", { name: "Importar outro arquivo" })).toBeVisible();
  const mobileWidths = await page.locator(".vs-shell").evaluate((element) => ({
    client: element.clientWidth,
    scroll: element.scrollWidth,
  }));
  expect(mobileWidths.scroll).toBeLessThanOrEqual(mobileWidths.client + 1);
});

test("Video Studio autenticado leva um MP4 real do upload à revisão versionada", async ({
  page,
  request,
}) => {
  test.setTimeout(180_000);
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const registration = await request.post("/api/v1/auth/register", {
    data: {
      email: `ugc-e2e-${suffix}@example.com`,
      name: "UGC E2E",
      password: "senha-ugc-e2e-123",
      workspaceName: `UGC E2E ${suffix}`,
    },
  });
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const headers = { Authorization: `Bearer ${accessToken}` };
  const bootstrap = await request.get("/api/v1/bootstrap", { headers });
  const workspaceId = (await bootstrap.json()).workspaces[0].id;
  const createdPost = await request.post("/api/v1/posts", {
    headers,
    data: {
      workspaceId,
      title: "UGC real auditável",
      platform: "Instagram",
      format: "video",
      copy: "Take real para validar a cadeia assistida.",
      status: "draft",
      author: "UGC E2E",
      objective: "Validar o Video Studio autenticado",
      origin: "manual",
    },
  });
  expect(createdPost.status()).toBe(201);
  const postId = (await createdPost.json()).id;
  const fixtureDirectory = mkdtempSync(join(tmpdir(), "clicko-ugc-e2e-"));
  // Observe the real Web Audio output without replacing the renderer or sources.
  await page.addInitScript(() => {
    const originalConnect = AudioNode.prototype.connect;
    (window as any).__soundTaps = [];
    (AudioNode.prototype as any).connect = function (...args: any[]) {
      const connected = (originalConnect as any).apply(this, args);
      if (args[0] === this.context.destination && this instanceof GainNode) {
        const tap = this.context.createAnalyser();
        tap.fftSize = 1024;
        (originalConnect as any).call(this, tap);
        (window as any).__soundTaps.push(tap);
      }
      return connected;
    };
    (window as any).__soundRms = () => Math.max(0, ...(window as any).__soundTaps.map((tap: AnalyserNode) => {
      const pcm = new Float32Array(tap.fftSize);
      tap.getFloatTimeDomainData(pcm);
      return Math.sqrt(pcm.reduce((sum, value) => sum + value * value, 0) / pcm.length);
    }));
    let sampling = false;
    (window as any).__observePreviewSound = () => {
      (window as any).__soundPeak = 0;
      (window as any).__soundSamples = [];
      if (sampling) return;
      sampling = true;
      const sample = () => {
        const rms = (window as any).__soundRms();
        const input = document.querySelector<HTMLInputElement>('[aria-label="Posição do vídeo"]');
        (window as any).__soundPeak = Math.max((window as any).__soundPeak, rms);
        (window as any).__soundSamples.push({ time: Number(input?.value ?? 0), rms });
        requestAnimationFrame(sample);
      };
      requestAnimationFrame(sample);
    };
  });
  const fixturePath = join(fixtureDirectory, "ugc-real.mp4");
  execFileSync(
    "ffmpeg",
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-y",
      "-f",
      "lavfi",
      "-i",
      "color=c=0x201a36:s=360x640:r=30",
      "-f",
      "lavfi",
      "-i",
      "sine=frequency=440:sample_rate=48000",
      "-t",
      "2",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-c:a",
      "aac",
      "-shortest",
      fixturePath,
    ],
    { stdio: "ignore" },
  );

  try {
    await page.addInitScript(
      ({ token }) => localStorage.setItem("nexus_access_token", token),
      { token: accessToken },
    );
    await page.goto(`/content/${postId}/edit?mode=video`);
    await expect(page.locator(".cx-demo-banner")).toHaveCount(0);
    await expect(page.getByRole("button", { name: /Adicionar take/ })).toBeEnabled({
      timeout: 30_000,
    });
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: /Adicionar take/ }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: "ugc-real.mp4",
      mimeType: "video/mp4",
      buffer: readFileSync(fixturePath),
    });
    await expect(page.getByText("Mídia validada e projeto UGC criado.")).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator(".vs-pipeline-card p").nth(1)).toContainText(
      "Mídia pronta",
    );
    await expect(page.locator(".vs-pipeline-card p").nth(4)).toContainText("r1");

    await page.getByRole("button", { name: "Criar proxy de edição" }).click();
    await expect(page.locator(".vs-pipeline-card p").nth(2)).toContainText(
      "validado",
      { timeout: 60_000 },
    );
    await page.getByRole("button", { name: "Gerar forma de onda" }).click();
    await expect(page.locator(".vs-pipeline-card p").nth(3)).toContainText(
      "extraída",
      { timeout: 60_000 },
    );
    await expect(page.locator(".vs-waveform-bars i").first()).toBeVisible();

    const editorialCaptionText =
      "Pare de perder tempo no começo do dia.\nVeja o ritual funcionando em poucos passos.\nComece hoje com a experiência da marca.";
    await page.getByLabel("Texto editorial das legendas").fill(editorialCaptionText);
    await page.getByRole("button", { name: "Aplicar na timeline" }).click();
    await expect(
      page.getByText("Legendas editoriais salvas na timeline."),
    ).toBeVisible();
    await page.getByRole("button", { name: "Cortes" }).click();
    await page.getByLabel("Início (s)").fill("0.4");
    await page.getByLabel("Fim (s)").fill("0.8");
    await page.getByRole("button", { name: "Aplicar corte" }).click();
    await expect(
      page.getByText("Corte aplicado e timeline recomposta frame a frame."),
    ).toBeVisible();
    await expect(page.getByText("TAKE 02", { exact: true })).toBeVisible();

    const secondTake = page.locator(".vs-video-clip").nth(1);
    await secondTake.press("Alt+ArrowLeft");
    await expect(
      page.getByText("Take movido um passo para a esquerda."),
    ).toBeVisible();
    const firstTake = page.locator(".vs-video-clip").first();
    const beforeTrim = Number(await firstTake.getAttribute("data-duration-frames"));
    await firstTake.locator(".vs-trim-handle.is-end").press("ArrowLeft");
    await expect(firstTake).toHaveAttribute(
      "data-duration-frames",
      String(beforeTrim - 1),
    );

    await page.getByRole("button", { name: "Legendas" }).click();
    const persistedEditorialCaptionText = await page
      .getByLabel("Texto editorial das legendas")
      .inputValue();
    expect(persistedEditorialCaptionText.split("\n").sort()).toEqual(
      editorialCaptionText.split("\n").sort(),
    );
    await page.getByRole("button", { name: "Saída" }).click();
    await page.getByRole("button", { name: "Renderizar prova privada" }).click();
    await expect(page.getByText("Prova privada vinculável")).toBeVisible({
      timeout: 90_000,
    });
    await expect(page.getByText("QC técnico aprovado · escuta pendente")).toBeVisible();
    await expect(page.locator(".vs-job-card")).toContainText("Concluído");
    await expect(page.getByRole("button", { name: "Enviar para revisão" })).toBeEnabled();

    await page.reload();
    await expect(page.getByLabel("Texto editorial das legendas")).toHaveValue(
      persistedEditorialCaptionText,
      { timeout: 30_000 },
    );
    await page.getByRole("button", { name: "Saída" }).click();
    await expect(page.locator(".vs-job-card")).toContainText("Concluído", {
      timeout: 30_000,
    });
    await expect(page.getByText("Prova privada vinculável")).toBeVisible();
    await expect(page.getByRole("button", { name: "Enviar para revisão" })).toBeEnabled();

    await page.getByRole("button", { name: "Enviar para revisão" }).click();
    await expect(page).toHaveURL(new RegExp(`/approvals/${postId}\\?view=creative`));
    await expect(
      page.getByText("Versão exata enviada para revisão humana."),
    ).toBeVisible();
    const reviewResponse = await request.get(
      "/api/v1/studios/v1/reviews/latest",
      {
        headers,
        params: { workspace_id: workspaceId, post_id: postId },
      },
    );
    expect(reviewResponse.status()).toBe(200);
    const review = await reviewResponse.json();
    expect(review.status).toBe("requested");
    expect(review.renderJobId).toBeTruthy();
    expect(review.renderAssetId).toBeTruthy();
    expect(review.renderChecksumSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(review.snapshot.contentType).toBe("video");
    expect(review.snapshot.assets).toHaveLength(1);
    const tracks = review.snapshot.composition.mediaTimeline.tracks;
    expect(tracks.find((track: any) => track.kind === "video").clips).toHaveLength(2);
    const reviewCaptionTrack = tracks.find((track: any) => track.kind === "caption");
    expect(reviewCaptionTrack.cues.length).toBeGreaterThan(0);
    expect(reviewCaptionTrack.name).toBe("Legendas editoriais PT-BR");
    expect(reviewCaptionTrack.cues.every((cue: any) =>
      cue.speaker === null &&
      cue.sourceSegmentId === null &&
      cue.confidence === null
    )).toBeTruthy();
    expect(review.snapshot.composition.narrative).toMatchObject({
      captionMode: "editorial",
      speechExpected: false,
      voicePolicy: "prohibited",
      musicPolicy: "prohibited",
      naturalSoundPolicy: "required-before-approval",
    });
    const renderJobResponse = await request.get(
      `/api/v1/studios/v1/jobs/${review.renderJobId}`,
      { headers },
    );
    expect(renderJobResponse.status()).toBe(200);
    const renderJob = await renderJobResponse.json();
    expect(renderJob.status).toBe("succeeded");
    expect(renderJob.provider).toBe("builtin.ffmpeg-ugc-v1");
    expect(renderJob.executionCapability).toBe("media_cpu");
    expect(renderJob.queueName).toBe("studio.media.cpu");
    expect(renderJob.result.artifact.assetId).toBe(review.renderAssetId);
    expect(renderJob.result.artifact.checksumSha256).toBe(
      review.renderChecksumSha256,
    );
    expect(renderJob.result.framesRendered).toBe(47);
    expect(renderJob.result.renderedLayerIds).toEqual(["brand-band", "brand-cta"]);
    expect(renderJob.result.renderedCaptionTrackIds).toEqual(["captions-main"]);
    expect(renderJob.result.qualityEvaluation.status).toBe("passed");
    expect(renderJob.result.qualityEvaluation.policy.policyId).toBe("ugc-review-v1");
    expect(renderJob.result.qualityEvaluation.metrics.avDurationDeltaMs).toBeLessThanOrEqual(80);
    expect(renderJob.result.qualityEvaluation.metrics.blackFrameRatio).toBeLessThanOrEqual(0.05);
    expect(renderJob.result.warnings).not.toEqual(
      expect.arrayContaining([
        expect.stringContaining("page_layer_not_rendered"),
        expect.stringContaining("caption_track_not_rendered"),
      ]),
    );
    const assetsResponse = await request.get("/api/v1/assets", {
      headers,
      params: { workspace_id: workspaceId },
    });
    expect(assetsResponse.status()).toBe(200);
    const renderedAsset = (await assetsResponse.json()).find(
      (asset: any) => asset.id === review.renderAssetId,
    );
    expect(renderedAsset.metadata).toMatchObject({
      schemaVersion: "studio.asset-lineage.v1",
      derivation: "video_render",
      generationJobId: review.renderJobId,
      renderedFromOriginal: true,
      documentId: review.documentId,
      compositionProjection: {
        schemaVersion: "studio.ugc-composition-projection.v1",
        renderedLayerIds: ["brand-band", "brand-cta"],
        renderedCaptionTrackIds: ["captions-main"],
      },
      qualityEvaluation: {
        schemaVersion: "studio.video-technical-quality-evaluation.v1",
        status: "passed",
      },
    });
    expect(renderedAsset.metadata.sourceAssetBindings).toHaveLength(1);
    expect(renderedAsset.metadata.documentSnapshotSha256).toMatch(/^[0-9a-f]{64}$/);

    const foreignRegistration = await request.post("/api/v1/auth/register", {
      data: {
        email: `ugc-foreign-${suffix}@example.com`,
        name: "UGC Foreign",
        password: "senha-ugc-foreign-123",
        workspaceName: `UGC Foreign ${suffix}`,
      },
    });
    expect(foreignRegistration.status()).toBe(201);
    const foreignHeaders = {
      Authorization: `Bearer ${(await foreignRegistration.json()).accessToken}`,
    };
    expect(
      (
        await request.get(`/api/v1/studios/v1/jobs/${review.renderJobId}`, {
          headers: foreignHeaders,
        })
      ).status(),
    ).toBe(404);
    expect(
      (
        await request.get(renderJob.result.artifact.storageUri, {
          headers: foreignHeaders,
        })
      ).status(),
    ).toBe(404);
    const artifactResponse = await request.get(
      renderJob.result.artifact.storageUri,
      { headers },
    );
    expect(artifactResponse.status()).toBe(200);
    const artifactPath = join(fixtureDirectory, "ugc-rendered.mp4");
    writeFileSync(artifactPath, await artifactResponse.body());
    const probe = JSON.parse(
      execFileSync(
        "ffprobe",
        [
          "-v",
          "error",
          "-count_frames",
          "-show_entries",
          "stream=codec_name,width,height,avg_frame_rate,nb_read_frames",
          "-show_entries",
          "format=duration",
          "-of",
          "json",
          artifactPath,
        ],
        { encoding: "utf8" },
      ),
    );
    expect(probe.streams.find((stream: any) => stream.codec_name === "h264")).toMatchObject({
      width: 1080,
      height: 1920,
      avg_frame_rate: "30/1",
      nb_read_frames: "47",
    });
    expect(probe.streams.some((stream: any) => stream.codec_name === "aac")).toBeTruthy();

    const captionTrack = tracks.find((track: any) => track.kind === "caption");
    const evidenceCue = captionTrack.cues[0];
    const evidenceFrame =
      evidenceCue.timeline.startFrame +
      Math.floor(evidenceCue.timeline.durationFrames / 2);
    const brandCrop = extractRgbCrop(artifactPath, evidenceFrame, 80, 1645, 920, 140);
    const captionCrop = extractRgbCrop(artifactPath, evidenceFrame, 120, 1320, 840, 280);
    const ctaCrop = extractRgbCrop(artifactPath, evidenceFrame, 120, 1660, 840, 120);
    expect(
      countRgbPixels(
        brandCrop,
        (red, green, blue) =>
          Math.abs(red - 108) < 30 &&
          Math.abs(green - 92) < 30 &&
          Math.abs(blue - 231) < 30,
      ),
    ).toBeGreaterThan((brandCrop.length / 3) * 0.65);
    expect(countRgbPixels(captionCrop, (red, green, blue) => Math.min(red, green, blue) > 205)).toBeGreaterThan(300);
    expect(countRgbPixels(ctaCrop, (red, green, blue) => Math.min(red, green, blue) > 205)).toBeGreaterThan(300);

    const ingestsResponse = await request.get(
      "/api/v1/studios/v1/media-ingests",
      { headers, params: { workspace_id: workspaceId } },
    );
    const persistedIngest = (await ingestsResponse.json())[0];
    expect(persistedIngest.proxyAssetId).toBeTruthy();
    expect(persistedIngest.waveformAssetId).toBeTruthy();
    expect(persistedIngest.proxyTimeMap.sourceAssetId).toBe(
      review.snapshot.assets[0].id,
    );
    expect(persistedIngest.proxyTimeMap.representationAssetId).toBe(
      persistedIngest.proxyAssetId,
    );
    const transcriptsResponse = await request.get(
      "/api/v1/studios/v1/transcripts",
      {
        headers,
        params: {
          workspace_id: workspaceId,
          media_ingest_id: persistedIngest.id,
        },
      },
    );
    expect(transcriptsResponse.status()).toBe(200);
    expect(await transcriptsResponse.json()).toEqual([]);
    // The human listening attestation is bound to the pinned MP4 and saved with
    // the decision. This technical fixture is not production content approval.
    const reviewVideo = page.getByTestId("review-snapshot-video");
    await expect(reviewVideo).toHaveAttribute("src", /^blob:/);
    const acousticPanel = page.locator(".cx-acoustic-analysis");
    await expect(acousticPanel.getByRole("heading", { name: "Análise automática do MP4" })).toBeVisible();
    await expect(acousticPanel.getByText("Nenhum detector de fala e música foi aprovado.")).toBeVisible();
    await expect(acousticPanel.getByRole("button", { name: "Analisar fala e música" })).toBeDisabled();
    const approveAfterListening = page.getByRole("button", { name: /Aprovar esta versão/ });
    await expect(approveAfterListening).toBeDisabled();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByLabel("Ouvi o mix inteiro deste MP4").scrollIntoViewIfNeeded();
    const reviewMobileWidth = await page.locator(".cx-review-approved").evaluate((element) => ({
      client: element.clientWidth,
      scroll: element.scrollWidth,
    }));
    expect(reviewMobileWidth.scroll).toBeLessThanOrEqual(reviewMobileWidth.client + 1);
    const reviewAccessibility = await new AxeBuilder({ page })
      .include(".cx-review-approved")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(reviewAccessibility.violations).toEqual([]);
    await page.screenshot({ path: "artifacts/validation/video-review-listening-mobile.png", fullPage: true });
    await expect(page.getByText("Versão exata enviada para revisão humana.")).toBeHidden({ timeout: 10_000 });
    await acousticPanel.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "artifacts/validation/video-review-acoustic-unavailable-mobile.png", fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByLabel("Ouvi o mix inteiro deste MP4").check();
    await page.getByLabel("Fala ou narração incidental").selectOption("pass");
    await page.getByLabel("Música incidental").selectOption("pass");
    await page.getByLabel("Coerência dos sons naturais").selectOption("fail");
    await page.getByLabel("Equilíbrio do mix").selectOption("pass");
    await expect(approveAfterListening).toBeDisabled();
    await page.getByLabel("Coerência dos sons naturais").selectOption("pass");
    await expect(approveAfterListening).toBeEnabled();
    await page.getByLabel("Comentário da decisão").fill("Escuta da fixture técnica concluída; direitos e análise automática pendentes.");
    await approveAfterListening.click();
    await expect(page).toHaveURL(new RegExp(`/publish/${postId}$`));
    const approved = await request.get("/api/v1/studios/v1/reviews/latest", {
      headers, params: { workspace_id: workspaceId, post_id: postId },
    });
    expect(approved.status()).toBe(200);
    const approvedReview = await approved.json();
    expect(approvedReview.status).toBe("approved");
    expect(approvedReview.listeningReview).toMatchObject({
      reviewId: review.id,
      documentId: review.documentId,
      documentVersion: review.documentVersion,
      result: "pass",
      publicationAdmitted: false,
      submission: {
        renderAssetId: review.renderAssetId,
        renderChecksumSha256: review.renderChecksumSha256,
        listenedEntireMix: true,
        speechAbsent: "pass",
        musicAbsent: "pass",
        naturalSoundsCoherent: "pass",
        mixBalanced: "pass",
      },
    });
    expect(approvedReview.listeningReview.snapshotChecksumSha256).toMatch(/^[0-9a-f]{64}$/);
    for (const endpoint of ["publication-preflight", "publication-package"]) {
      const blocked = await request.get(`/api/v1/studios/v1/reviews/${review.id}/${endpoint}`, { headers });
      expect(blocked.status()).toBe(409);
      expect((await blocked.json()).detail.code).toBe("studio_publication_natural_sound_evidence_pending");
    }
    const blockedSchedule = await request.post(`/api/v1/studios/v1/reviews/${review.id}/internal-schedule`, {
      headers, data: { scheduledAt: new Date(Date.now() + 86_400_000).toISOString() },
    });
    expect(blockedSchedule.status()).toBe(409);
    await page.goto(`/publish/${postId}`);
    await expect(page.getByText(/O mix de sons naturais ainda não foi validado/)).toBeVisible();
    // Mute is a document edit, not just the player's local mute flag.
    await page.goto(`/content/${postId}/edit?mode=video`);
    await page.getByRole("button", { name: "Saída" }).click();
    await expect(page.getByRole("button", { name: "Remover som original" })).toBeEnabled();
    await page.getByRole("button", { name: "Remover som original" }).click();
    await expect(page.getByText("Som original removido da edição. O arquivo permanece intacto.")).toBeVisible();
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("muted", true);
    await expect(page.getByRole("button", { name: "Enviar para revisão" })).toBeDisabled();
    await page.reload();
    await page.getByRole("button", { name: "Saída" }).click();
    await expect(page.getByRole("button", { name: "Restaurar som original" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("muted", true);
    await page.getByRole("button", { name: "Saída" }).click();
    await page.getByRole("button", { name: "Renderizar prova privada" }).click();
    await expect(page.getByText("Prova sem som original · não é mix natural aprovado")).toBeVisible({ timeout: 90_000 });
    const documentsResponse = await request.get("/api/v1/studios/v1/documents", {
      headers, params: { workspace_id: workspaceId, post_id: postId },
    });
    const mutedDocument = (await documentsResponse.json()).find((item: any) => item.documentId === review.documentId);
    expect(mutedDocument.composition.mediaTimeline.tracks.find((item: any) => item.kind === "audio").muted).toBe(true);
    const jobsResponse = await request.get("/api/v1/studios/v1/jobs", { headers, params: { workspace_id: workspaceId } });
    const mutedJob = (await jobsResponse.json()).find((item: any) =>
      item.result?.documentRevision === mutedDocument.revision && item.jobType === "video_render"
    );
    expect(mutedJob.result.warnings).toContain("ffmpeg_ugc_original_audio_muted");
    expect(mutedJob.result.qualityEvaluation.metrics.silenceRatio).toBeGreaterThan(0.95);
    const mutedDownload = await request.get(mutedJob.result.artifact.storageUri, { headers });
    expect(mutedDownload.status()).toBe(200);
    const mutedPath = join(fixtureDirectory, "ugc-muted.mp4");
    writeFileSync(mutedPath, await mutedDownload.body());
    const decodedSilence = execFileSync("ffmpeg", ["-v", "error", "-i", mutedPath, "-vn", "-f", "s16le", "pipe:1"]);
    expect(decodedSilence.byteLength).toBeGreaterThan(48_000);
    expect(decodedSilence.some((byte) => byte !== 0)).toBe(false);
    expect((await request.get(mutedJob.result.artifact.storageUri, { headers: foreignHeaders })).status()).toBe(404);
    // The old human-review snapshot remains immutable and references the audible version.
    const previousReview = await request.get("/api/v1/studios/v1/reviews/latest", {
      headers, params: { workspace_id: workspaceId, post_id: postId },
    });
    expect(previousReview.status()).toBe(200);
    expect((await previousReview.json()).snapshot.composition.mediaTimeline.tracks.find((item: any) => item.kind === "audio").muted).toBe(false);
    await page.getByRole("button", { name: "Restaurar som original" }).click();
    await expect(page.getByText("Som original restaurado na edição; revisão acústica pendente.")).toBeVisible();
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("muted", false);
    await expect(page.getByRole("button", { name: "Enviar para revisão" })).toBeDisabled();
    const currentResponse = await request.get(`/api/v1/studios/v1/documents/${review.documentId}`, { headers });
    const currentDocument = await currentResponse.json();
    const concurrentSave = await request.put(`/api/v1/studios/v1/documents/${review.documentId}`, {
      headers, data: { expectedRevision: currentDocument.revision, document: currentDocument },
    });
    expect(concurrentSave.status()).toBe(200);
    await page.getByRole("button", { name: "Remover som original" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "A timeline mudou em outra sessão" })).toBeVisible();
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("muted", false);
    const unauthorizedMute = await request.put(`/api/v1/studios/v1/documents/${review.documentId}`, {
      headers: foreignHeaders, data: { expectedRevision: currentDocument.revision, document: currentDocument },
    });
    expect(unauthorizedMute.status()).toBe(404);
    // The same real action remains reachable without horizontal scrolling on mobile.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Remover som original" }).scrollIntoViewIfNeeded();
    await page.getByRole("button", { name: "Remover som original" }).click();
    await expect(page.getByRole("button", { name: "Restaurar som original" })).toHaveAttribute("aria-pressed", "true");
    // A private audio upload can be placed, adjusted and rendered without voice synthesis.
    const soundPath = join(fixtureDirectory, "sound-candidate.wav");
    await page.evaluate(() => {
      (window as any).__soundExperience = [];
      window.addEventListener("clicko:experience", (event) => {
        (window as any).__soundExperience.push((event as CustomEvent).detail);
      });
    });
    await page.getByRole("button", { name: "Sons", exact: true }).click();
    execFileSync("ffmpeg", ["-v", "error", "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=2", "-c:a", "pcm_s16le", soundPath]);
    await page.getByLabel("Arquivo WAV, MP3 ou FLAC — até 20 MB").setInputFiles(soundPath);
    await page.getByLabel("Origem e autoria do som").fill("Fixture técnica Clicko; não é som natural aprovado");
    await page.getByLabel("Licença ou autorização declarada").fill("Fixture de teste própria; sem uso em produção");
    await page.getByLabel("Início no vídeo (s)", { exact: true }).fill("0.3");
    await page.getByLabel("Início no arquivo (s)", { exact: true }).fill("0.2");
    await page.getByLabel("Duração do som (s)", { exact: true }).fill("0.6");
    await page.getByLabel("Volume do som (dB)").fill("-6");
    await page.getByLabel("Fade de entrada/saída (s)").fill("0.1");
    await page.getByRole("button", { name: "Aplicar som natural", exact: true }).click();
    await expect(page.getByText("Som salvo na edição. Renderize para conferir o mix; escuta e direitos ainda pendentes.")).toBeVisible({ timeout: 30_000 });
    const mixedSnapshot = await (await request.get(`/api/v1/studios/v1/documents/${review.documentId}`, { headers })).json();
    const soundRef = mixedSnapshot.assets.find((item: any) => item.provenance.purpose === "natural-sound-candidate");
    const soundEvents = await page.evaluate(() => (window as any).__soundExperience);
    expect(soundEvents).toContainEqual(expect.objectContaining({
      actionId: "VIDEO-SOUND-APPLY", screenId: "SCREEN-VIDEO", event: "video.natural_sound_apply_requested", kind: "action",
    }));
    expect(JSON.stringify(soundEvents)).not.toContain("Fixture técnica Clicko");
    expect(soundRef.rightsStatus).toBe("unknown");
    expect(soundRef.checksum).toHaveLength(64);
    expect(soundRef.provenance.humanListeningStatus).toBe("pending");
    expect(mixedSnapshot.composition.mediaTimeline.tracks.find((item: any) => item.id === "audio-natural").clips[0]).toMatchObject({
      assetId: soundRef.id, timeline: { startFrame: 9, durationFrames: 18 }, gainDb: -6,
      source: { startMicroseconds: 200_000, durationMicroseconds: 600_000 },
    });
    await expect(page.getByText("Som salvo na edição. Renderize para conferir o mix; escuta e direitos ainda pendentes.")).toBeHidden({ timeout: 10_000 });
    await page.getByRole("button", { name: "Revisar direitos deste som", exact: true }).click();
    const rightsPanel = page.locator(".vs-sound-rights");
    await rightsPanel.getByLabel("Decisão").selectOption("verified");
    await rightsPanel.getByLabel("Base do direito").selectOption("owned");
    await rightsPanel.getByLabel("Referência verificável da origem").fill("Fixture técnica interna CLICK-E2E-SOUND");
    await rightsPanel.getByLabel("Referência da licença ou autorização").fill("Declaração de teste CLICK-E2E-RIGHTS");
    await rightsPanel.getByLabel("Notas da conferência").fill("Teste automatizado; não autoriza uso em produção.");
    const rightsMobileWidth = await page.evaluate(() => ({
      client: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
    }));
    expect(rightsMobileWidth.scroll).toBeLessThanOrEqual(rightsMobileWidth.client + 1);
    const rightsAccessibility = await new AxeBuilder({ page })
      .include(".vs-sound-rights")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(rightsAccessibility.violations).toEqual([]);
    await rightsPanel.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "artifacts/validation/video-natural-sound-rights-mobile.png", fullPage: true });
    await rightsPanel.getByRole("button", { name: "Registrar decisão" }).click();
    await expect(page.getByText("Direitos verificados para este arquivo. Renderize novamente antes de enviar para revisão.")).toBeVisible();
    await expect(rightsPanel.getByText("Verificados", { exact: true })).toBeVisible();
    const rightsSnapshot = await (await request.get(`/api/v1/studios/v1/documents/${review.documentId}`, { headers })).json();
    const rightsRef = rightsSnapshot.assets.find((item: any) => item.id === soundRef.id);
    expect(rightsRef).toMatchObject({ rightsStatus: "verified", provenance: {
      rightsStatusReason: "rights_review_verified", rightsPublicationScope: "commercial-saas",
    }});
    expect(rightsRef.provenance.rightsReviewId).toBeTruthy();
    const rightsEvents = await page.evaluate(() => (window as any).__soundExperience);
    expect(rightsEvents).toContainEqual(expect.objectContaining({
      actionId: "VIDEO-SOUND-RIGHTS-SAVE", screenId: "SCREEN-VIDEO", event: "video.sound_rights_reviewed", kind: "action",
    }));
    expect(JSON.stringify(rightsEvents)).not.toContain("CLICK-E2E-RIGHTS");
    expect((await request.get(`/api/v1/assets/${soundRef.id}/content`, { headers: foreignHeaders })).status()).toBe(404);
    await page.reload();
    await page.getByRole("button", { name: "Sons", exact: true }).click();
    await expect(page.getByLabel("Início no vídeo (s)", { exact: true })).toHaveValue("0.3");
    await expect(page.getByLabel("Volume do som (dB)")).toHaveValue("-6");
    await page.getByLabel("Volume do som (dB)").fill("-9");
    await page.getByRole("button", { name: "Aplicar som natural", exact: true }).click();
    await expect(page.getByText("Som salvo na edição. Renderize para conferir o mix; escuta e direitos ainda pendentes.")).toBeVisible();
    const adjusted = await (await request.get(`/api/v1/studios/v1/documents/${review.documentId}`, { headers })).json();
    expect(adjusted.assets.map((item: any) => item.id)).toEqual(mixedSnapshot.assets.map((item: any) => item.id));
    expect(adjusted.assets.find((item: any) => item.id === soundRef.id).rightsStatus).toBe("verified");
    expect(adjusted.composition.mediaTimeline.tracks.find((item: any) => item.id === "audio-main").muted).toBe(true);
    const soundDocument = async () => (await request.get(`/api/v1/studios/v1/documents/${review.documentId}`, { headers })).json();
    const soundCues = (document: any) => document.composition.mediaTimeline.tracks.find((item: any) => item.id === "audio-natural").clips;
    const firstSoundId = soundCues(adjusted)[0].id;
    await page.getByRole("button", { name: "Adicionar outro som", exact: true }).click();
    await page.getByRole("combobox", { name: "Arquivo já importado", exact: true }).selectOption(soundRef.id);
    await page.getByLabel("Início no vídeo (s)", { exact: true }).fill("1");
    await page.getByLabel("Duração do som (s)", { exact: true }).fill("0.3");
    await page.getByRole("button", { name: "Aplicar som natural", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Som 2 ·/ })).toBeVisible();
    const twoSounds = await soundDocument();
    expect(twoSounds.assets.map((item: any) => item.id)).toEqual(adjusted.assets.map((item: any) => item.id));
    expect(soundCues(twoSounds)).toHaveLength(2);
    expect(soundCues(twoSounds).find((item: any) => item.id === firstSoundId)).toEqual(soundCues(adjusted)[0]);
    const secondSoundId = soundCues(twoSounds)[1].id;
    await page.getByLabel("Volume do som (dB)").fill("-12");
    await page.getByRole("button", { name: /^Som 1 ·/ }).click();
    await expect(page.getByText("Há ajustes não aplicados. Aplique ou descarte antes de trocar de som.")).toBeVisible();
    await expect(page.getByLabel("Volume do som (dB)")).toHaveValue("-12");
    await page.getByRole("button", { name: "Descartar ajustes e trocar" }).click();
    await expect(page.getByLabel("Volume do som (dB)")).toHaveValue("-9");
    await page.getByRole("button", { name: "Editar som natural no frame 30", exact: true }).click();
    await expect(page.getByLabel("Volume do som (dB)")).toHaveValue("-6");
    await page.getByRole("button", { name: "Desativar som selecionado", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Som 2 ·.*desativado/ })).toBeVisible();
    expect(soundCues(await soundDocument()).find((item: any) => item.id === secondSoundId).enabled).toBe(false);
    await page.getByRole("button", { name: "Desfazer último ajuste de som", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Som 2 ·.*ativo$/ })).toBeVisible();
    expect(soundCues(await soundDocument()).find((item: any) => item.id === secondSoundId).enabled).toBe(true);
    await expect(page.getByRole("button", { name: "Desfazer último ajuste de som", exact: true })).toBeDisabled();
    // Undo must not erase another session's newer sound mix.
    await page.getByRole("button", { name: "Desativar som selecionado", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Som 2 ·.*desativado/ })).toBeVisible();
    const beforeConcurrentSound = await soundDocument();
    soundCues(beforeConcurrentSound).find((item: any) => item.id === secondSoundId).gainDb = -15;
    const externalSoundSave = await request.put(`/api/v1/studios/v1/documents/${review.documentId}`, {
      headers, data: { expectedRevision: beforeConcurrentSound.revision, document: beforeConcurrentSound },
    });
    expect(externalSoundSave.status()).toBe(200);
    await page.getByRole("button", { name: "Desfazer último ajuste de som", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "nenhum ajuste foi desfeito" }).first()).toBeVisible();
    await expect(page.getByLabel("Volume do som (dB)")).toHaveValue("-15");
    expect(soundCues(await soundDocument()).find((item: any) => item.id === secondSoundId)).toMatchObject({ enabled: false, gainDb: -15 });
    await page.getByRole("button", { name: "Reativar som selecionado", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Som 2 ·.*ativo$/ })).toBeVisible();
    await page.reload();
    await page.getByRole("button", { name: "Sons", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Som 2 ·/ })).toBeVisible();
    const finalMixSnapshot = await soundDocument();
    // A failed private source must not silently yield a video-only preview.
    const soundUrl = `**/api/v1/assets/${soundRef.id}/content`;
    await page.route(soundUrl, (route) => route.fulfill({ status: 503, body: "temporary test failure" }));
    await page.getByRole("button", { name: "Reproduzir preview", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Erro HTTP 503" })).toBeVisible();
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("paused", true);
    await page.unroute(soundUrl);
    let heldSound: import("@playwright/test").Route | undefined;
    await page.route(soundUrl, (route) => { heldSound = route; });
    await page.getByRole("button", { name: "Reproduzir preview", exact: true }).click();
    await expect(page.getByText("Carregando e verificando os sons privados. Clique em cancelar para interromper.")).toBeVisible();
    await page.getByRole("button", { name: "Cancelar carregamento do preview", exact: true }).first().click();
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("paused", true);
    await heldSound?.abort().catch(() => undefined);
    await page.unroute(soundUrl);
    const seekPreview = async (seconds: number) => {
      await page.getByLabel("Posição do vídeo", { exact: true }).evaluate((input, value) => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, String(value));
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }, seconds);
    };
    await seekPreview(0.4);
    await page.evaluate(() => (window as any).__observePreviewSound());
    await page.getByRole("button", { name: "Reproduzir preview", exact: true }).click();
    await expect.poll(() => page.evaluate(() => (window as any).__soundPeak), { intervals: [15, 20, 30], timeout: 2000 }).toBeGreaterThan(0.002);
    await page.getByRole("button", { name: "Pausar preview", exact: true }).click();
    await expect.poll(() => page.evaluate(() => (window as any).__soundRms()), { intervals: [25, 50], timeout: 2000 }).toBe(0);
    await seekPreview(1.05);
    await page.evaluate(() => (window as any).__observePreviewSound());
    await page.getByRole("button", { name: "Reproduzir preview", exact: true }).click();
    await expect.poll(() => page.evaluate(() => (window as any).__soundPeak), { intervals: [15, 20, 30], timeout: 2000 }).toBeGreaterThan(0.001);
    expect(await page.evaluate(() => (window as any).__soundSamples.some((sample: any) => sample.time >= 1 && sample.time < 1.34 && sample.rms > 0.001))).toBe(true);
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("muted", true);
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("paused", true, { timeout: 3000 });
    await expect.poll(() => page.evaluate(() => (window as any).__soundRms()), { intervals: [25, 50], timeout: 2000 }).toBe(0);
    // Uninterrupted output crosses the reordered source boundary, not only seeks.
    await seekPreview(0);
    await page.evaluate(() => {
      (window as any).__previewSamples = [];
      (window as any).__samplePreview = true;
      const sample = () => {
        const input = document.querySelector<HTMLInputElement>('[aria-label="Posição do vídeo"]');
        (window as any).__previewSamples.push({ time: Number(input?.value ?? 0), rms: (window as any).__soundRms() });
        if ((window as any).__samplePreview) requestAnimationFrame(sample);
      };
      requestAnimationFrame(sample);
    });
    await page.getByRole("button", { name: "Reproduzir preview", exact: true }).click();
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("paused", false);
    await expect(page.locator(".vs-phone-frame video")).toHaveJSProperty("paused", true, { timeout: 3000 });
    const samples = await page.evaluate(() => { (window as any).__samplePreview = false; return (window as any).__previewSamples as Array<{ time: number; rms: number }>; });
    expect(samples.some((sample) => sample.time > 0.4 && sample.time < 0.8 && sample.rms > 0.002)).toBe(true);
    expect(samples.some((sample) => sample.time > 1.0 && sample.time < 1.3 && sample.rms > 0.001)).toBe(true);
    expect((await soundDocument()).revision).toBe(finalMixSnapshot.revision);
    const soundAccessibility = await new AxeBuilder({ page }).include(".vs-shell").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(soundAccessibility.violations).toEqual([]);
    const mobileHeader = await page.locator(".vs-topbar").evaluate((header) => {
      const title = header.querySelector(".vs-title")!.getBoundingClientRect();
      const back = header.querySelector(".vs-back")!.getBoundingClientRect();
      const review = header.querySelector(".vs-review")!.getBoundingClientRect();
      return { titleLeft: title.left, titleRight: title.right, titleBottom: title.bottom,
        backRight: back.right, reviewTop: review.top, width: document.documentElement.clientWidth };
    });
    expect(mobileHeader.titleLeft).toBeGreaterThanOrEqual(mobileHeader.backRight);
    expect(mobileHeader.titleRight).toBeLessThanOrEqual(mobileHeader.width);
    expect(mobileHeader.reviewTop).toBeGreaterThanOrEqual(mobileHeader.titleBottom);
    await page.locator(".vs-topbar").scrollIntoViewIfNeeded();
    await page.screenshot({ path: "artifacts/validation/video-studio-header-mobile.png", fullPage: true });
    await page.getByRole("button", { name: "Adicionar outro som", exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: "artifacts/validation/video-studio-natural-sound-mobile.png", fullPage: true });
    await page.getByRole("button", { name: "Saída" }).click();
    await page.getByRole("button", { name: "Renderizar prova privada" }).click();
    await expect(page.getByText("Som externo materializado · origem e escuta pendentes")).toBeVisible({ timeout: 90_000 });
    await expect(page.getByLabel("MP4 renderizado com o mix de áudio")).toBeVisible();
    const mixedJobs = await (await request.get("/api/v1/studios/v1/jobs", { headers, params: { workspace_id: workspaceId } })).json();
    const mixedJob = mixedJobs.find((item: any) => item.jobType === "video_render" && item.result?.documentRevision === finalMixSnapshot.revision);
    expect(mixedJob.status).toBe("succeeded");
    const mixBytes = await (await request.get(mixedJob.result.artifact.storageUri, { headers })).body();
    const mixPath = join(fixtureDirectory, "ugc-with-sound.mp4");
    writeFileSync(mixPath, mixBytes);
    const mixPcm = execFileSync("ffmpeg", ["-v", "error", "-i", mixPath, "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1"]);
    expect(mixPcm.subarray(4800, 14400).some((byte) => byte !== 0)).toBe(false);
    expect(mixPcm.subarray(38400, 67200).some((byte) => byte !== 0)).toBe(true);
    expect(mixPcm.subarray(100800, 115200).some((byte) => byte !== 0)).toBe(true);
    // Disable cue 2 only, render again, and compare the actual PCM windows.
    await page.getByRole("button", { name: "Sons", exact: true }).click();
    await page.getByRole("button", { name: /^Som 2 ·/ }).click();
    await page.getByRole("button", { name: "Desativar som selecionado", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Som 2 ·.*desativado/ })).toBeVisible();
    const inactiveMix = await soundDocument();
    await page.getByRole("button", { name: "Saída" }).click();
    await page.getByRole("button", { name: "Renderizar prova privada" }).click();
    await expect(page.getByText("Prova privada vinculável")).toBeVisible({ timeout: 90_000 });
    const updatedSoundJobs = await (await request.get("/api/v1/studios/v1/jobs", { headers, params: { workspace_id: workspaceId } })).json();
    const inactiveJob = updatedSoundJobs.find((item: any) => item.jobType === "video_render" && item.result?.documentRevision === inactiveMix.revision);
    expect(inactiveJob?.status).toBe("succeeded");
    const inactivePath = join(fixtureDirectory, "ugc-inactive-cue.mp4");
    writeFileSync(inactivePath, await (await request.get(inactiveJob.result.artifact.storageUri, { headers })).body());
    const inactivePcm = execFileSync("ffmpeg", ["-v", "error", "-i", inactivePath, "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1"]);
    expect(inactivePcm.subarray(38400, 67200).some((byte) => byte !== 0)).toBe(true);
    expect(inactivePcm.subarray(100800, 115200).some((byte) => byte !== 0)).toBe(false);
    const widths = await page.evaluate(() => ({
      client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth,
    }));
    expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1);
    const accessibility = await new AxeBuilder({ page }).include(".vs-shell").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(accessibility.violations).toEqual([]);
    await page.screenshot({ path: "artifacts/validation/video-studio-muted-mobile.png", fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    const tabSizes = await page.locator(".vs-inspector-tabs button").evaluateAll((buttons) => buttons.map((button) => ({ client: button.clientWidth, scroll: button.scrollWidth })));
    expect(tabSizes.every((size) => size.scroll <= size.client)).toBe(true);
    await page.screenshot({
      path: "artifacts/validation/video-studio-ugc.png",
      fullPage: true,
    });
  } finally {
    rmSync(fixtureDirectory, { recursive: true, force: true });
  }
});

test("Studio autenticado persiste Visual e Carrossel até revisão e exportação", async ({
  page,
  request,
}) => {
  test.setTimeout(60_000);
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const registration = await request.post("/api/v1/auth/register", {
    data: {
      email: `studio-e2e-${suffix}@example.com`,
      name: "Studio E2E",
      password: "senha-studio-e2e-123",
      workspaceName: `Studio E2E ${suffix}`,
    },
  });
  expect(registration.status()).toBe(201);
  const { accessToken } = await registration.json();
  const bootstrap = await request.get("/api/v1/bootstrap", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const bootstrapData = await bootstrap.json();
  const workspaceId = bootstrapData.workspaces[0].id;
  const brandProfile = bootstrapData.workspaces[0].brandProfile;
  brandProfile.industry = "marketing de conteúdo auditável";
  brandProfile.targetAudience = "gestores de social media que exigem evidência";
  brandProfile.keywords = ["conteúdo", "evidência", "contexto", "social media"];
  brandProfile.products = [{ name: "Clicko Studios", description: "produção de conteúdo auditável" }];
  brandProfile.pillars = ["contexto", "evidência", "criação"];
  brandProfile.watchlist = { brainRevision: 2, topics: ["conteúdo auditável"] };
  const updatedBrand = await request.patch(`/api/v1/workspaces/${workspaceId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: { brandProfile },
  });
  expect(updatedBrand.status()).toBe(200);
  const signal = await request.post("/api/v1/radar/signals", {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: {
      workspaceId,
      source: "Fonte pública E2E",
      url: `https://example.com/studio-e2e-${suffix}`,
      title: "Gestores de social media priorizam conteúdo auditável com evidência",
      summary: "Contexto e evidência orientam criação de conteúdo para social media.",
      publishedAt: new Date().toISOString(),
      topics: ["conteúdo", "evidência", "contexto", "social media"],
      metrics: { novelty_score: 70, momentum_score: 45 },
    },
  });
  expect(signal.status()).toBe(201);
  const ranked = await request.post("/api/v1/radar/rank", {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: { workspaceId },
  });
  expect(ranked.status()).toBe(200);
  const opportunity = (await ranked.json())[0];
  const campaignResponse = await request.post("/api/v1/campaigns", {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: {
      workspaceId,
      opportunityId: opportunity.id,
      name: "Campanha vertical Studio",
      status: "planned",
      brainRevision: 2,
    },
  });
  expect(campaignResponse.status()).toBe(201);
  const campaignId = (await campaignResponse.json()).id;
  const createdPost = await request.post("/api/v1/posts", {
    headers: { Authorization: `Bearer ${accessToken}` },
    data: {
      workspaceId,
      title: "Corte vertical auditável",
      platform: "Instagram",
      format: "carousel",
      copy: "Brief real para o primeiro corte do Studio.",
      status: "draft",
      author: "Studio E2E",
      objective: "Validar persistência ponta a ponta",
      campaignId,
      brainRevision: 2,
      origin: "strategy",
    },
  });
  expect(createdPost.status()).toBe(201);
  const postId = (await createdPost.json()).id;
  await page.addInitScript(
    ({ token }) => localStorage.setItem("nexus_access_token", token),
    { token: accessToken },
  );

  await page.goto(`/content/${postId}/edit?mode=visual`);
  await expect(page.locator(".cx-demo-banner")).toHaveCount(0);
  const visualHeadline = page.getByRole("textbox", { name: "Headline visual" });
  await expect(visualHeadline).toBeEnabled();
  const openedDocuments = await request.get("/api/v1/studios/v1/documents", {
    headers: { Authorization: `Bearer ${accessToken}` },
    params: { workspace_id: workspaceId, post_id: postId },
  });
  const externallyEdited = (await openedDocuments.json()).find(
    (document: any) => document.contentType === "visual",
  );
  externallyEdited.title = "Edição concorrente auditável";
  const concurrentSave = await request.put(
    `/api/v1/studios/v1/documents/${externallyEdited.documentId}`,
    {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: {
        expectedRevision: externallyEdited.revision,
        document: externallyEdited,
      },
    },
  );
  expect(concurrentSave.status()).toBe(200);
  await visualHeadline.fill("ALTERAÇÃO LOCAL EM CONFLITO");
  await expect(page.getByText("Este documento mudou em outra sessão.")).toBeVisible();
  await page.getByRole("button", { name: "Recarregar versão atual" }).click();
  await expect(visualHeadline).toHaveValue("O Brasil cabe em uma xícara.");
  await visualHeadline.fill("CONTEXTO VIRA CRIAÇÃO AUDITÁVEL.");
  await expect(page.locator(".cx-visual-approved > header > i")).toContainText(
    "Sincronizado",
  );
  await page.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(page.getByText("Peça visual salva")).toBeVisible();
  await expect(page.locator(".cx-visual-approved > header > strong")).toHaveText("v1");
  await page.getByRole("button", { name: "Criar versão", exact: true }).click();
  await expect(page.getByText("Nova versão visual criada")).toBeVisible();
  await page.reload();
  await expect(visualHeadline).toHaveValue("CONTEXTO VIRA CRIAÇÃO AUDITÁVEL.");
  await expect(page.locator(".cx-visual-approved > header > strong")).toHaveText("v2");
  await visualHeadline.fill("SEGUNDA DIREÇÃO PARA COMPARAR.");
  await expect(page.locator(".cx-visual-approved > header > i")).toContainText("Sincronizado");
  await page.getByRole("button", { name: "Criar versão", exact: true }).click();
  await expect(page.locator(".cx-visual-approved > header > strong")).toHaveText("v3");
  await page.getByRole("button", { name: "Histórico", exact: true }).click();
  const historyDialog = page.getByRole("dialog", {
    name: "Histórico de versões do Studio",
  });
  await expect(historyDialog).toBeVisible();
  await historyDialog
    .locator(".cx-studio-history-body > aside > button")
    .filter({ hasText: "v2" })
    .click();
  await expect(historyDialog.locator(".cx-studio-version-compare")).toContainText(
    "CONTEXTO VIRA CRIAÇÃO AUDITÁVEL.",
  );
  await expect(historyDialog.locator(".cx-studio-version-compare")).toContainText(
    "SEGUNDA DIREÇÃO PARA COMPARAR.",
  );
  await historyDialog.getByRole("button", { name: "Restaurar como nova versão" }).click();
  await expect(page.getByText("v2 restaurada como uma nova versão")).toBeVisible();
  await expect(visualHeadline).toHaveValue("CONTEXTO VIRA CRIAÇÃO AUDITÁVEL.");
  await expect(page.locator(".cx-visual-approved > header > strong")).toHaveText("v5");
  await page.getByRole("button", { name: "Movimento", exact: true }).click();
  await expect(page.getByTestId("motion-inspector")).toBeVisible();
  await page.getByRole("button", { name: "Salvar sugestão" }).click();
  await expect(page.getByText(/Sugestão reversível salva/)).toBeVisible();
  await page.getByRole("button", { name: "Revisar e aplicar" }).click();
  await expect(page.getByText(/Movimento revisado e aplicado/)).toBeVisible();
  const motionGraphs = await request.get("/api/v1/studios/v1/motion-graphs", {
    headers: { Authorization: `Bearer ${accessToken}` },
    params: { workspace_id: workspaceId },
  });
  expect(motionGraphs.status()).toBe(200);
  expect((await motionGraphs.json())[0].graph.status).toBe("reviewed");
  await page.getByRole("button", { name: "Exportar", exact: true }).click();
  await expect(page.getByText("PNG exportado para a biblioteca")).toBeVisible();
  await page
    .getByRole("button", { name: "Enviar para revisão", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`/approvals/${postId}`));
  await expect(page.getByTestId("review-studio-headline")).toHaveText(
    "CONTEXTO VIRA CRIAÇÃO AUDITÁVEL.",
  );
  await expect(page.locator(".cx-review-approved > header .cx-chip")).toHaveText("v5");
  await page.getByRole("button", { name: /Aprovar esta versão/ }).click();
  await expect(page).toHaveURL(new RegExp(`/publish/${postId}$`));

  await navigateSpa(page, `/content/${postId}/edit?mode=carousel`);
  await expect(page.getByRole("button", { name: "Salvar", exact: true })).toBeEnabled();
  await page.getByRole("textbox", { name: "Título do slide" }).fill("UMA HISTÓRIA EM SETE PASSOS");
  await page.getByRole("button", { name: "Adicionar slide" }).click();
  await expect(page.locator(".cx-carousel-approved > header > span")).toContainText("Salvo agora");
  await page.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(page.getByText("Carrossel salvo")).toBeVisible();
  await page.getByRole("button", { name: "Criar versão", exact: true }).click();
  await expect(page.getByText("Nova versão do carrossel criada")).toBeVisible();
  await page.getByRole("button", { name: "Exportar", exact: true }).click();
  await expect(page.getByText("Pacote PNG ordenado exportado para a biblioteca")).toBeVisible();
  await page.reload();
  await expect(page.getByText("7 slides · 48s de leitura")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Título do slide" })).toHaveValue(
    "UMA HISTÓRIA EM SETE PASSOS",
  );
  const studioDocuments = await request.get("/api/v1/studios/v1/documents", {
    headers: { Authorization: `Bearer ${accessToken}` },
    params: { workspace_id: workspaceId, post_id: postId },
  });
  const persistedDocuments = await studioDocuments.json();
  expect(persistedDocuments).toHaveLength(2);
  expect(persistedDocuments.every((document: any) => document.brandMemoryRef.revision === 2)).toBeTruthy();
  expect(persistedDocuments.every((document: any) => document.opportunityRef.id === opportunity.id)).toBeTruthy();
  expect(
    persistedDocuments.some((document: any) =>
      document.exports.some((entry: any) => entry.format === "png_set"),
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "artifacts/validation/studios-authenticated-carousel.png",
  });
});
