import { chromium } from "playwright";

const routes = {
  s03: "/radar",
  s04: "/radar/opportunities/op-festival",
  s05: "/campaigns/new?opportunity=op-festival",
  s06: "/campaigns/campaign-aurora",
  s15: "/campaigns/campaign-aurora/world",
  s16: "/campaigns/campaign-aurora/moodboard",
  s18: "/brand-memory",
  s23: "/projects",
};

const phase3Routes = {
  s07: "/content",
  s08: "/content/post-ritual/edit?mode=editorial",
  s09: "/content/post-ritual/edit?mode=visual",
  s10: "/approvals/post-ritual?view=creative",
  s17: "/content/post-ritual/edit?mode=carousel",
  s19: "/library/assets",
  s21: "/factory",
};

const phase4Routes = {
  s11: "/calendar",
  s12: "/publish/post-ritual",
  s13: "/content/post-ritual",
  s14: "/content/post-ritual/remix",
  s20: "/analytics/learning",
};

const phase5Routes = {
  s26: "/apps",
  s34: "/content/post-ritual/edit?mode=presenter",
  instagram: "/apps/instagram",
  facebook: "/apps/facebook",
  tiktok: "/apps/tiktok",
  youtube: "/apps/youtube",
  x: "/apps/x",
  linkedin: "/apps/linkedin",
  pinterest: "/apps/pinterest",
  threads: "/apps/threads",
  twitch: "/apps/twitch",
  googleBusinessProfile: "/apps/google-business-profile",
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 1024 } });
await page.addInitScript(() =>
  localStorage.setItem("clicko:splash-seen", "true"),
);

for (const [surface, route] of Object.entries(routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-2-${surface}-1280.png`,
    fullPage: true,
  });
}

for (const [surface, route] of Object.entries(phase3Routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-3-${surface}-1280.png`,
    fullPage: true,
  });
}

for (const [surface, route] of Object.entries(phase4Routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-4-${surface}-1280.png`,
    fullPage: true,
  });
}

for (const [surface, route] of Object.entries(phase5Routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-5-${surface}-1280.png`,
    fullPage: true,
  });
}

await page.setViewportSize({ width: 1440, height: 900 });
for (const [surface, route] of Object.entries(phase4Routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-4-${surface}-1440.png`,
    fullPage: true,
  });
}

for (const [surface, route] of Object.entries(phase5Routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-5-${surface}-1440.png`,
    fullPage: true,
  });
}

await page.setViewportSize({ width: 1536, height: 1024 });
for (const [surface, route] of Object.entries(phase3Routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-3-${surface}-1536.png`,
    fullPage: true,
  });
}

for (const [surface, route] of Object.entries(phase4Routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  await page.screenshot({
    path: `artifacts/visual-validation/phase-4-${surface}-1536.png`,
    fullPage: true,
  });
}

await browser.close();
