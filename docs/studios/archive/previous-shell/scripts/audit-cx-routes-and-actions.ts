import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import ts from "typescript";

import {
  ROUTE_REGISTRY,
  matchingRoutesForPath,
  routeForPath,
  validateRouteRegistry,
} from "../src/app/router/routeRegistry.ts";
import { EXPERIENCE_ACTIONS } from "../src/app/experience/registry.ts";
import { TAB_PATHS } from "../src/app/router/navigation.ts";
import { STITCH_SCREENS } from "../src/product/screenManifest.ts";

interface ControlFinding {
  file: string;
  line: number;
  tag: string;
  actionId: string | null;
  hasActionIdAttribute: boolean;
  labelHint: string | null;
  contractScope: boolean;
  requiresActionId: boolean;
  classification:
    | "wired"
    | "submit"
    | "disabled-with-reason"
    | "disabled-without-reason"
    | "review";
}

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return entry.isFile() && path.endsWith(".tsx") ? [path] : [];
  });
}

function attributeName(attribute: ts.JsxAttributeLike) {
  return ts.isJsxAttribute(attribute) ? attribute.name.getText() : "";
}

function literalAttribute(
  attributes: ts.NodeArray<ts.JsxAttributeLike>,
  name: string,
) {
  const attribute = attributes.find(
    (candidate) => attributeName(candidate) === name,
  );
  if (!attribute || !ts.isJsxAttribute(attribute)) return null;
  return attribute.initializer && ts.isStringLiteral(attribute.initializer)
    ? attribute.initializer.text
    : null;
}

function controlLabelHint(
  node: ts.JsxOpeningElement | ts.JsxSelfClosingElement,
  source: ts.SourceFile,
) {
  const attributes = node.attributes.properties;
  const explicit =
    literalAttribute(attributes, "aria-label") ??
    literalAttribute(attributes, "ariaLabel") ??
    literalAttribute(attributes, "title");
  if (explicit) return explicit;
  if (!ts.isJsxOpeningElement(node) || !ts.isJsxElement(node.parent)) return null;
  const text = node.parent.children
    .filter(ts.isJsxText)
    .map((child) => child.getText(source))
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
  return text || null;
}

function auditControls(root: string): ControlFinding[] {
  const findings: ControlFinding[] = [];
  for (const file of sourceFiles(join(root, "src"))) {
    const content = readFileSync(file, "utf8");
    const source = ts.createSourceFile(
      file,
      content,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const inspect = (node: ts.Node) => {
      if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
        const tag = node.tagName.getText(source);
        const names = new Set(node.attributes.properties.map(attributeName));
        const isRenderedControl = ["button", "Button", "input", "select", "textarea"].includes(tag);
        const isHonestStateAction = tag === "HonestState" && names.has("onAction");
        if (isRenderedControl || isHonestStateAction) {
          const type = literalAttribute(node.attributes.properties, "type");
          const wired = [...names].some((name) => /^on[A-Z]/.test(name));
          const honestButtonDefault = tag === "Button" && !wired && type !== "submit";
          const disabled =
            names.has("disabled") ||
            names.has("aria-disabled") ||
            honestButtonDefault;
          const disabledWithReason =
            disabled &&
            (honestButtonDefault ||
              names.has("title") ||
              names.has("aria-describedby") ||
              names.has("data-disabled-reason"));
          const classification = wired
            ? "wired"
            : type === "submit"
              ? "submit"
              : disabledWithReason
                ? "disabled-with-reason"
                : disabled
                  ? "disabled-without-reason"
                  : "review";
          const relativeFile = relative(root, file).replaceAll("\\", "/");
          const contractScope = [
            "src/canonical/",
            "src/studios/",
            "src/app/experience/",
          ].some((prefix) => relativeFile.startsWith(prefix));
          findings.push({
            file: relativeFile,
            line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1,
            tag,
            actionId:
              literalAttribute(node.attributes.properties, "data-action-id") ??
              literalAttribute(node.attributes.properties, "actionId"),
            hasActionIdAttribute:
              names.has("data-action-id") || names.has("actionId"),
            labelHint: controlLabelHint(node, source),
            classification,
            contractScope,
            requiresActionId:
              contractScope &&
              (classification === "wired" || classification === "submit"),
          });
        }
      }
      ts.forEachChild(node, inspect);
    };
    inspect(source);
  }
  return findings;
}

const root = process.cwd();
const controls = auditControls(root);
const knownUrls = [...new Set([
  ...Object.values(TAB_PATHS),
  ...STITCH_SCREENS.map((screen) => screen.route),
])].sort();
const routeEvidence = knownUrls.map((url) => ({
  url,
  matches: matchingRoutesForPath(url).map((route) => route.routeId),
  owner: routeForPath(url)?.owner ?? null,
}));
const coveredActionIds = new Set(
  controls.flatMap((control) => (control.actionId ? [control.actionId] : [])),
);
const executableWithoutActionId = controls.filter(
  (control) => control.requiresActionId && !control.hasActionIdAttribute,
);
const missingActionIds = EXPERIENCE_ACTIONS.map((action) => action.actionId).filter(
  (actionId) => !coveredActionIds.has(actionId),
);
const registeredActionIds = new Set(
  EXPERIENCE_ACTIONS.map((action) => action.actionId),
);
const unregisteredActionIds = [...coveredActionIds].filter(
  (actionId) => !registeredActionIds.has(actionId),
);
const summary = {
  generatedAt: new Date().toISOString(),
  scope: "static baseline; review findings are triage, not proof of a dead control",
  routes: {
    registryEntries: ROUTE_REGISTRY.length,
    knownUrls: knownUrls.length,
    registryIssues: validateRouteRegistry(),
    orphanKnownUrls: routeEvidence.filter((route) => route.matches.length === 0).length,
    conflictingKnownUrls: routeEvidence.filter((route) => route.matches.length > 1).length,
    byOwner: Object.fromEntries(
      ["canonical", "product-surface", "legacy"].map((owner) => [
        owner,
        routeEvidence.filter((route) => route.owner === owner).length,
      ]),
    ),
  },
  controls: {
    total: controls.length,
    wired: controls.filter((control) => control.classification === "wired").length,
    submit: controls.filter((control) => control.classification === "submit").length,
    disabledWithReason: controls.filter(
      (control) => control.classification === "disabled-with-reason",
    ).length,
    disabledWithoutReason: controls.filter(
      (control) => control.classification === "disabled-without-reason",
    ).length,
    requiresReview: controls.filter((control) => control.classification === "review").length,
    withActionId: controls.filter((control) => control.hasActionIdAttribute).length,
    withLiteralActionId: controls.filter((control) => control.actionId).length,
    withDynamicActionId: controls.filter(
      (control) => control.hasActionIdAttribute && !control.actionId,
    ).length,
    executableInContractScope: controls.filter(
      (control) => control.requiresActionId,
    ).length,
    withoutActionIdInContractScope: executableWithoutActionId.length,
  },
  actionCoverage: {
    contractActions: EXPERIENCE_ACTIONS.length,
    coveredActionIds: [...coveredActionIds].sort(),
    missingActionIds,
    unregisteredActionIds: unregisteredActionIds.sort(),
  },
  routeEvidence,
  controlEvidence: controls,
  executableWithoutActionId,
  reviewControls: controls.filter((control) => control.classification === "review"),
  disabledWithoutReason: controls.filter(
    (control) => control.classification === "disabled-without-reason",
  ),
};

const outputArgument = process.argv
  .slice(2)
  .find((argument) => !argument.startsWith("--"));
const output = resolve(
  root,
  outputArgument || "docs/studios/evidence/CX_ROUTE_ACTION_BASELINE.json",
);
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ output: relative(root, output), ...summary.routes, controls: summary.controls }, null, 2));
if (missingActionIds.length > 0) {
  console.error(`Missing executable coverage for action contracts: ${missingActionIds.join(", ")}`);
  process.exitCode = 1;
}
if (summary.controls.disabledWithoutReason > 0) {
  console.error(
    `${summary.controls.disabledWithoutReason} disabled controls are missing an explicit reason.`,
  );
  process.exitCode = 1;
}
if (process.argv.includes("--strict") && executableWithoutActionId.length > 0) {
  console.error(
    `${executableWithoutActionId.length} executable controls in the canonical contract scope are missing actionId.`,
  );
  process.exitCode = 1;
}
if (process.argv.includes("--strict") && unregisteredActionIds.length > 0) {
  console.error(
    `Controls reference unregistered actionIds: ${unregisteredActionIds.join(", ")}`,
  );
  process.exitCode = 1;
}
