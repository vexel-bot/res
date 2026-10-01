import React from "react";
import { createRoot } from "react-dom/client";
import { ContextualEditingPanel } from "../../src/studios/ContextualEditingPanel";
import type { StudioDocumentRecord } from "../../src/api/productApi";
import "../../src/studios/video-studio.css";

export function mountContextualHarness(record: StudioDocumentRecord) {
  const host = document.createElement("div");
  host.className = "vs-shell";
  host.style.cssText = "position:fixed;inset:0;z-index:99999;overflow:auto;padding:24px;background:white;color:#111;";
  document.body.append(host);
  const root = createRoot(host);
  const renders: { documentId: string; planId: string }[] = [];
  function update(value: StudioDocumentRecord) {
    root.render(<div className="vs-inspector-body" style={{ maxWidth: 500, margin: "auto" }}>
      <ContextualEditingPanel document={value} disabled={false}
        onRender={async (doc, planId) => { renders.push({ documentId: doc.documentId, planId }); }} />
    </div>);
  }
  update(record);
  return { update, renders, dispose: () => { root.unmount(); host.remove(); } };
}
