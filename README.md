# O-Team CLI (Agent Office)

### Complex Tasks. Independent Contexts. Human Oversight. — All from the Terminal.

> **A-Team builds the offices. O-Team CLI makes them run like a company — no browser required.**

**[English](#english)** | **[繁體中文](#繁體中文)**

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

O-Team CLI **consumes** these team folders and lets you:

1. **Register** teams from local paths (single folder or batch scan)
2. **Build** named pipelines by selecting and ordering teams
3. **Run** pipelines with per-node prompt injection and automatic context handoff
4. **Review** outputs at gate nodes before proceeding

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  A-Team #1  │───▶│  A-Team #2  │───▶│  A-Team #3  │───▶│  A-Team #4  │
│  Research   │    │  Design     │    │  Writing    │    │  QA Review  │
│             │    │             │    │             │    │             │
│ output.md ──│───▶│── input.md  │    │ output.md ──│───▶│── input.md  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      ▲                                                        │
      │            Each node = independent claude process      │
      └──────────── Human review gate at every step ───────────┘
```

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
- **Automatic handoff** — `output.md` from completed nodes copies to the next node's `input.md`
- **Shared workspace** — `workspace/` directory persists across all nodes for shared files
- **Audit trail** — every node's assembled `prompt.md` and `run.log` are preserved

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

### Use Cases

#### Multi-Team Software Development
Chain specialized teams for end-to-end feature delivery:
```
Architecture Team → Frontend Team → Backend Team → QA Team → Docs Team
```
Each team receives the previous team's deliverables as context, works independently, and produces artifacts for the next.

#### Content Production Pipeline
Automate multi-stage content workflows:
```
Research Team → Drafting Team → Review Team → Localization Team
```
Human review gates ensure editorial quality at every stage.

#### Code Review & Refactoring
Set up quality-focused pipelines:
```
Analysis Team → Refactor Team → Test Team → Security Audit Team
```
Each stage focuses on one concern with full context isolation.

#### Technical Specification Design
Chain analysis through to final spec:
```
Requirements Team → Architecture Team → Spec Writing Team → Spec Review Team
```

### Architecture

```
~/.o-team/                         # Global (cross-project)
├── registry.json                   # Team registry
└── config.json                     # Global settings

{project}/.o-team/                 # Per-project
├── pipelines/                      # Pipeline definitions (git-committable)
│   └── my-pipeline.yaml
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
        │   └── run.log             # CLI output log
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
  │   Spawn: claude -p "$(cat prompt.md)" --dangerously-skip-permissions
  │   (cwd = office folder → loads that team's CLAUDE.md + .claude/)
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
3. Reports any missing dependencies

**Options:**

```bash
npx github:chemistrywow31/O-Team --force       # Overwrite existing installation
npx github:chemistrywow31/O-Team --uninstall   # Remove the skill
```

**Manual install** (if you prefer not to use npx):

```bash
mkdir -p .claude/skills
git clone https://github.com/chemistrywow31/O-Team.git .claude/skills/o-team
pip install pyyaml
```

### Quick Start

```bash
# 1. Start Claude Code in your project
claude

# 2. Register your agent teams
/o-team:registry add ./teams

# 3. Build a pipeline
/o-team:build

# 4. Run it
/o-team:run my-pipeline
```

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

### O-Team Web vs O-Team CLI

| Feature | O-Team Web | O-Team CLI |
|---------|-----------|------------|
| Interface | Browser SPA (React) | Terminal (Claude Code) |
| Pipeline builder | Drag-and-drop canvas | Interactive selection + YAML |
| Prompt generation | Manual per node | AI auto-generates from objective |
| Team import | ZIP / Git / Local | Local path registration |
| Execution monitor | Real-time chat UI | Terminal output streaming |
| Database | MongoDB | JSON files (zero-dependency) |
| Installation | `npm install` + MongoDB | `git clone` (zero-dependency) |
| Multi-user | Planned | Single-user (per terminal) |
| Platform | Browser (any OS) | Terminal (any OS with Claude Code) |

### Project Structure

```
o-team-cli/
├── package.json                # npm package (for npx install)
├── bin/
│   └── install.js              # npx entry — copies skill into .claude/skills/
├── skill/                      # Actual skill content
│   ├── SKILL.md                # Skill definition (triggers + interaction flow)
│   ├── scripts/
│   │   ├── utils.py            # Shared utilities (YAML/JSON I/O, UUID, paths)
│   │   ├── validate_path.py    # Team directory validation
│   │   ├── registry.py         # Team registry management
│   │   ├── create_pipeline.py  # Pipeline YAML generation
│   │   ├── validate_pipeline.py# Pipeline integrity validation
│   │   ├── run_pipeline.py     # Execution engine (sandbox + office + spawn)
│   │   ├── approve_node.py     # Gate operations (approve/reject/skip/abort)
│   │   ├── check_status.py     # Run status query
│   │   ├── list_runs.py        # Run history
│   │   └── clean_runs.py       # Run directory cleanup
│   ├── references/
│   │   └── pipeline-schema.md  # YAML schema documentation
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

### O-Team CLI (Agent Office)

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
- **自動交接** — 完成節點的 `output.md` 自動複製為下一節點的 `input.md`
- **共享工作區** — `workspace/` 目錄跨所有節點持續存在，放置共用檔案
- **審計軌跡** — 每個節點的組裝 `prompt.md` 和 `run.log` 完整保留

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

### 使用場景

#### 多團隊軟體開發
串接專業團隊進行端到端功能交付：
```
架構團隊 → 前端團隊 → 後端團隊 → QA 團隊 → 文件團隊
```
每個團隊接收前一個團隊的交付成果作為上下文，獨立作業，產出交給下一個。

#### 內容生產流水線
自動化多階段內容工作流：
```
調研團隊 → 撰稿團隊 → 審稿團隊 → 本地化團隊
```
人工審核閘門確保每個階段的編輯品質。

#### 程式碼審查與重構
建立品質導向的流水線：
```
分析團隊 → 重構團隊 → 測試團隊 → 安全稽核團隊
```
每個階段專注一個關注點，上下文完全隔離。

#### 技術規格設計
從需求分析到最終規格：
```
需求團隊 → 架構團隊 → 規格撰寫團隊 → 規格審查團隊
```

### 架構

```
~/.o-team/                         # 全域（跨專案）
├── registry.json                   # 團隊註冊表
└── config.json                     # 全域設定

{project}/.o-team/                 # 專案級
├── pipelines/                      # 流水線定義（可 git commit）
│   └── my-pipeline.yaml
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
        │   └── run.log             # CLI 輸出日誌
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
  │   啟動: claude -p "$(cat prompt.md)" --dangerously-skip-permissions
  │   (cwd = 辦公室資料夾 → 載入該團隊的 CLAUDE.md + .claude/)
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
3. 回報任何缺少的依賴

**選項：**

```bash
npx github:chemistrywow31/O-Team --force       # 覆蓋現有安裝
npx github:chemistrywow31/O-Team --uninstall   # 移除 skill
```

**手動安裝**（不想用 npx）：

```bash
mkdir -p .claude/skills
git clone https://github.com/chemistrywow31/O-Team.git .claude/skills/o-team
pip install pyyaml
```

### 快速開始

```bash
# 1. 在你的專案中啟動 Claude Code
claude

# 2. 註冊你的 agent 團隊
/o-team:registry add ./teams

# 3. 建構流水線
/o-team:build

# 4. 執行
/o-team:run my-pipeline
```

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

### O-Team Web 版 vs O-Team CLI 版

| 功能 | O-Team Web | O-Team CLI |
|------|-----------|------------|
| 介面 | 瀏覽器 SPA (React) | 終端機 (Claude Code) |
| 流水線建構 | 拖拽式畫布 | 互動式選擇 + YAML |
| Prompt 生成 | 手動逐節點設定 | AI 根據目標自動串聯生成 |
| 團隊匯入 | ZIP / Git / 本機路徑 | 本機路徑註冊 |
| 執行監控 | 即時 Chat 介面 | 終端機輸出串流 |
| 資料庫 | MongoDB | JSON 檔案（零依賴） |
| 安裝方式 | `npm install` + MongoDB | `git clone`（零依賴） |
| 多用戶 | 計劃中 | 單用戶（每個終端機獨立） |
| 跨平台 | 瀏覽器（任何 OS） | 終端機（任何有 Claude Code 的 OS） |

### 專案結構

```
o-team-cli/
├── package.json                # npm 套件（供 npx 安裝）
├── bin/
│   └── install.js              # npx 入口 — 將 skill 複製到 .claude/skills/
├── skill/                      # 實際 skill 內容
│   ├── SKILL.md                # 技能定義（觸發條件 + 互動流程）
│   ├── scripts/
│   │   ├── utils.py            # 共用工具（YAML/JSON I/O、UUID、路徑操作）
│   │   ├── validate_path.py    # 團隊目錄驗證
│   │   ├── registry.py         # 團隊註冊管理
│   │   ├── create_pipeline.py  # Pipeline YAML 生成
│   │   ├── validate_pipeline.py# Pipeline 完整性驗證
│   │   ├── run_pipeline.py     # 執行引擎（沙盒 + 辦公室 + 進程管理）
│   │   ├── approve_node.py     # 閘門操作（approve/reject/skip/abort）
│   │   ├── check_status.py     # 執行狀態查詢
│   │   ├── list_runs.py        # 執行歷史
│   │   └── clean_runs.py       # 執行目錄清理
│   ├── references/
│   │   └── pipeline-schema.md  # YAML schema 文件
│   └── templates/
│       └── example-pipeline.yaml
├── README.md
└── LICENSE
```

### 授權

MIT
