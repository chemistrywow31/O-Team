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
# With teams
/ot:reg add ./my-teams     # register teams
/ot:build                  # build a team-based pipeline
/ot:run                    # execute

# Without teams — pure prompt chain
/ot:chain                  # build interactively, or: /ot:chain chain.md
```

### Commands

| Command | Description |
|---------|-------------|
| `/ot:demo` | Guided tutorial — start here |
| `/ot:chain [path]` | Build a pipeline from a prompt chain (no teams required) |
| `/ot:reg` | List registered teams |
| `/ot:reg add <path>` | Register team(s) from path |
| `/ot:reg rm <slug>` | Remove a team |
| `/ot:build` | Build a team-based pipeline interactively |
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

1. **Nodes** are either **teams** (folders with `CLAUDE.md` defining an identity) or **pure prompts** (no team — the prompt itself is all the instruction). A pipeline can mix both.

2. **Pipelines** chain nodes in order. Each node is `auto` (proceed automatically) or `gate` (pause for your review).

3. **Execution** creates an isolated sandbox per run. Each node gets its own office folder, runs as an independent `claude -p` process, and writes `output.md` which becomes the next node's input.

### Per-node controls

Every node can independently set:

| Field | Purpose |
|---|---|
| `model` | Route cheap tasks to Haiku, reasoning to Sonnet, synthesis to Opus |
| `effort` | Thinking level: `low` / `medium` / `high` / `xhigh` / `max`. Delivered via a per-subprocess env var — parallel runs don't race. |
| `mode` | `auto` (hands-free) or `gate` (pause for approve / edit / reject / skip) |
| `identity` | Written as CLAUDE.md in the node's office folder |
| `rules` | List of markdown files copied into the node's `.claude/rules/` |
| `timeout` | Subprocess timeout (seconds) |

### Cross-node references

Later nodes can pull in outputs from any prior step — not just the immediately preceding one:

```yaml
- id: 03-report
  prompt: |
    Combine these inputs:

    Original facts: {{node:01-extract}}
    Analysis:       {{node:02-analyse}}

    ...produce the final brief.
```

At prompt-assembly time each `{{node:<id>}}` tag is replaced with `<output id="<id>">...content of that node's output.md...</output>`. Every completed node's output is also auto-copied to `workspace/<node_id>.md`, so a node can instead read it via the Read tool if the content is too large to inline.

### Example pipeline

See [`skill/templates/example-prompt-chain.yaml`](skill/templates/example-prompt-chain.yaml) for a complete example demonstrating every feature — inline and external prompts, `{{node:<id>}}` cross-references, per-node `model` / `effort`, `identity`, `rules`, and mixed `auto` / `gate` modes.

### Why O-Team

- **Fresh context every step** — Each node runs in its own `claude` process. No context degradation, no cross-contamination between teams. Step 5 is as sharp as step 1.
- **Review where it matters** — Gate nodes pause for your review with approve, reject, edit, or skip. Auto nodes run hands-free. Mix both in one pipeline.
- **Pick up where you left off** — `--from N` restarts from any node, reusing outputs from the previous run. Swap in revised input or keep everything as-is.
- **Full audit trail** — Every node saves its assembled prompt, raw stream events, and human-readable log. See exactly what happened and why.
- **Live status bar** — Real-time pipeline progress in your Claude Code status bar. See which node is running, what tool it's using, and how much it costs — as it happens.
- **Stream-parsed monitoring** — Type-safe event parsing tracks tool calls, agent spawns, costs, and durations. Agent lifecycle linking (`tool_use_id` → `task_id`) gives you accurate subagent visibility.

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

{project}/.o-team/                        # Per-project
├── pipelines/*.yaml                      # Saved pipelines (git-committable)
├── runs/{uuid}/                          # Execution sandboxes (gitignored)
│   ├── meta.json                          # Run state
│   ├── workspace/                         # Shared across nodes
│   │   └── {prev-node-id}.md              # Auto-published prior outputs
│   └── {node-id}/                         # Node office folder
│       ├── CLAUDE.md                      # Team identity (or prompt-node stub)
│       ├── .claude/                       # Team config (copied)
│       ├── input.md                       # Input from previous node
│       ├── output.md                      # This node's deliverable
│       ├── prompt.md                      # Assembled prompt (audit)
│       └── run.log                        # Execution log
└── archive/YYYY/MM/DD/{name}-{uuid}/     # Archived runs (date-partitioned)
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
# 有團隊
/ot:reg add ./my-teams     # 註冊團隊
/ot:build                  # 建立以團隊為節點的 pipeline
/ot:run                    # 執行

# 沒團隊 — 純 prompt chain
/ot:chain                  # 互動建立，或：/ot:chain chain.md
```

### 指令一覽

| 指令 | 說明 |
|------|------|
| `/ot:demo` | 教學導覽 — 從這裡開始 |
| `/ot:chain [path]` | 從 prompt chain 建立 pipeline（不需團隊） |
| `/ot:reg` | 列出已註冊的團隊 |
| `/ot:reg add <path>` | 從路徑註冊團隊 |
| `/ot:reg rm <slug>` | 移除團隊 |
| `/ot:build` | 互動式建立團隊 pipeline |
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

1. **節點**可以是**團隊**（包含 `CLAUDE.md` 定義身份的資料夾）或**純 prompt**（不需團隊，prompt 本身就是全部指令）。Pipeline 可以混用兩種。

2. **Pipeline** 把節點依序串接。每個節點是 `auto`（自動繼續）或 `gate`（暫停審核）。

3. **執行**時為每次 run 建立隔離的 sandbox。每個節點有自己的辦公室資料夾、獨立的 `claude -p` 程序，產出的 `output.md` 成為下一個節點的輸入。

### 每個節點都可獨立設定

| 欄位 | 用途 |
|---|---|
| `model` | 便宜任務用 Haiku、推理用 Sonnet、最終統合用 Opus |
| `effort` | 思考強度：`low` / `medium` / `high` / `xhigh` / `max`。透過 subprocess 獨立的環境變數傳遞，多 chain 平行不互相干擾 |
| `mode` | `auto`（全自動）或 `gate`（暫停審核：核准/編輯/退回/跳過） |
| `identity` | 寫入節點辦公室的 CLAUDE.md |
| `rules` | Markdown 檔案清單，複製到節點的 `.claude/rules/` |
| `timeout` | Subprocess 逾時秒數 |

### 跨節點引用

後續節點可以取用任何先前步驟的 output，不只上一步：

```yaml
- id: 03-report
  prompt: |
    整合以下資料：

    原始事實：{{node:01-extract}}
    分析結果：{{node:02-analyse}}

    ...產出最終報告。
```

組 prompt 時，每個 `{{node:<id>}}` tag 會被替換成 `<output id="<id>">...該節點 output.md 的內容...</output>`。每個完成節點的 output 也會自動複製到 `workspace/<node_id>.md`，內容太大時可以讓節點改用 Read tool 讀取。

### 範例 pipeline

完整範例見 [`skill/templates/example-prompt-chain.yaml`](skill/templates/example-prompt-chain.yaml)，涵蓋所有功能：inline 與外部 prompt、`{{node:<id>}}` 跨節點引用、節點級 `model` / `effort`、`identity`、`rules`、`auto` / `gate` 混用。

### 為什麼選 O-Team

- **每一步都是全新上下文** — 每個節點在自己的 `claude` 程序中執行。沒有上下文退化，團隊之間不會交叉汙染。第 5 步和第 1 步一樣精準。
- **在關鍵環節把關** — Gate 節點暫停讓你審核，支援核准、退回、編輯、跳過。Auto 節點全自動推進。同一 pipeline 自由混搭。
- **從任意節點接續** — `--from N` 從指定節點重新開始，自動沿用上次 run 的產出。可以帶入修改過的 input，也可以直接用先前結果。
- **完整稽核軌跡** — 每個節點保存組裝後的 prompt、原始串流事件、人類可讀日誌。出了什麼事、為什麼，一目了然。
- **即時狀態列** — Claude Code 狀態列即時顯示 pipeline 進度。當前節點在幹嘛、用了什麼工具、花了多少錢 — 執行中就能看到。
- **串流解析監控** — 型別安全的事件解析，追蹤 tool calls、agent 啟動、成本與耗時。Agent 生命週期連結（`tool_use_id` → `task_id`）提供精確的 subagent 可見性。

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
