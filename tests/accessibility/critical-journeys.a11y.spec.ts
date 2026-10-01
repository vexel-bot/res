import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const criticalSurfaces = [
  { name: "Início", path: "/dashboard" },
  { name: "Criar", path: "/content/new?type=post" },
  { name: "Editar imagem", path: "/content/post-ritual/edit?mode=visual" },
  { name: "Editar vídeo", path: "/content/post-ritual/edit?mode=video" },
  { name: "Reutilizar", path: "/content/post-ritual/remix" },
  { name: "Fábrica", path: "/factory" },
  { name: "Revisar", path: "/approvals/post-ritual" },
  { name: "Publicar", path: "/publish/post-ritual" },
] as const;

const evidenceDirectory = resolve(
  process.cwd(),
  "artifacts/validation/accessibility",
);

function violationSummary(
  violations: Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"],
) {
  return violations
    .map(
      (violation) =>
        `${violation.id} (${violation.impact ?? "unknown"}): ${violation.nodes
          .map((node) => node.target.join(" "))
          .join(", ")}`,
    )
    .join("\n");
}

for (const surface of criticalSurfaces) {
  test(`${surface.name} não possui violações WCAG A/AA detectáveis`, async ({
    page,
  }, testInfo) => {
    await page.goto(surface.path);
    await page.locator("body").waitFor({ state: "visible" });

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();

    mkdirSync(evidenceDirectory, { recursive: true });
    writeFileSync(
      resolve(
        evidenceDirectory,
        `${surface.name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, "-")}.json`,
      ),
      `${JSON.stringify(results, null, 2)}\n`,
      "utf8",
    );

    await testInfo.attach("axe-results", {
      body: JSON.stringify(results, null, 2),
      contentType: "application/json",
    });

    expect(results.violations.length, violationSummary(results.violations)).toBe(
      0,
    );
  });
}
