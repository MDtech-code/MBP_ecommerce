import fs from "fs";
import path from "path";
import process from "process";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, "../src");

// FSD Layer hierarchy (Index 0 is highest, Index 5 is lowest)
const LAYER_HIERARCHY = [
  "app",
  "pages",
  "widgets",
  "features",
  "entities",
  "shared",
];

// Regex to find import/export statements
const IMPORT_REGEX =
  /(?:import|export)\s+(?:[^'"]*\s+from\s+)?['"]([^'"]+)['"]/g;

let totalFilesChecked = 0;
let totalViolations = 0;

const colors = {
  reset: "\x1b[0m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  green: "\x1b[32m",
  cyan: "\x1b[36m",
  bold: "\x1b[1m",
};

function getLayerIndex(layerName) {
  return LAYER_HIERARCHY.indexOf(layerName);
}

function scanDirectory(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      scanDirectory(fullPath);
    } else if (entry.isFile() && /\.(js|jsx|ts|tsx)$/.test(entry.name)) {
      checkFile(fullPath);
    }
  }
}

function checkFile(filePath) {
  totalFilesChecked++;
  const content = fs.readFileSync(filePath, "utf-8");
  const relativePath = path.relative(SRC_DIR, filePath);

  // Determine current layer of the file
  const pathParts = relativePath.split(path.sep);
  const currentLayer = pathParts[0];
  const currentSlice = pathParts[1];

  if (!LAYER_HIERARCHY.includes(currentLayer)) return;
  const currentLayerIdx = getLayerIndex(currentLayer);

  let match;
  while ((match = IMPORT_REGEX.exec(content)) !== null) {
    const importPath = match[1];

    // Check Alias Imports (e.g., @features/auth, @entities/user/model)
    if (importPath.startsWith("@")) {
      const aliasParts = importPath.split("/");
      const importedLayer = aliasParts[0].replace("@", "");
      const importedSlice = aliasParts[1];

      if (!LAYER_HIERARCHY.includes(importedLayer)) continue;
      const importedLayerIdx = getLayerIndex(importedLayer);

      // RULE 1: The Hierarchy Law (Cannot import from same layer or above, except shared)
      if (importedLayerIdx <= currentLayerIdx && currentLayer !== "shared") {
        // Exception: App layer files can import from other app configs
        if (!(currentLayer === "app" && importedLayer === "app")) {
          reportViolation(
            filePath,
            importPath,
            `[Hierarchy Violation] '${currentLayer}' layer cannot import from '${importedLayer}' layer.`,
          );
        }
      }

      // RULE 2: The Cross-Feature Law (Features cannot import other features)
      if (
        currentLayer === "features" &&
        importedLayer === "features" &&
        currentSlice !== importedSlice
      ) {
        reportViolation(
          filePath,
          importPath,
          `[Cross-Feature Violation] Feature '${currentSlice}' cannot import directly from feature '${importedSlice}'.`,
        );
      }

      // RULE 3: The Public API Law (No deep imports into slices)
      // e.g., @features/auth/model/useLoginForm is illegal (length > 2)
      // Note: @shared sub-groups like @shared/ui/Button are handled differently, but let's flag > 2 for standard slices
      if (importedLayer !== "shared" && aliasParts.length > 2) {
        reportViolation(
          filePath,
          importPath,
          `[Deep Import Violation] Must import from slice root barrel ('@${importedLayer}/${importedSlice}'), not internal folders.`,
        );
      }
    }

    // RULE 4: Relative upward leaks across layers (e.g., ../../../features/auth)
    if (importPath.startsWith("../")) {
      const resolvedImport = path.resolve(path.dirname(filePath), importPath);
      const relToSrc = path.relative(SRC_DIR, resolvedImport);
      const targetLayer = relToSrc.split(path.sep)[0];

      if (
        LAYER_HIERARCHY.includes(targetLayer) &&
        targetLayer !== currentLayer
      ) {
        reportViolation(
          filePath,
          importPath,
          `[Relative Cross-Layer Leak] Use path aliases ('@${targetLayer}/...') instead of relative paths across layer boundaries.`,
        );
      }
    }
  }
}

function reportViolation(filePath, importPath, reason) {
  totalViolations++;
  const shortPath = path.relative(process.cwd(), filePath);
  console.log(
    `${colors.red}${colors.bold}✖ Violation in: ${colors.cyan}${shortPath}${colors.reset}`,
  );
  console.log(`  ${colors.yellow}Import:${colors.reset} "${importPath}"`);
  console.log(`  ${colors.bold}Reason:${colors.reset} ${reason}\n`);
}

console.log(
  `${colors.bold}🔍 Starting Feature-Sliced Design Architecture Audit...${colors.reset}\n`,
);
scanDirectory(SRC_DIR);

console.log(
  `${colors.bold}── Audit Summary ───────────────────────────${colors.reset}`,
);
console.log(
  `Files Analyzed: ${colors.cyan}${totalFilesChecked}${colors.reset}`,
);
if (totalViolations === 0) {
  console.log(
    `${colors.green}${colors.bold}✔ Zero architectural violations found! Workspace is clean.${colors.reset}\n`,
  );
  process.exit(0);
} else {
  console.log(
    `Total Violations Found: ${colors.red}${colors.bold}${totalViolations}${colors.reset}`,
  );
  console.log(
    `${colors.yellow}Tip: Use your IDE's global search/replace with the regex patterns from Part 2 to fix deep imports quickly.${colors.reset}\n`,
  );
  process.exit(1);
}
