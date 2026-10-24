import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const files = [
  "src/canonical/canonical.css",
  "src/canonical/feedback.css",
  "src/design-system/lab.css",
];

type Violation = {
  file: string;
  line: number;
  declaration: string;
};

const violations: Violation[] = [];

for (const relativeFile of files) {
  const absoluteFile = path.join(root, relativeFile);
  const source = fs.readFileSync(absoluteFile, "utf8");
  const lines = source.split(/\r?\n/);

  lines.forEach((line, index) => {
    const declarations = [
      ...line.matchAll(/font-size:\s*([0-9.]+)px/gi),
      ...line.matchAll(/font:\s*(?:[1-9]00\s+)?([0-9.]+)px(?:[\s/;!]|$)/gi),
    ];

    for (const declaration of declarations) {
      const size = Number(declaration[1]);
      if (size > 0 && size < 12) {
        violations.push({
          file: relativeFile,
          line: index + 1,
          declaration: declaration[0],
        });
      }
    }
  });
}

if (violations.length > 0) {
  console.error("Design contract failed: operational typography below 12px.");
  for (const violation of violations) {
    console.error(
      `- ${violation.file}:${violation.line} (${violation.declaration})`,
    );
  }
  process.exit(1);
}

console.log(
  `Design contract passed: ${files.length} final CSS layers contain no typography below 12px.`,
);
