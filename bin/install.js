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
// Statusline helpers
// ---------------------------------------------------------------------------

function _applyStandaloneStatusline(settingsPath, pythonCmd, oTeamDir) {
  const scriptPath = path.join(oTeamDir, "statusline_standalone.py");
  const newCmd = `${pythonCmd} ${scriptPath}`;

  try {
    _updateSettingsStatusline(settingsPath, newCmd);
    console.log("  ✅ Statusline: O-Team standalone enabled");
    console.log(`     Command: ${newCmd}`);
  } catch (err) {
    console.log(`  ⚠️  Failed to update settings: ${err.message}`);
    console.log(`     Manually set statusLine.command to: ${newCmd}`);
  }
}

function _applyMergeStatusline(settingsPath, currentCmd, pythonCmd, oTeamDir) {
  const extraCmdScript = path.join(oTeamDir, "statusline.py");
  const extraCmdArg = `--extra-cmd "${pythonCmd} ${extraCmdScript}"`;

  // Check if --extra-cmd already present
  if (currentCmd.includes("--extra-cmd")) {
    // Replace existing --extra-cmd
    const newCmd = currentCmd.replace(
      /--extra-cmd\s+"[^"]*"/,
      extraCmdArg
    );
    try {
      _updateSettingsStatusline(settingsPath, newCmd);
      console.log("  ✅ Statusline: merged with claude-hud (replaced existing --extra-cmd)");
    } catch (err) {
      console.log(`  ⚠️  Failed to update settings: ${err.message}`);
    }
  } else {
    // Append --extra-cmd before the closing quote of the bash -c command
    // The claude-hud command ends with: ...index.js"'
    // We need to insert before the final "'
    let newCmd;
    if (currentCmd.includes('index.js"\'')) {
      newCmd = currentCmd.replace(
        'index.js"\'',
        `index.js" ${extraCmdArg}'`
      );
    } else if (currentCmd.includes("index.js'")) {
      newCmd = currentCmd.replace(
        "index.js'",
        `index.js' ${extraCmdArg}`
      );
    } else {
      // Fallback: just append
      newCmd = currentCmd + ` ${extraCmdArg}`;
    }

    try {
      _updateSettingsStatusline(settingsPath, newCmd);
      console.log("  ✅ Statusline: merged with claude-hud");
      console.log("     Pipeline status will appear alongside HUD info.");
    } catch (err) {
      console.log(`  ⚠️  Failed to update settings: ${err.message}`);
      console.log(`     Manually add to your statusLine command: ${extraCmdArg}`);
    }
  }
}

function _updateSettingsStatusline(settingsPath, newCommand) {
  let settings = {};
  if (fs.existsSync(settingsPath)) {
    settings = JSON.parse(fs.readFileSync(settingsPath, "utf-8"));
  }

  // Backup current command
  const prev = settings.statusLine?.command;
  if (prev) {
    if (!settings._o_team_backup) settings._o_team_backup = {};
    settings._o_team_backup.statusLine_command = prev;
  }

  settings.statusLine = {
    type: "command",
    command: newCommand,
  };

  const dir = path.dirname(settingsPath);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + "\n");
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
  // Also remove commands
  const cmdDir = path.join(process.cwd(), ".claude", "commands", "o-team");
  if (fs.existsSync(cmdDir)) {
    fs.rmSync(cmdDir, { recursive: true });
    console.log(`  ✅ Removed commands: ${cmdDir}`);
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

// Copy command files to .claude/commands/o-team/
const COMMANDS_SRC = path.join(TARGET_DIR, "commands");
const COMMANDS_DIR = path.join(process.cwd(), ".claude", "commands", "o-team");

try {
  if (fs.existsSync(COMMANDS_SRC)) {
    fs.mkdirSync(COMMANDS_DIR, { recursive: true });
    for (const file of fs.readdirSync(COMMANDS_SRC)) {
      fs.copyFileSync(
        path.join(COMMANDS_SRC, file),
        path.join(COMMANDS_DIR, file)
      );
    }
    console.log("  ✅ Commands installed to .claude/commands/o-team/");
  }
} catch (err) {
  console.log(`  ⚠️  Failed to install commands: ${err.message}`);
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

// ---------------------------------------------------------------------------
// Statusline setup
// ---------------------------------------------------------------------------

const os = require("os");
const homeDir = os.homedir();
const oTeamDir = path.join(homeDir, ".o-team");
const settingsPath = path.join(homeDir, ".claude", "settings.json");
const pythonCmd = python ? python.cmd : "python3";

// Install statusline scripts to ~/.o-team/
const STATUSLINE_FILES = [
  { src: "statusline.py", desc: "claude-hud extra-cmd" },
  { src: "statusline_standalone.py", desc: "standalone statusline" },
];

try {
  fs.mkdirSync(oTeamDir, { recursive: true });
  for (const f of STATUSLINE_FILES) {
    fs.copyFileSync(
      path.join(TARGET_DIR, "scripts", f.src),
      path.join(oTeamDir, f.src)
    );
  }
  console.log(`  ✅ Statusline scripts installed to ${oTeamDir}`);
} catch (err) {
  console.log(`  ⚠️  Failed to install statusline scripts: ${err.message}`);
}

// Detect current statusline configuration
const statuslineArg = args.find((a) => a.startsWith("--statusline"));
let statuslineChoice = null;
if (statuslineArg) {
  // --statusline=merge or --statusline merge
  statuslineChoice = statuslineArg.includes("=")
    ? statuslineArg.split("=")[1]
    : args[args.indexOf(statuslineArg) + 1];
}

let currentStatusline = null; // "claude-hud", "other", or null
let currentCmd = "";
try {
  if (fs.existsSync(settingsPath)) {
    const settings = JSON.parse(fs.readFileSync(settingsPath, "utf-8"));
    currentCmd = settings.statusLine?.command || "";
    if (currentCmd.includes("claude-hud")) {
      currentStatusline = "claude-hud";
    } else if (currentCmd.trim()) {
      currentStatusline = "other";
    }
  }
} catch {
  // can't read settings
}

// Apply statusline choice
console.log("");

if (statuslineChoice === "o-team") {
  // Option 1: Replace with O-Team standalone
  _applyStandaloneStatusline(settingsPath, pythonCmd, oTeamDir);
} else if (statuslineChoice === "keep") {
  // Option 2: Don't touch
  console.log("  📊 Statusline: kept as-is (--statusline keep)");
  console.log("     Pipeline events will be logged but not shown in status bar.");
} else if (statuslineChoice === "merge") {
  // Option 3: Merge with claude-hud
  if (currentStatusline === "claude-hud") {
    _applyMergeStatusline(settingsPath, currentCmd, pythonCmd, oTeamDir);
  } else {
    console.log("  ⚠️  --statusline merge requires claude-hud, but it was not detected.");
    console.log("     Falling back to O-Team standalone statusline.");
    _applyStandaloneStatusline(settingsPath, pythonCmd, oTeamDir);
  }
} else {
  // No flag — show guidance based on detected setup
  console.log("  📊 Statusline configuration");
  console.log("");

  if (currentStatusline === "claude-hud") {
    const alreadyMerged = currentCmd.includes("--extra-cmd") && currentCmd.includes("o-team");
    if (alreadyMerged) {
      console.log("  ✅ claude-hud with O-Team merge already configured!");
    } else {
      console.log("  Detected: claude-hud (supports merge)");
      console.log("");
      console.log("  Options (re-run install with --statusline <choice>):");
      console.log("    --statusline merge   → Add O-Team status to claude-hud (recommended)");
      console.log("    --statusline o-team  → Replace claude-hud with O-Team statusline");
      console.log("    --statusline keep    → Keep claude-hud as-is, no pipeline status");
    }
  } else if (currentStatusline === "other") {
    console.log("  Detected: existing statusline (not claude-hud, merge not supported)");
    console.log("");
    console.log("  Options (re-run install with --statusline <choice>):");
    console.log("    --statusline o-team  → Replace with O-Team statusline");
    console.log("    --statusline keep    → Keep current statusline (recommended)");
  } else {
    console.log("  Detected: no statusline configured");
    console.log("");
    console.log("  Options (re-run install with --statusline <choice>):");
    console.log("    --statusline o-team  → Enable O-Team statusline (recommended)");
    console.log("    --statusline keep    → Skip statusline setup");
  }
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
