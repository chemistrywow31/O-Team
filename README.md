# O-Team CLI

```
   ___        _____
  / _ \      |_   _|__  __ _ _ __ ___
 | | | |_____  | |/ _ \/ _` | '_ ` _ \
 | |_| |_____| | |  __/ (_| | | | | | |
  \___/        |_|\___|\__,_|_| |_| |_|
               Agent Office
```

Chain multiple AI agent teams into pipelines. Each team works independently, passes results to the next, and you review at checkpoints.

**[English](#english)** | **[繁體中文](#繁體中文)**

---

<a id="english"></a>

## English

### Try it in 30 seconds

```bash
# Install
cd your-project
npx github:chemistrywow31/O-Team

# Open Claude Code, then:
/ot:demo
```

`/ot:demo` walks you through the entire workflow — registering teams, building a pipeline, and running it — with explanations at every step.

### What is O-Team?

O-Team is **prompt chaining, evolved**.

Traditional prompt chaining passes output from one prompt to the next within a single session. It works for simple tasks, but breaks down at scale — context degrades, errors compound, and you can't intervene mid-chain.

O-Team takes each link in the chain and gives it:
- **Its own process** — a separate `claude` instance with a fresh context window
- **Its own identity** — a team-specific `CLAUDE.md` with specialized expertise
- **Human checkpoints** — gate nodes where you review, edit, or reject before continuing

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Scout   │────▶│ Analyst  │────▶│ Advisor  │
│ Research │     │ Evaluate │     │  Brief   │
│  [auto]  │     │  [auto]  │     │  [gate]  │
└──────────┘     └──────────┘     └──────────┘
  fresh context    fresh context    fresh context
                                   ↑ you review here
```

The result: multi-step AI workflows that stay sharp at every stage, with human oversight where it matters.

### Quick Start (without demo)

```bash
# 1. Register teams (created by A-Team or manually)
/ot:reg add ./my-teams

# 2. Build a pipeline interactively
/ot:build

# 3. Run it
/ot:run
```

### Commands

| Command | Description |
|---------|-------------|
| `/ot:demo` | Guided tutorial — start here |
| `/ot:reg` | List registered teams |
| `/ot:reg add <path>` | Register team(s) from path |
| `/ot:reg rm <slug>` | Remove a team |
| `/ot:build` | Build a pipeline interactively |
| `/ot:run [name]` | Run a pipeline |
| `/ot:pipe` | List saved pipelines |
| `/ot:pipe show <name>` | Show pipeline details |
| `/ot:pipe rm <name>` | Delete a pipeline |
| `/ot:status` | Check running pipeline status |
| `/ot:runs` | View run history |
| `/ot:clean` | Clean up old runs |
| `/ot:config` | Settings (statusline, language) |

<details>
<summary>Long aliases (backward compatible)</summary>

All commands also work with the `o-team:` prefix:
`/o-team:registry`, `/o-team:build`, `/o-team:run`, `/o-team:pipeline`, `/o-team:status`, `/o-team:runs`, `/o-team:clean`, `/o-team:config`
</details>

### How It Works

1. **Teams** are folders with a `CLAUDE.md` that defines the team's identity and capabilities. Create them with [A-Team](https://github.com/chemistrywow31/A-Team) or write them yourself.

2. **Pipelines** chain registered teams in order. Each team becomes a node. You set each node to `auto` (proceed automatically) or `gate` (pause for review).

3. **Execution** creates an isolated sandbox for each run. Each node gets its own office folder with the team's config, runs as an independent `claude -p` process, and writes `output.md` which becomes the next node's input.

### Installation

```bash
cd your-project
npx github:chemistrywow31/O-Team
```

The installer copies the skill to `.claude/skills/o-team/` and sets up statusline scripts.

**Options:**

```bash
npx github:chemistrywow31/O-Team --statusline merge    # Merge with claude-hud
npx github:chemistrywow31/O-Team --statusline o-team    # Standalone statusline
npx github:chemistrywow31/O-Team --statusline keep      # Don't touch statusline
npx github:chemistrywow31/O-Team --force                # Overwrite existing
npx github:chemistrywow31/O-Team --uninstall            # Remove
```

**Manual install:**

```bash
mkdir -p .claude/skills
git clone https://github.com/chemistrywow31/O-Team.git .claude/skills/o-team
pip install pyyaml
```

**Requirements:** Claude Code CLI + Python 3.10+ + Node.js 18+ (npx only)

### Statusline

O-Team shows real-time pipeline status in the Claude Code status bar:

```
O [1/3] 01-scout Read              ← node using Read tool
O [2/3] 02-analyst Agent:explore   ← agent spawned
O [3/3] 03-advisor Done(45s,$0.03) ← node complete
```

Three modes: `merge` (with claude-hud), `o-team` (standalone), `keep` (don't touch).
Configure via `--statusline` flag during install or `/ot:config`.

### i18n

Supports English and Traditional Chinese (繁體中文).

```
/ot:config → Language
```

### Architecture

```
~/.o-team/                          # Global
├── registry.json                    # Registered teams
├── config.json                      # Settings
└── status.json                      # Live status (transient)

{project}/.o-team/                   # Per-project
├── pipelines/*.yaml                 # Saved pipelines (git-committable)
└── runs/{uuid}/                     # Execution sandboxes (gitignored)
    ├── meta.json                    # Run state
    ├── workspace/                   # Shared across nodes
    └── {node-id}/                   # Node office folder
        ├── CLAUDE.md                # Team identity (copied)
        ├── .claude/                 # Team config (copied)
        ├── input.md                 # Input from previous node
        ├── output.md                # This node's deliverable
        ├── prompt.md                # Assembled prompt (audit)
        └── run.log                  # Execution log
```

### License

MIT

---

<a id="繁體中文"></a>

## 繁體中文

**[English](#english)** | **繁體中文**

### 30 秒體驗

```bash
# 安裝
cd your-project
npx github:chemistrywow31/O-Team

# 開啟 Claude Code，然後：
/ot:demo
```

`/ot:demo` 會帶你走過完整流程 — 註冊團隊、建立 pipeline、執行 — 每一步都有說明。

### O-Team 是什麼？

O-Team 是 **Prompt Chaining 的進化版**。

傳統的 prompt chaining 在同一個 session 中把前一個 prompt 的輸出傳給下一個。簡單任務沒問題，但規模一大就會崩 — 上下文退化、錯誤累積、無法中途介入。

O-Team 把 chain 中的每一環獨立出來，賦予：
- **獨立程序** — 每個節點是一個全新的 `claude` 實例，上下文從零開始
- **專屬身份** — 每個團隊有自己的 `CLAUDE.md`，定義專業領域
- **人工檢查點** — gate 節點讓你審核、修改、退回再繼續

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Scout   │────▶│ Analyst  │────▶│ Advisor  │
│  調查    │     │  分析     │     │  建議    │
│  [auto]  │     │  [auto]  │     │  [gate]  │
└──────────┘     └──────────┘     └──────────┘
  全新上下文       全新上下文       全新上下文
                                   ↑ 你在這裡審核
```

結果：多步驟 AI 工作流在每個階段都保持精準，關鍵環節有人工把關。

### 快速開始（不用 demo）

```bash
# 1. 註冊團隊（用 A-Team 建立或手動建立）
/ot:reg add ./my-teams

# 2. 互動式建立 pipeline
/ot:build

# 3. 執行
/ot:run
```

### 指令一覽

| 指令 | 說明 |
|------|------|
| `/ot:demo` | 教學導覽 — 從這裡開始 |
| `/ot:reg` | 列出已註冊的團隊 |
| `/ot:reg add <path>` | 從路徑註冊團隊 |
| `/ot:reg rm <slug>` | 移除團隊 |
| `/ot:build` | 互動式建立 pipeline |
| `/ot:run [name]` | 執行 pipeline |
| `/ot:pipe` | 列出已存的 pipeline |
| `/ot:pipe show <name>` | 顯示 pipeline 詳情 |
| `/ot:pipe rm <name>` | 刪除 pipeline |
| `/ot:status` | 查看執行中的狀態 |
| `/ot:runs` | 查看執行歷史 |
| `/ot:clean` | 清理舊的執行紀錄 |
| `/ot:config` | 設定（狀態列、語系） |

<details>
<summary>完整指令名稱（向後相容）</summary>

所有指令也支援 `o-team:` 前綴：
`/o-team:registry`、`/o-team:build`、`/o-team:run`、`/o-team:pipeline`、`/o-team:status`、`/o-team:runs`、`/o-team:clean`、`/o-team:config`
</details>

### 運作方式

1. **團隊**是包含 `CLAUDE.md` 的資料夾，定義團隊的身份與能力。用 [A-Team](https://github.com/chemistrywow31/A-Team) 生成或手動建立。

2. **Pipeline** 把註冊的團隊依序串接。每個團隊成為一個節點，可設為 `auto`（自動繼續）或 `gate`（暫停審核）。

3. **執行**時為每次 run 建立隔離的 sandbox。每個節點有自己的辦公室資料夾、獨立的 `claude -p` 程序，產出的 `output.md` 成為下一個節點的輸入。

### 安裝

```bash
cd your-project
npx github:chemistrywow31/O-Team
```

**手動安裝：**

```bash
mkdir -p .claude/skills
git clone https://github.com/chemistrywow31/O-Team.git .claude/skills/o-team
pip install pyyaml
```

**需求：** Claude Code CLI + Python 3.10+ + Node.js 18+（僅 npx 需要）

### 授權

MIT
