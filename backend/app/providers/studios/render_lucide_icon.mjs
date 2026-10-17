import fs from "node:fs";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as icons from "lucide-react";

const [name, destination, appearance = "card", requestedColor = "#f8fafc"] = process.argv.slice(2);
if (!/^#[0-9a-fA-F]{6}$/.test(requestedColor)) {
  throw new Error("procedural_icon_color_invalid");
}
const allowed = new Set([
  "AudioWaveform",
  "CircleDot",
  "CirclePlay",
  "Lightbulb",
  "MessageCircle",
  "Monitor",
  "Network",
  "PanelsTopLeft",
  "Smartphone",
  "Tablet",
  "Sparkles",
  "UserRoundCheck",
  "Users",
]);
if (!allowed.has(name) || !destination || !icons[name]) {
  throw new Error("procedural_icon_not_allowed");
}
const glyph = renderToStaticMarkup(
  React.createElement(icons[name], {
    x: 192,
    y: 192,
    width: 640,
    height: 640,
    color: requestedColor,
    strokeWidth: 1.65,
    "aria-hidden": "true",
  }),
);
const backdrop = appearance === "transparent" ? "" : `
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#152b3b"/><stop offset="1" stop-color="#0a1722"/></linearGradient></defs>
  <rect x="32" y="32" width="960" height="960" rx="220" fill="url(#bg)"/>
  <circle cx="785" cy="228" r="118" fill="#38bdf8" opacity="0.16"/>
  <circle cx="248" cy="805" r="156" fill="#f97316" opacity="0.13"/>`;
const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  ${backdrop}
  ${glyph}
</svg>`;
fs.writeFileSync(destination, svg, "utf8");
