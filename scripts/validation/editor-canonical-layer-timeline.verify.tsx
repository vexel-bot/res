import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CanonicalLayerTimeline } from "../../src/studios/CanonicalLayerTimeline";
import type { StudioDocumentRecord } from "../../src/api/productApi";

const output = "output/visual-directed-native14-20261004/";
const render = (document: StudioDocumentRecord, frame = 449) => renderToStaticMarkup(
  <CanonicalLayerTimeline document={document} frame={frame} onSeek={() => {}} onSelect={() => {}} />,
);
for (const key of ["organization-a", "comparison-a", "interface-a"]) {
  const document = JSON.parse(readFileSync(`${output}${key}-render.json`, "utf8")).snapshot as StudioDocumentRecord;
  const original = JSON.stringify(document);
  const html = render(document);
  assert.match(html, /aria-valuemax="449"/);
  assert.match(html, /aria-valuenow="449"/);
  assert.doesNotMatch(html, /TAKE|Ajustar início|Ajustar fim|data-clip-id="demo"/);
  assert.equal((html.match(/data-layer-id=/g) ?? []).length, document.composition.pages.flatMap(p => p.layers).length);
  if (key === "interface-a") {
    assert.match(html, /Inspecionar capture · frames \[0, 285\)/);
    assert.match(html, /Inspecionar capture-result · frames \[285, 450\)/);
    assert.match(html, /data-source-start-seconds="9.5"/);
  }
  assert.match(render(document, 450), /aria-valuenow="449"/);
  const invalid = structuredClone(document);
  const properties = invalid.composition.pages[0].layers[0].properties as Record<string, unknown>;
  properties.editorialTiming = { startFrame: 449, durationFrames: 2, fps: 30 };
  assert.match(render(invalid), /Intervalo ausente ou incompatível/);
  properties.editorialTiming = { startFrame: 0, durationFrames: 450, fps: 24 };
  assert.match(render(invalid), /Intervalo ausente ou incompatível/);
  delete properties.editorialTiming;
  assert.match(render(invalid), /Intervalo ausente ou incompatível/);
  assert.equal(JSON.stringify(document), original, "Projection must not mutate the canonical document");
}
console.log("Three retained real snapshots: canonical bounds, source cut, read-only controls, invalid timing guards and no mutation passed. SSR guards only; browser proof is separate.");
