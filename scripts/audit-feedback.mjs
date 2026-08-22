import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "playwright";

const routes = {
  home: "/dashboard",
  homeHorizonte: "/dashboard?brand=horizonte",
  projects: "/projects",
  projectsHorizonte: "/projects?brand=horizonte",
  content: "/content",
  library: "/library/assets",
  editorial: "/content/post-ritual/edit?mode=editorial",
  visual: "/content/post-ritual/edit?mode=visual",
  calendar: "/calendar",
  factory: "/factory",
  factoryHorizonte: "/factory?brand=horizonte",
  apps: "/apps",
  instagram: "/apps/instagram",
  presenter: "/content/post-ritual/edit?mode=presenter",
};

const outputDirectory = "artifacts/feedback-audit";
const label = process.argv[2] || "current";
const viewportWidth = Number(process.argv[3] || 1280);
const viewportHeight = viewportWidth >= 1440 ? 900 : 800;
await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: viewportWidth, height: viewportHeight },
});
await page.addInitScript(() =>
  localStorage.setItem("clicko:splash-seen", "true"),
);

const report = {};
for (const [name, route] of Object.entries(routes)) {
  await page.goto(`http://127.0.0.1:3000${route}`, {
    waitUntil: "networkidle",
  });
  report[name] = await page.evaluate(() => {
    const root = document.querySelector(".cx-product") || document.body;
    const visible = [...root.querySelectorAll("*")].filter((element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none" && rect.width > 0 && rect.height > 0;
    });
    const overflowers = visible
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.right > innerWidth + 1 || rect.left < -1;
      })
      .slice(0, 15)
      .map((element) => ({
        selector: `${element.tagName.toLowerCase()}.${[...element.classList].join(".")}`,
        left: Math.round(element.getBoundingClientRect().left),
        right: Math.round(element.getBoundingClientRect().right),
      }));
    const tinyText = visible.filter((element) => {
      const text = element.textContent?.trim();
      const fontSize = Number.parseFloat(getComputedStyle(element).fontSize);
      return text && element.children.length === 0 && fontSize < 10;
    }).length;
    return {
      viewport: innerWidth,
      rootClientWidth: root.clientWidth,
      rootScrollWidth: root.scrollWidth,
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
      overflowers,
      tinyText,
    };
  });
  await page.screenshot({
    path: `${outputDirectory}/${name}-${viewportWidth}-${label}.png`,
    fullPage: true,
  });
}

await writeFile(
  `${outputDirectory}/${label}.json`,
  `${JSON.stringify(report, null, 2)}\n`,
);
await browser.close();
console.log(JSON.stringify(report, null, 2));
