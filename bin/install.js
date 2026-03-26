#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const SKILL_NAME = "o-team";
const SKILL_SRC = path.join(__dirname, "..", "skill");
const TARGET_DIR = path.join(process.cwd(), ".claude", "skills", SKILL_NAME);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function copyRecursive(src, dest) {
  if (!fs.existsSync(src)) return;

  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      // Skip __pycache__
      if (entry === "__pycache__") continue;
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    fs.copyFileSync(src, dest);
  }
}

function checkPython() {
  const cmds = ["python3", "python"];
  for (const cmd of cmds) {
    try {
      const version = execSync(`${cmd} --version 2>&1`, { encoding: "utf8" }).trim();
      return { cmd, version };
    } catch {
      // try next
    }
  }
  return null;
}

function checkPyYAML(pythonCmd) {
  try {
    execSync(`${pythonCmd} -c "import yaml" 2>&1`, { encoding: "utf8" });
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);
const isUninstall = args.includes("--uninstall") || args.includes("uninstall");

console.log("");
console.log("  O-Team CLI — Multi-team AI Agent Pipeline Orchestrator");
console.log("  ======================================================");
console.log("");

if (isUninstall) {
  if (fs.existsSync(TARGET_DIR)) {
    fs.rmSync(TARGET_DIR, { recursive: true });
    console.log(`  ✅ Removed: ${TARGET_DIR}`);
  } else {
    console.log(`  ⚠️  Not installed at: ${TARGET_DIR}`);
  }
  console.log("");
  process.exit(0);
}

// Check if already installed
if (fs.existsSync(TARGET_DIR)) {
  const existingSkill = path.join(TARGET_DIR, "SKILL.md");
  if (fs.existsSync(existingSkill)) {
    console.log(`  ⚠️  O-Team skill already exists at: ${TARGET_DIR}`);
    console.log("");

    if (args.includes("--force") || args.includes("-f")) {
      console.log("  --force detected, overwriting...");
      fs.rmSync(TARGET_DIR, { recursive: true });
    } else {
      console.log("  Use --force to overwrite, or --uninstall to remove.");
      console.log("");
      process.exit(1);
    }
  }
}

// Copy skill files
console.log(`  Installing to: ${TARGET_DIR}`);
console.log("");

try {
  copyRecursive(SKILL_SRC, TARGET_DIR);
  console.log("  ✅ Skill files installed");
} catch (err) {
  console.error(`  ❌ Failed to copy files: ${err.message}`);
  process.exit(1);
}

// Check Python
const python = checkPython();
if (python) {
  console.log(`  ✅ Python found: ${python.version}`);

  if (checkPyYAML(python.cmd)) {
    console.log("  ✅ PyYAML installed");
  } else {
    console.log("  ⚠️  PyYAML not found. Install with:");
    console.log(`     ${python.cmd} -m pip install pyyaml`);
  }
} else {
  console.log("  ⚠️  Python not found. Install Python 3.10+ to use O-Team CLI.");
}

// Check Claude CLI
try {
  execSync("claude --version 2>&1", { encoding: "utf8" });
  console.log("  ✅ Claude Code CLI found");
} catch {
  console.log("  ⚠️  Claude Code CLI not found. Install from:");
  console.log("     https://docs.anthropic.com/en/docs/claude-code");
}

// Done
console.log("");
console.log("  ────────────────────────────────────────");
console.log("  Installation complete!");
console.log("");
console.log("  Quick start:");
console.log("    1. claude                              # Start Claude Code");
console.log("    2. /o-team:registry add ./teams        # Register teams");
console.log("    3. /o-team:build                       # Build pipeline");
console.log("    4. /o-team:run my-pipeline             # Run it");
console.log("  ────────────────────────────────────────");
console.log("");
