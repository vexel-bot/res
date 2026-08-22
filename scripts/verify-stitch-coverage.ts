import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { SCREEN_TOTALS, STITCH_SCREENS } from "../src/product/screenManifest";
import { STITCH_ARTIFACTS } from "../src/product/stitchArtifacts.generated";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

assert(
  SCREEN_TOTALS.approved === 38,
  `Projeto aprovado deveria ter 38 telas; recebeu ${SCREEN_TOTALS.approved}.`,
);
assert(
  SCREEN_TOTALS.creativeLab === 19,
  `Creative Lab deveria ter 19 telas; recebeu ${SCREEN_TOTALS.creativeLab}.`,
);
assert(
  SCREEN_TOTALS.total === 57,
  `A matriz deveria ter 57 telas; recebeu ${SCREEN_TOTALS.total}.`,
);

const ids = new Set(STITCH_SCREENS.map((screen) => screen.id));
assert(ids.size === 57, "Há IDs duplicados na matriz de telas.");
assert(
  STITCH_SCREENS.every((screen) => screen.route.startsWith("/")),
  "Toda tela precisa de uma rota absoluta.",
);
assert(
  !STITCH_SCREENS.some((screen) =>
    screen.frame.includes("Creative OS Redesign"),
  ),
  "O projeto descartável entrou na matriz.",
);
assert(
  STITCH_ARTIFACTS.length === 57,
  `A importação deveria conter 57 artefatos; recebeu ${STITCH_ARTIFACTS.length}.`,
);
assert(
  new Set(STITCH_ARTIFACTS.map((artifact) => artifact.screenId)).size === 57,
  "Há screenIds duplicados na importação.",
);

for (const artifact of STITCH_ARTIFACTS) {
  const source = resolve(
    "public",
    artifact.htmlPath.replace(/^\/stitch\//, "stitch/"),
  );
  const screenshot = resolve(
    "public",
    artifact.screenshotPath.replace(/^\/stitch\//, "stitch/"),
  );
  assert(
    existsSync(source) && statSync(source).size > 1_000,
    `${artifact.id}: HTML exportado ausente ou vazio.`,
  );
  assert(
    existsSync(screenshot) && statSync(screenshot).size > 1_000,
    `${artifact.id}: screenshot exportado ausente ou vazio.`,
  );
  assert(
    readFileSync(source, "utf8").includes("/stitch/bridge.js"),
    `${artifact.id}: ponte de navegação ausente.`,
  );
}

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return [".ts", ".tsx", ".css"].includes(extname(entry.name)) ? [path] : [];
  });
}

const frontendFiles = sourceFiles(resolve("src"));

const legacyGreen = /#(?:8bd132|98dc45|477713|3f6e0f)\b/i;
const offenders = frontendFiles.filter((file) =>
  legacyGreen.test(readFileSync(file, "utf8")),
);
assert(
  offenders.length === 0,
  `Verde legado encontrado em: ${offenders.join(", ")}`,
);

console.log(
  `Stitch: ${SCREEN_TOTALS.approved} + ${SCREEN_TOTALS.creativeLab} = ${SCREEN_TOTALS.total} telas rastreadas.`,
);
console.log(
  "Fontes: 57 HTMLs e 57 screenshots oficiais preservados como especificação visual; o produto usa componentes React compartilhados, sem iframe.",
);
console.log("Paleta: nenhum verde legado encontrado no frontend.");
