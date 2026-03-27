# O-Team CLI (Agent Office)

```
   ___        _____
  / _ \      |_   _|__  __ _ _ __ ___
 | | | |_____  | |/ _ \/ _` | '_ ` _ \
 | |_| |_____| | |  __/ (_| | | | | | |
  \___/        |_|\___|\__,_|_| |_| |_|
                Agent Office
```

### Complex Tasks. Independent Contexts. Human Oversight. — All from the Terminal.

> **A-Team builds the offices. O-Team CLI makes them run like a company — no browser required.**

**[English](#english)** | **[繁體中文](#繁體中文)**

### Quick Start

```bash
# Install
cd your-project
npx github:chemistrywow31/O-Team

# Optional: set up statusline (choose one)
npx github:chemistrywow31/O-Team --force --statusline merge    # claude-hud users
npx github:chemistrywow31/O-Team --force --statusline o-team   # no existing statusline
```

```bash
# Use in Claude Code
claude

/o-team:registry add ./teams     # Register your A-Team agent teams
/o-team:build                    # Build a pipeline interactively
/o-team:run my-pipeline          # Run it
/o-team:config                   # Configure statusline & language
```

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  A-Team #1  │───▶│  A-Team #2  │───▶│  A-Team #3  │───▶│  A-Team #4  │
│  Research   │    │  Design     │    │  Writing    │    │  QA Review  │
│ output.md ──│───▶│── input.md  │    │ output.md ──│───▶│── input.md  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       Each node = independent claude process with fresh context
```

---

<a id="english"></a>

## English

O-Team CLI is a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that chains multiple AI agent teams into sequential pipelines. Each team runs as an independent `claude` process with its own fresh context window, passing only structured `output.md → input.md` handoffs to the next. Human review gates at configurable nodes ensure output quality — all without leaving the terminal.

### The Problem

Running a single AI agent on a focused task works well. But real-world projects need **multiple specialized teams** working in sequence — research, design, implementation, review. When you try to do this in a single AI session:

- **Context degrades** — the AI loses focus as the conversation grows longer
- **Mistakes compound** — one bad output pollutes everything downstream
- **No checkpoints** — you can't review, adjust, or intervene mid-process

### The Solution

O-Team CLI treats each AI agent team as an independent office. Like departments in a company, each office:

- **Works in isolation** — every node spawns a separate `claude -p` process with its own full context window and team-specific `CLAUDE.md` + `.claude/` configuration
- **Hands off results deliberately** — nodes exchange only `output.md → input.md` files, not conversation history
- **Reports to management** — `gate` mode pauses execution for human review: approve, reject, edit the output, or abort

The result: multi-team AI pipelines where quality doesn't degrade as complexity grows.

### How It Connects to A-Team

[A-Team](https://github.com/chemistrywow31/A-Team) generates specialized AI agent team folders — each containing a `CLAUDE.md` definition and `.claude/agents/` with role-specific agents.

O-Team CLI **consumes** these team folders and lets you register, build pipelines, run them with automatic handoff, and review outputs at gate nodes.

### Features

#### Team Registry
- **Register** agent teams by local path — single folder or entire directory
- **Auto-detect** team structure: parses `CLAUDE.md`, counts agents/skills/rules, finds coordinator
- **Validate** path integrity: CLAUDE.md existence, `.claude/` structure, agent definitions
- **AI-powered summaries** — Claude reads each team's configuration and generates capability descriptions
- **Global registry** at `~/.o-team/registry.json` — register once, use across projects

#### Pipeline Builder (`/o-team:build`)
- **Select and order** registered teams by number — no YAML editing required
- **Choose execution mode** per node: `auto` (proceed immediately) or `gate` (pause for review)
- **AI-generated prompts** — provide the objective and first node's prompt, Opus cascades prompts for all downstream nodes based on each team's `CLAUDE.md` capabilities
- **Review before saving** — all generated prompts shown for confirmation/modification
- **Pipeline YAML** — saved to `.o-team/pipelines/`, version-controllable

#### Execution Engine (`/o-team:run`)
- **UUID sandbox isolation** — each run creates a unique workspace; concurrent runs don't interfere
- **Office folder model** — each node gets its own directory with a complete copy of the team's `CLAUDE.md` + `.claude/` configuration
- **Independent context** — each node spawns a separate `claude -p` process from its office folder, loading only that team's identity
- **Stream JSON events** — uses `--output-format stream-json --verbose` to receive structured events from each node process (see [Statusline](#statusline))
- **Automatic handoff** — `output.md` from completed nodes copies to the next node's `input.md`
- **Shared workspace** — `workspace/` directory persists across all nodes for shared files
- **Audit trail** — every node's assembled `prompt.md`, `run.log`, and raw `events.jsonl` are preserved

#### Human Review Gates
- **approve** — accept output, continue to next node
- **reject** — discard output, re-execute the node
- **edit** — modify `output.md` directly, then continue
- **skip** — skip this node, pass input through to next
- **abort** — cancel the entire pipeline

#### Run Management
- **Status** — check any run's current state and per-node progress
- **History** — list all runs with state, progress, timestamps
- **Clean** — remove specific runs or bulk clean by state
- **Resume** — resume paused or errored runs from where they stopped

---

### Commands

| Command | Description |
|---------|-------------|
| `/o-team:registry add <path>` | Register team folder(s) |
| `/o-team:registry list` | List registered teams |
| `/o-team:registry remove <slug>` | Remove a registered team |
| `/o-team:build` | Build a named pipeline interactively |
| `/o-team:run <pipeline-name>` | Execute a pipeline |
| `/o-team:status <run-id>` | Check run status |
| `/o-team:runs` | List run history |
| `/o-team:clean [run-id]` | Clean up run directories |
| `/o-team:config` | Interactive settings (statusline, language) |

---

### Statusline

O-Team integrates with the Claude Code status bar to show real-time pipeline execution status. During a run, you can see which node is active, what tool is being used, and agent activity — all in the bottom bar of your terminal.

#### How It Works

```
claude -p --output-format stream-json --verbose
    │
    ▼  (newline-delimited JSON events)
stream_parser.py ─── parse events ──┬── display track (text, tool_use, result)
                                    └── agent track (spawn, progress, complete)
    │
    ├── events.jsonl    (raw event archive, per node)
    ├── run.log         (parsed text + tool log)
    └── ~/.o-team/status.json (global status file)
            │
            ▼
     statusline script ── read & format
            │
            ▼
     Claude Code status bar
```

The execution engine parses four event types from `claude -p --output-format stream-json --verbose`:

| Event type | Subtype | What it contains |
|-----------|---------|-----------------|
| `system` | `init`, `task_started`, `task_progress`, `task_notification` | Session lifecycle, agent spawns, agent progress |
| `assistant` | — | Content blocks: `text` (LLM output) and `tool_use` (tool invocations) |
| `result` | `success`, `error` | Final result, duration, cost, turn count |

These are parsed into a `StatusSnapshot` that tracks the current phase (`running`, `tool`, `agent`, `complete`, `error`), which tool or agent is active, and cost/duration metrics.

#### Status Display Format

When a pipeline is running, the status bar shows:

```
O [1/3] 01-research Read            ← node is using the Read tool
O [2/3] 02-design Agent:explore     ← node spawned an agent
O [3/3] 03-review ...               ← node is thinking
O [3/3] 03-review Done(45s,$0.03)   ← node completed
```

When no pipeline is running, nothing extra is shown.

#### Statusline Compatibility

Claude Code supports **only one** `statusLine.command` in `settings.json`. There is no native way to compose multiple statusline tools. O-Team provides three configuration modes to handle this:

| Mode | Flag / Config | Behavior |
|------|--------------|----------|
| **O-Team standalone** | `--statusline o-team` | Replaces existing statusline. Shows basic session info + pipeline status. |
| **Keep existing** | `--statusline keep` | Does not touch statusline. Events are logged to `events.jsonl` and `run.log` but not shown in the bar. |
| **Merge with claude-hud** | `--statusline merge` | Adds O-Team status alongside claude-hud via its `--extra-cmd` mechanism. |

**Merge is only supported with [claude-hud](https://github.com/jarrodwatts/claude-hud)** (13.8k stars), which is the only statusline tool that provides an extensibility mechanism (`--extra-cmd`). Other tools (ccusage, ccstatusline, CCometixLine, claude-powerline, etc.) do not support composition.

| If you have... | Recommended mode |
|----------------|-----------------|
| No statusline | `o-team` (enables pipeline status) |
| claude-hud | `merge` (keeps HUD + adds pipeline status) |
| Other statusline tool | `keep` (don't break existing setup) |

#### Configuring Statusline

**Option A: During installation**

```bash
npx github:chemistrywow31/O-Team --statusline merge   # Merge with claude-hud
npx github:chemistrywow31/O-Team --statusline o-team   # Use O-Team standalone
npx github:chemistrywow31/O-Team --statusline keep     # Don't touch statusline
```

If you omit `--statusline`, the installer detects your current setup and shows recommended options without making changes.

**Option B: Interactive configuration**

```
/o-team:config
```

This opens an interactive settings flow using Claude Code's AskUserQuestion interface. It detects your current statusline, presents appropriate options, and applies your choice.

**Option C: Manual**

For O-Team standalone:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.o-team/statusline_standalone.py"
  }
}
```

For claude-hud merge, append to your existing claude-hud command:
```
--extra-cmd "python3 ~/.o-team/statusline.py"
```

#### Statusline Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `statusline.py` | `~/.o-team/statusline.py` | For claude-hud `--extra-cmd`. Outputs `{"label": "..."}` JSON. |
| `statusline_standalone.py` | `~/.o-team/statusline_standalone.py` | Standalone statusline. Reads Claude Code stdin JSON + pipeline status. |

Both scripts read `~/.o-team/status.json`, which is written by the execution engine during pipeline runs. The file is automatically deleted when the pipeline completes, pauses, or errors. A 60-second staleness check prevents ghost status from crashed runs.

#### Safety

- When `--statusline merge` or `--statusline o-team` modifies `settings.json`, the previous `statusLine.command` is backed up to `settings._o_team_backup.statusLine_command`
- `/o-team:config` offers a "Restore" option to revert to the backed-up command
- `--statusline keep` never touches `settings.json`

---

### Internationalization (i18n)

O-Team supports **English** and **Traditional Chinese (繁體中文)**.

#### Language Detection

Language is detected in priority order:

1. `~/.o-team/config.json` → `"language"` field (user override via `/o-team:config`)
2. `~/.claude/settings.json` → `"language"` field (Claude Code setting)
3. System `LANG` / `LC_ALL` environment variable
4. Fallback: English

#### Switching Language

**Via interactive config:**

```
/o-team:config → Language / 語系 → select
```

**Via command line:**

```bash
cd your-project/.claude/skills/o-team
python -m scripts.config set-language zh-TW --json   # 繁體中文
python -m scripts.config set-language en --json       # English
```

**Via manual edit:**

```json
// ~/.o-team/config.json
{
  "language": "zh-TW"
}
```

#### Scope

| Component | i18n applied |
|-----------|-------------|
| `/o-team:config` UI (AskUserQuestion options) | Yes — translated via `i18n.t()` |
| Claude's response text | Yes — SKILL.md instructs Claude to match detected locale |
| Pipeline execution output (node headers, status) | Yes — via `i18n.t()` |
| Statusline label | English only (50-char limit, needs to be compact) |
| ASCII art banner | English only (fixed-width art) |
| Error messages from Python scripts | English only |

---

### Architecture

```
~/.o-team/                         # Global (cross-project)
├── registry.json                   # Team registry
├── config.json                     # Global settings (language, etc.)
├── status.json                     # Live pipeline status (transient)
├── statusline.py                   # claude-hud extra-cmd script
└── statusline_standalone.py        # Standalone statusline script

{project}/.o-team/                 # Per-project
├── pipelines/                      # Pipeline definitions (git-committable)
│   └── my-pipeline.yaml
├── status.json                     # Per-project live status (transient)
└── runs/                           # Execution sandboxes (gitignored)
    └── {uuid}/
        ├── meta.json               # Run state
        ├── snapshot.yaml            # Pipeline snapshot at execution time
        ├── workspace/              # Shared files across all nodes
        ├── 01-research/            # Node 1 office folder
        │   ├── CLAUDE.md           # ← copied from team
        │   ├── .claude/            # ← copied from team
        │   ├── input.md            # Handoff from previous node
        │   ├── output.md           # This node's deliverable
        │   ├── prompt.md           # Assembled prompt (audit)
        │   ├── run.log             # Parsed CLI output log
        │   └── events.jsonl        # Raw stream-json events (debug)
        └── 02-design/              # Node 2 office folder
            └── ...
```

#### Execution Flow

```
/o-team:run my-pipeline
  │
  ▼
Create UUID sandbox + copy team configs into office folders
  │
  ▼
For each node sequentially:
  │
  ├─▶ Assemble prompt.md (instructions + input.md context + workspace listing)
  │     │
  │     ▼
  │   Spawn: claude -p "<prompt>" --output-format stream-json --verbose
  │          --dangerously-skip-permissions
  │   (cwd = office folder → loads that team's CLAUDE.md + .claude/)
  │     │
  │     ▼
  │   Parse stream-json events:
  │     ├─ assistant/text     → run.log + status preview
  │     ├─ assistant/tool_use → run.log + status bar (tool name)
  │     ├─ system/task_*      → status bar (agent activity)
  │     └─ result             → run.log + final metrics
  │     │
  │     ▼
  │   Process completes → check exit code
  │     │
  │     ▼
  │   mode=auto? ──▶ Copy output.md → next input.md → next node
  │   mode=gate? ──▶ PAUSED — show output preview
  │                     │
  │                     ▼
  │                  Human reviews:
  │                   ├─ approve → Copy output → Next node
  │                   ├─ reject  → Reset & re-execute
  │                   ├─ edit    → Modify output.md → Continue
  │                   ├─ skip    → Pass through → Next node
  │                   └─ abort   → Cancel pipeline
  │
  ▼
All nodes complete → final output in last node's output.md
```

### Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Python 3.10+
- Node.js 18+ (for npx install only)

### Installation

```bash
cd your-project
npx github:chemistrywow31/O-Team
```

That's it. The installer:
1. Copies the skill to `.claude/skills/o-team/`
2. Checks for Python, PyYAML, and Claude CLI
3. Installs statusline scripts to `~/.o-team/`
4. Detects your statusline setup and shows options

**Install with statusline configuration:**

```bash
npx github:chemistrywow31/O-Team --statusline merge    # Merge with claude-hud
npx github:chemistrywow31/O-Team --statusline o-team    # O-Team standalone
npx github:chemistrywow31/O-Team --statusline keep      # Don't touch statusline
```

**Other options:**

```bash
npx github:chemistrywow31/O-Team --force       # Overwrite existing installation
npx github:chemistrywow31/O-Team --uninstall   # Remove the skill
```

**Manual install** (if you prefer not to use npx):

```bash
mkdir -p .claude/skills
git clone https://github.com/chemistrywow31/O-Team.git .claude/skills/o-team
pip install pyyaml
# Copy statusline scripts manually:
cp .claude/skills/o-team/scripts/statusline.py ~/.o-team/
cp .claude/skills/o-team/scripts/statusline_standalone.py ~/.o-team/
```

### O-Team Web vs O-Team CLI

| Feature | O-Team Web | O-Team CLI |
|---------|-----------|------------|
| Interface | Browser SPA (React) | Terminal (Claude Code) |
| Pipeline builder | Drag-and-drop canvas | Interactive selection + YAML |
| Prompt generation | Manual per node | AI auto-generates from objective |
| Team import | ZIP / Git / Local | Local path registration |
| Execution monitor | Real-time chat UI | Stream JSON + statusline |
| Event tracking | Socket.IO events | `events.jsonl` per node |
| Database | MongoDB | JSON files (zero-dependency) |
| Installation | `npm install` + MongoDB | `git clone` (zero-dependency) |
| Multi-user | Planned | Single-user (per terminal) |
| Platform | Browser (any OS) | Terminal (any OS with Claude Code) |

### Project Structure

```
o-team-cli/
├── package.json                    # npm package (for npx install)
├── bin/
│   └── install.js                  # npx entry — copies skill, statusline setup
├── skill/                          # Actual skill content
│   ├── SKILL.md                    # Skill definition (triggers + interaction flow)
│   ├── scripts/
│   │   ├── utils.py                # Shared utilities (YAML/JSON I/O, UUID, paths)
│   │   ├── i18n.py                 # Internationalization (en, zh-TW)
│   │   ├── config.py               # Configuration management (statusline, language)
│   │   ├── stream_parser.py        # Stream JSON event parser
│   │   ├── statusline.py           # claude-hud --extra-cmd script
│   │   ├── statusline_standalone.py# Standalone statusline script
│   │   ├── validate_path.py        # Team directory validation
│   │   ├── registry.py             # Team registry management
│   │   ├── create_pipeline.py      # Pipeline YAML generation
│   │   ├── validate_pipeline.py    # Pipeline integrity validation
│   │   ├── run_pipeline.py         # Execution engine (sandbox + stream-json + spawn)
│   │   ├── approve_node.py         # Gate operations (approve/reject/skip/abort)
│   │   ├── check_status.py         # Run status query
│   │   ├── list_runs.py            # Run history
│   │   └── clean_runs.py           # Run directory cleanup
│   ├── references/
│   │   └── pipeline-schema.md      # YAML schema documentation
│   └── templates/
│       └── example-pipeline.yaml
├── README.md
└── LICENSE
```

### License

MIT

---

<a id="繁體中文"></a>

## 繁體中文

**[English](#english)** | **繁體中文**

```
   ___        _____
  / _ \      |_   _|__  __ _ _ __ ___
 | | | |_____  | |/ _ \/ _` | '_ ` _ \
 | |_| |_____| | |  __/ (_| | | | | | |
  \___/        |_|\___|\__,_|_| |_| |_|
                Agent Office
```

### 複雜任務。獨立上下文。人工把關。— 全在終端機完成。

> **A-Team 打造專業辦公室，O-Team CLI 讓它們組成一間公司 — 不需要瀏覽器。**

O-Team CLI 是一個 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 技能（Skill），將多個 AI Agent 團隊串接成線性流水線。每個團隊作為獨立的 `claude` 進程執行，擁有自己的全新上下文空間。團隊之間只透過結構化文件交接（`output.md → input.md`）——不共享對話歷史、不互相污染。可配置的人工審核閘門確保產出品質，一切操作都在終端機中完成。

### 痛點

單一 AI Agent 處理專注任務表現很好。但真實專案需要**多個專業團隊**依序協作——調研、設計、實作、審查。當你試圖在一個 AI session 中完成所有事：

- **上下文退化** — 對話越長，AI 越容易失焦
- **錯誤累積** — 一個節點的錯誤產出污染所有下游
- **沒有檢查點** — 無法在過程中審查、調整或介入

### 解決方案

O-Team CLI 把每個 AI Agent 團隊當作一間獨立辦公室。就像公司裡的各個部門：

- **獨立運作** — 每個節點啟動一個獨立的 `claude -p` 進程，擁有自己完整的上下文空間，載入該團隊專屬的 `CLAUDE.md` 和 `.claude/` 配置
- **刻意交接** — 節點之間只傳遞 `output.md → input.md` 文件，而非對話歷史
- **向管理層回報** — `gate` 模式暫停執行等待人工審查：批准、退回、修改產出或終止

最終效果：多團隊 AI 流水線，品質不會隨複雜度增加而衰退。

### 與 A-Team 的關係

[A-Team](https://github.com/chemistrywow31/A-Team) 生成專業的 AI Agent 團隊資料夾——每個包含 `CLAUDE.md` 定義和 `.claude/agents/` 目錄中的角色化 Agent。

O-Team CLI **消費**這些團隊資料夾，讓你可以：

1. **註冊** 團隊（本機路徑，單一或批次掃描）
2. **組建** 命名流水線（選擇團隊 + 排序）
3. **執行** 流水線（逐節點 Prompt 注入 + 自動上下文交接）
4. **審查** 閘門節點的產出，確認後再繼續

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  A-Team #1  │───▶│  A-Team #2  │───▶│  A-Team #3  │───▶│  A-Team #4  │
│  調研團隊    │    │  設計團隊    │    │  撰寫團隊    │    │  QA 審查    │
│             │    │             │    │             │    │             │
│ output.md ──│───▶│── input.md  │    │ output.md ──│───▶│── input.md  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      ▲                                                        │
      │            每個節點 = 獨立的 claude 進程                  │
      └──────────── 每一步都有人工審核閘門 ─────────────────────┘
```

### 功能特色

#### 團隊註冊
- **註冊** Agent 團隊：支援單一資料夾或整個目錄批次掃描
- **自動偵測** 團隊結構：解析 `CLAUDE.md`、統計 agents/skills/rules 數量、尋找 coordinator
- **驗證** 路徑完整性：CLAUDE.md 存在性、`.claude/` 結構、Agent 定義
- **AI 生成摘要** — Claude 讀取每個團隊的配置，自動產出能力描述
- **全域註冊表** `~/.o-team/registry.json` — 註冊一次，跨專案使用

#### 流水線建構器（`/o-team:build`）
- **選擇並排序** 已註冊的團隊（輸入編號即可，不需手寫 YAML）
- **選擇執行模式**：每個節點可設為 `auto`（自動繼續）或 `gate`（暫停審查）
- **AI 自動生成 Prompt** — 提供目標和第一步 Prompt，Opus 根據每個團隊的 `CLAUDE.md` 能力自動串聯生成後續所有節點的 Prompt
- **儲存前確認** — 所有生成的 Prompt 一次呈現，可逐一修改
- **Pipeline YAML** — 存入 `.o-team/pipelines/`，可納入版本控制

#### 執行引擎（`/o-team:run`）
- **UUID 沙盒隔離** — 每次執行建立唯一工作區，並行執行互不干擾
- **辦公室模型** — 每個節點獨立資料夾，包含完整的團隊 `CLAUDE.md` + `.claude/` 配置副本
- **獨立上下文** — 每個節點啟動獨立的 `claude -p` 進程，從自己的辦公室資料夾啟動，只載入該團隊身分
- **Stream JSON 事件** — 使用 `--output-format stream-json --verbose` 接收結構化事件（參見[狀態列](#狀態列statusline)）
- **自動交接** — 完成節點的 `output.md` 自動複製為下一節點的 `input.md`
- **共享工作區** — `workspace/` 目錄跨所有節點持續存在，放置共用檔案
- **審計軌跡** — 每個節點的組裝 `prompt.md`、`run.log` 和原始 `events.jsonl` 完整保留

#### 人工審核閘門
- **approve** — 接受產出，繼續下一節點
- **reject** — 丟棄產出，重新執行本節點
- **edit** — 直接修改 `output.md`，然後繼續
- **skip** — 跳過本節點，將輸入直接傳遞給下一節點
- **abort** — 取消整條流水線

#### 執行管理
- **狀態查詢** — 查看任何 run 的當前狀態和逐節點進度
- **歷史紀錄** — 列出所有 run，含狀態、進度、時間戳
- **清理** — 刪除指定 run 或按狀態批次清理
- **恢復** — 從暫停或錯誤的位置恢復執行

---

### 指令一覽

| 指令 | 說明 |
|------|------|
| `/o-team:registry add <path>` | 註冊團隊資料夾 |
| `/o-team:registry list` | 列出已註冊團隊 |
| `/o-team:registry remove <slug>` | 移除已註冊團隊 |
| `/o-team:build` | 互動式建構命名流水線 |
| `/o-team:run <pipeline-name>` | 執行流水線 |
| `/o-team:status <run-id>` | 查詢執行狀態 |
| `/o-team:runs` | 列出執行歷史 |
| `/o-team:clean [run-id]` | 清理執行目錄 |
| `/o-team:config` | 互動式設定（狀態列、語系） |

---

### 狀態列（Statusline）

O-Team 整合 Claude Code 狀態列，在 pipeline 執行時即時顯示當前節點、使用的工具和 agent 活動。

#### 運作方式

```
claude -p --output-format stream-json --verbose
    │
    ▼  (每行一個 JSON 事件)
stream_parser.py ── 解析事件 ──┬── 顯示軌道 (text, tool_use, result)
                               └── Agent 軌道 (spawn, progress, complete)
    │
    ├── events.jsonl    (原始事件存檔)
    ├── run.log         (解析後的文字+工具紀錄)
    └── ~/.o-team/status.json (全域狀態檔)
            │
            ▼
     statusline 腳本 ── 讀取並格式化
            │
            ▼
     Claude Code 狀態列
```

#### 狀態列相容性

Claude Code 的 `settings.json` 只支援**一個** `statusLine.command`，沒有原生的組合機制。O-Team 提供三種配置模式：

| 模式 | 安裝參數 | 行為 |
|------|---------|------|
| **O-Team 獨立** | `--statusline o-team` | 替換現有 statusline，顯示基本 session 資訊 + pipeline 狀態 |
| **保留現有** | `--statusline keep` | 不動 statusline，事件記錄在 log 但不顯示在狀態列 |
| **合併 claude-hud** | `--statusline merge` | 透過 `--extra-cmd` 在 claude-hud 旁顯示 O-Team 狀態 |

**合併模式僅支援 [claude-hud](https://github.com/jarrodwatts/claude-hud)**（13.8k stars），因為它是唯一提供擴充機制的 statusline 工具。其他工具（ccusage、ccstatusline、CCometixLine、claude-powerline 等）不支援組合。

| 你目前的狀態 | 建議模式 |
|-------------|---------|
| 沒有 statusline | `o-team`（啟用 pipeline 狀態） |
| 有 claude-hud | `merge`（保留 HUD + 加入 pipeline 狀態） |
| 有其他 statusline 工具 | `keep`（不破壞現有設定） |

#### 設定方式

**方式 A：安裝時指定**

```bash
npx github:chemistrywow31/O-Team --statusline merge
npx github:chemistrywow31/O-Team --statusline o-team
npx github:chemistrywow31/O-Team --statusline keep
```

**方式 B：互動設定**

```
/o-team:config
```

**方式 C：手動修改** `~/.claude/settings.json`

---

### 多語系（i18n）

O-Team 支援 **English** 和**繁體中文**。

#### 語言偵測優先順序

1. `~/.o-team/config.json` → `"language"` 欄位（使用者覆寫，透過 `/o-team:config`）
2. `~/.claude/settings.json` → `"language"` 欄位（Claude Code 設定）
3. 系統 `LANG` / `LC_ALL` 環境變數
4. 預設：English

#### 切換語系

```
/o-team:config → 語系 / Language → 選擇
```

或直接編輯 `~/.o-team/config.json`：

```json
{
  "language": "zh-TW"
}
```

---

### 架構

```
~/.o-team/                         # 全域（跨專案）
├── registry.json                   # 團隊註冊表
├── config.json                     # 全域設定（語系等）
├── status.json                     # Pipeline 即時狀態（暫存）
├── statusline.py                   # claude-hud extra-cmd 腳本
└── statusline_standalone.py        # 獨立 statusline 腳本

{project}/.o-team/                 # 專案級
├── pipelines/                      # 流水線定義（可 git commit）
│   └── my-pipeline.yaml
├── status.json                     # 專案級即時狀態（暫存）
└── runs/                           # 執行沙盒（gitignored）
    └── {uuid}/
        ├── meta.json               # Run 狀態
        ├── snapshot.yaml           # 執行時的流水線快照
        ├── workspace/              # 跨節點共享檔案
        ├── 01-research/            # 節點 1 辦公室資料夾
        │   ├── CLAUDE.md           # ← 複製自團隊
        │   ├── .claude/            # ← 複製自團隊
        │   ├── input.md            # 上一節點的交接文件
        │   ├── output.md           # 本節點的產出
        │   ├── prompt.md           # 組裝後的完整 Prompt（審計用）
        │   ├── run.log             # 解析後的 CLI 輸出日誌
        │   └── events.jsonl        # 原始 stream-json 事件（除錯用）
        └── 02-design/              # 節點 2 辦公室資料夾
            └── ...
```

#### 執行流程

```
/o-team:run my-pipeline
  │
  ▼
建立 UUID 沙盒 + 複製團隊配置到各辦公室資料夾
  │
  ▼
依序處理每個節點：
  │
  ├─▶ 組裝 prompt.md（指令 + input.md 上下文 + workspace 檔案清單）
  │     │
  │     ▼
  │   啟動: claude -p "<prompt>" --output-format stream-json --verbose
  │          --dangerously-skip-permissions
  │   (cwd = 辦公室資料夾 → 載入該團隊的 CLAUDE.md + .claude/)
  │     │
  │     ▼
  │   解析 stream-json 事件：
  │     ├─ assistant/text     → run.log + 狀態預覽
  │     ├─ assistant/tool_use → run.log + 狀態列（工具名稱）
  │     ├─ system/task_*      → 狀態列（Agent 活動）
  │     └─ result             → run.log + 最終指標
  │     │
  │     ▼
  │   進程完成 → 檢查 exit code
  │     │
  │     ▼
  │   mode=auto? ──▶ 複製 output.md → 下一步 input.md → 繼續
  │   mode=gate? ──▶ 暫停 — 顯示產出預覽
  │                     │
  │                     ▼
  │                  人工審查：
  │                   ├─ approve → 複製產出 → 下一節點
  │                   ├─ reject  → 重置並重新執行
  │                   ├─ edit    → 修改 output.md → 繼續
  │                   ├─ skip    → 傳遞輸入 → 下一節點
  │                   └─ abort   → 取消流水線
  │
  ▼
全部完成 → 最終產出在最後一個節點的 output.md
```

### 前置需求

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) 已安裝並完成認證
- Python 3.10+
- Node.js 18+（僅 npx 安裝時需要）

### 安裝

```bash
cd your-project
npx github:chemistrywow31/O-Team
```

一行搞定。安裝程式會：
1. 將 skill 複製到 `.claude/skills/o-team/`
2. 檢查 Python、PyYAML、Claude CLI 是否就緒
3. 安裝 statusline 腳本到 `~/.o-team/`
4. 偵測你的 statusline 設定並顯示選項

**帶 statusline 設定安裝：**

```bash
npx github:chemistrywow31/O-Team --statusline merge    # 合併 claude-hud
npx github:chemistrywow31/O-Team --statusline o-team    # O-Team 獨立
npx github:chemistrywow31/O-Team --statusline keep      # 不動 statusline
```

**其他選項：**

```bash
npx github:chemistrywow31/O-Team --force       # 覆蓋現有安裝
npx github:chemistrywow31/O-Team --uninstall   # 移除 skill
```

### O-Team Web 版 vs O-Team CLI 版

| 功能 | O-Team Web | O-Team CLI |
|------|-----------|------------|
| 介面 | 瀏覽器 SPA (React) | 終端機 (Claude Code) |
| 流水線建構 | 拖拽式畫布 | 互動式選擇 + YAML |
| Prompt 生成 | 手動逐節點設定 | AI 根據目標自動串聯生成 |
| 團隊匯入 | ZIP / Git / 本機路徑 | 本機路徑註冊 |
| 執行監控 | 即時 Chat 介面 | Stream JSON + 狀態列 |
| 事件追蹤 | Socket.IO 事件 | `events.jsonl`（每節點） |
| 資料庫 | MongoDB | JSON 檔案（零依賴） |
| 安裝方式 | `npm install` + MongoDB | `git clone`（零依賴） |
| 多用戶 | 計劃中 | 單用戶（每個終端機獨立） |
| 跨平台 | 瀏覽器（任何 OS） | 終端機（任何有 Claude Code 的 OS） |

### 專案結構

```
o-team-cli/
├── package.json                    # npm 套件（供 npx 安裝）
├── bin/
│   └── install.js                  # npx 入口 — 複製 skill + statusline 設定
├── skill/                          # 實際 skill 內容
│   ├── SKILL.md                    # 技能定義（觸發條件 + 互動流程）
│   ├── scripts/
│   │   ├── utils.py                # 共用工具（YAML/JSON I/O、UUID、路徑）
│   │   ├── i18n.py                 # 多語系（en、zh-TW）
│   │   ├── config.py               # 設定管理（statusline、語系）
│   │   ├── stream_parser.py        # Stream JSON 事件解析器
│   │   ├── statusline.py           # claude-hud --extra-cmd 腳本
│   │   ├── statusline_standalone.py# 獨立 statusline 腳本
│   │   ├── validate_path.py        # 團隊目錄驗證
│   │   ├── registry.py             # 團隊註冊管理
│   │   ├── create_pipeline.py      # Pipeline YAML 生成
│   │   ├── validate_pipeline.py    # Pipeline 完整性驗證
│   │   ├── run_pipeline.py         # 執行引擎（沙盒 + stream-json + 進程）
│   │   ├── approve_node.py         # 閘門操作（approve/reject/skip/abort）
│   │   ├── check_status.py         # 執行狀態查詢
│   │   ├── list_runs.py            # 執行歷史
│   │   └── clean_runs.py          # 執行目錄清理
│   ├── references/
│   │   └── pipeline-schema.md      # YAML schema 文件
│   └── templates/
│       └── example-pipeline.yaml
├── README.md
└── LICENSE
```

### 授權

MIT
