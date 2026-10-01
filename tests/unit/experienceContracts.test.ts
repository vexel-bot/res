import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  validateActionContract,
  validateScreenContract,
  type ActionContract,
  type ScreenContract,
} from "../../src/app/experience/contracts.ts";
import {
  EXPERIENCE_ACTIONS,
  EXPERIENCE_SCREENS,
  experienceScreenForLocation,
  validateExperienceRegistry,
} from "../../src/app/experience/registry.ts";
import {
  matchingRoutesForPath,
  effectiveRouteOwnerForPath,
  NAVIGATION_TAB_PATHS,
  routeForPath,
  routeNavigationTabForPath,
  validateRouteRegistry,
} from "../../src/app/router/routeRegistry.ts";
import { TAB_PATHS } from "../../src/app/router/navigation.ts";
import { STITCH_SCREENS } from "../../src/product/screenManifest.ts";
import {
  ExperienceShell,
  HonestState,
  PRODUCTION_STEPS,
} from "../../src/app/experience/shells.tsx";

test("route registry has unique IDs/templates and one owner per known URL", () => {
  assert.deepEqual(validateRouteRegistry(), []);
  const knownPaths = new Set([
    ...Object.values(TAB_PATHS),
    ...STITCH_SCREENS.map((screen) => screen.route),
  ]);

  for (const path of knownPaths) {
    const matches = matchingRoutesForPath(path);
    assert.equal(matches.length, 1, `${path} matched ${matches.length} routes`);
  }
});

test("registry preserves current strangler ownership", () => {
  assert.equal(routeForPath("/content/post-1/edit?mode=video")?.owner, "canonical");
  assert.equal(routeForPath("/campaigns/active/studio")?.owner, "product-surface");
  assert.equal(routeForPath("/copilot?context=campaign")?.owner, "legacy");
  assert.equal(routeForPath("/factory/round-1")?.routeId, "ROUTE-FACTORY-ROUND");
  assert.equal(routeForPath("/does-not-exist"), undefined);
  assert.equal(
    effectiveRouteOwnerForPath("/content/post-1/edit?mode=video", {
      VITE_CANONICAL_CX_ROUTES: "false",
    }),
    "legacy",
  );
  assert.equal(
    effectiveRouteOwnerForPath("/content/post-1/edit?mode=video", {
      VITE_CANONICAL_CX_ROUTES: "true",
    }),
    "canonical",
  );
  assert.equal(
    effectiveRouteOwnerForPath("/content/new", {
      VITE_CANONICAL_CX_ROUTES: "false",
    }),
    "product-surface",
  );
});

test("navigation destinations and active tabs derive from the route registry", () => {
  for (const [tab, path] of Object.entries(NAVIGATION_TAB_PATHS)) {
    assert.equal(routeNavigationTabForPath(path), tab, `${tab} does not own ${path}`);
  }
  assert.equal(routeNavigationTabForPath("/campaigns/active/studio"), "studio");
  assert.equal(routeNavigationTabForPath("/radar/opportunities/op-1"), undefined);
});

test("all canonical vertical slices have valid reachable contracts", () => {
  assert.ok(EXPERIENCE_ACTIONS.length >= 36);
  assert.ok(EXPERIENCE_SCREENS.length >= 14);
  for (const actionId of [
    "CAROUSEL-VISUALIZE-SET",
    "REUSE-GENERATE-DERIVATIONS",
    "FACTORY-START-ROUND",
    "FACTORY-OPEN-BATCH-REVIEW",
    "EDITORIAL-OPEN-VIDEO",
    "VIDEO-UPLOAD-SOURCE",
    "VIDEO-RENDER-PREVIEW",
    "VIDEO-SEND-REVIEW",
    "EDITORIAL-OPEN-PRESENTER",
    "PRESENTER-OPEN-IDENTITIES",
    "IDENTITY-START-ENROLLMENT",
    "IDENTITY-SUBMIT-ENROLLMENT",
    "IDENTITY-REVOKE-CONSENT",
    "PRESENTER-GENERATE-SAMPLE",
    "PRESENTER-OPEN-VIDEO",
    "VISUAL-OPEN-MOTION",
    "MOTION-SAVE-SUGGESTION",
    "MOTION-APPLY",
    "LIBRARY-OPEN-IMAGE-LAB",
    "IMAGE-COMPARE",
    "IMAGE-CREATE-DERIVATION",
    "IMAGE-RETURN",
  ]) {
    assert.ok(
      EXPERIENCE_ACTIONS.some((action) => action.actionId === actionId),
      `${actionId} is missing`,
    );
  }
  const video = EXPERIENCE_SCREENS.find(
    (screen) => screen.screenId === "SCREEN-VIDEO",
  );
  assert.equal(video?.primaryActionId, "VIDEO-RENDER-PREVIEW");
  assert.ok(video?.supportedStates.includes("job-running"));
  assert.equal(
    experienceScreenForLocation("/content/post-1/edit?mode=video")?.screenId,
    "SCREEN-VIDEO",
  );
  const presenter = EXPERIENCE_SCREENS.find(
    (screen) => screen.screenId === "SCREEN-PRESENTER",
  );
  assert.equal(presenter?.primaryActionId, "PRESENTER-GENERATE-SAMPLE");
  assert.ok(presenter?.supportedStates.includes("forbidden"));
  assert.equal(
    experienceScreenForLocation("/content/post-1/edit?mode=presenter")?.screenId,
    "SCREEN-PRESENTER",
  );
  const identities = EXPERIENCE_SCREENS.find(
    (screen) => screen.screenId === "SCREEN-IDENTITY-LIBRARY",
  );
  assert.equal(identities?.primaryActionId, "IDENTITY-START-ENROLLMENT");
  assert.equal(
    experienceScreenForLocation("/library/identities")?.screenId,
    "SCREEN-IDENTITY-LIBRARY",
  );
  const motionVisual = experienceScreenForLocation(
    "/content/post-1/edit?mode=visual&tool=motion",
  );
  assert.equal(motionVisual?.screenId, "SCREEN-VISUAL");
  assert.ok(motionVisual?.secondaryActionIds.includes("MOTION-APPLY"));
  const imageLab = EXPERIENCE_SCREENS.find(
    (screen) => screen.screenId === "SCREEN-IMAGE-LAB",
  );
  assert.equal(imageLab?.primaryActionId, "IMAGE-CREATE-DERIVATION");
  assert.equal(
    experienceScreenForLocation("/library/assets/asset-1/edit?mode=image")?.screenId,
    "SCREEN-IMAGE-LAB",
  );
  assert.deepEqual(validateExperienceRegistry(), []);
  for (const screen of EXPERIENCE_SCREENS) {
    assert.equal(
      experienceScreenForLocation(screen.examplePath)?.screenId,
      screen.screenId,
      `${screen.screenId} cannot be resolved from ${screen.examplePath}`,
    );
  }
});

test("action and screen contracts fail closed", () => {
  const action: ActionContract = {
    actionId: "CREATE-START",
    label: "Começar",
    type: "NAV",
    object: "creative brief",
    preconditions: ["workspace selected"],
    permissions: ["content:create"],
    sideEffect: "opens the direction screen with the selected context",
    feedback: {
      loading: "Abrindo direção…",
      success: "Direção pronta para editar",
      recoverableError: "Não foi possível abrir. Tente novamente.",
    },
    persistence: "none",
    nextRoute: "/campaigns/new",
    analyticsEvent: "create.direction_started",
    accessibleName: "Começar uma direção criativa",
    testId: "create-start",
  };
  assert.deepEqual(validateActionContract(action), []);

  const screen: ScreenContract = {
    screenId: "SCREEN-CREATE-HUB",
    routeTemplate: "/content/new",
    owner: "product-surface",
    shell: "decision",
    userJob: "start by the outcome rather than by a model",
    requiredContext: ["workspaceId"],
    focalObject: "creation intent",
    primaryActionId: action.actionId,
    secondaryActionIds: [],
    output: "creative brief draft",
    nextBestAction: "compare or approve a direction",
    supportedStates: ["loading", "empty", "ready", "recoverable-error", "forbidden"],
    permissions: ["content:create"],
    persistence: "local",
    analyticsViewEvent: "create.hub_viewed",
    acceptanceTests: ["user can start from an opportunity, offer, or brief"],
  };
  assert.deepEqual(
    validateScreenContract(screen, new Map([[action.actionId, action]])),
    [],
  );

  const invalidJob = { ...action, actionId: "VIDEO-RENDER", type: "JOB", persistence: "none" } as ActionContract;
  assert.ok(validateActionContract(invalidJob).some((issue) => issue.field === "persistence"));
});

test("shared shell and honest-state primitives expose stable semantic contracts", () => {
  const shellMarkup = renderToStaticMarkup(
    React.createElement(
      ExperienceShell,
      {
        shell: "studio",
        routeId: "ROUTE-CONTENT-EDIT",
        screenId: "SCREEN-VISUAL",
        state: "dirty",
      },
      React.createElement("div", null, "Canvas"),
    ),
  );
  assert.match(shellMarkup, /data-shell="studio"/);
  assert.match(shellMarkup, /data-screen-state="dirty"/);
  assert.match(shellMarkup, /data-scroll-owner="cx-main"/);
  assert.deepEqual(PRODUCTION_STEPS, [
    "Direção",
    "Roteiro",
    "Materiais",
    "Montagem",
    "Revisão",
    "Entrega",
  ]);

  const noDecorativeAction = renderToStaticMarkup(
    React.createElement(HonestState, {
      state: "offline",
      detail: "A conexão caiu.",
      actionLabel: "Tentar novamente",
    }),
  );
  assert.doesNotMatch(noDecorativeAction, /<button/);

  const explainedDisabledAction = renderToStaticMarkup(
    React.createElement(HonestState, {
      state: "forbidden",
      detail: "Você não pode publicar.",
      actionLabel: "Publicar",
      disabledReason: "Permissão content:publish necessária.",
    }),
  );
  assert.match(explainedDisabledAction, /disabled=""/);
  assert.match(explainedDisabledAction, /Permissão content:publish necessária/);
});
