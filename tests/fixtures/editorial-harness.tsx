import React from "react";
import { createRoot } from "react-dom/client";
import { EditorialReviewPanel, type EditorialGateState } from "../../src/studios/EditorialReviewPanel";
import type { StudioDocumentRecord } from "../../src/api/productApi";

// Test-only component host, served by Vite in the isolated Playwright environment.
export function mountEditorialHarness(record: StudioDocumentRecord) {
  const host = document.createElement("div");
  host.id = "editorial-harness";
  host.style.cssText = "position:fixed;inset:0;z-index:99999;overflow:auto;background:#151b20;color:#fff;padding:16px;box-sizing:border-box;font-family:Arial,sans-serif;";
  document.body.append(host);
  const root = createRoot(host);
  let gate: EditorialGateState | undefined;
  function update(next: StudioDocumentRecord) {
    root.render(<div key={`${next.documentId}:${next.revision}`} style={{ maxWidth: 480, margin: "auto" }}>
      <EditorialReviewPanel document={next} active disabled={false} onGateChange={(state) => { gate = state; }} />
    </div>);
  }
  update(record);
  return { update, getGate: () => gate, dispose: () => { root.unmount(); host.remove(); } };
}
