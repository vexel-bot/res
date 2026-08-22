import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

const approvedRoutes = {
  s01: "/dashboard",
  s02: "/dashboard?create=open",
  s03: "/radar",
  s04: "/radar/opportunities/op-festival",
  s05: "/campaigns/new?opportunity=op-festival",
  s06: "/campaigns/campaign-aurora",
  s07: "/content",
  s08: "/content/post-ritual/edit?mode=editorial",
  s09: "/content/post-ritual/edit?mode=visual",
  s10: "/approvals/post-ritual?view=creative",
  s11: "/calendar",
  s12: "/publish/post-ritual",
  s13: "/content/post-ritual",
  s14: "/content/post-ritual/remix",
  s15: "/campaigns/campaign-aurora/world",
  s16: "/campaigns/campaign-aurora/moodboard",
  s17: "/content/post-ritual/edit?mode=carousel",
  s18: "/brand-memory",
  s19: "/library/assets",
  s20: "/analytics/learning",
  s21: "/factory",
  s22: "/dashboard?spotlight=open",
  s23: "/projects",
  s24: "/dashboard?activity=open",
  s25: "/dashboard?workspace=menu",
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

const outputDirectory = "artifacts/visual-validation/final-approved";
await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage();
await page.addInitScript(() =>
  localStorage.setItem("clicko:splash-seen", "true"),
);

for (const viewport of [
  { width: 1280, height: 1024 },
  { width: 1440, height: 900 },
]) {
  await page.setViewportSize(viewport);
  for (const [surface, route] of Object.entries(approvedRoutes)) {
    await page.goto(`http://127.0.0.1:3000${route}`, {
      waitUntil: "networkidle",
    });
    await page.screenshot({
      path: `${outputDirectory}/${surface}-${viewport.width}.png`,
      fullPage: true,
    });
  }
}

await browser.close();
