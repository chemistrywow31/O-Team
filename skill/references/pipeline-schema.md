---
name: Pipeline YAML Schema
description: Schema definition for O-Team pipeline configuration files
---

# Pipeline YAML Schema

## Top-level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | YES | Schema version, currently `"1"` |
| `name` | string | YES | Pipeline display name |
| `slug` | string | YES | Kebab-case identifier (auto-generated from name) |
| `objective` | string | NO | Overall pipeline objective description |
| `created_at` | string | YES | ISO 8601 timestamp of creation |
| `nodes` | array | YES | Ordered list of pipeline nodes (min 1) |

## Node Types

A pipeline supports two node types: **team nodes** and **prompt nodes**. Both can be mixed in the same pipeline.

### Team Node Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | YES | Unique node identifier, format: `{NN}-{team-slug}` |
| `team` | string | YES | Team slug (must exist in registry) |
| `team_path` | string | YES | Absolute path to team directory |
| `mode` | string | YES | Execution mode: `"auto"` or `"gate"` |
| `prompt` | string | NO | Instructions for this node |
| `timeout` | integer | NO | Timeout in seconds (default: 1800) |

### Prompt Node Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | YES | Unique node identifier |
| `mode` | string | YES | Execution mode: `"auto"` or `"gate"` |
| `prompt` | string | * | Inline prompt text (* one of `prompt` or `prompt_file` required) |
| `prompt_file` | string | * | Path to external .md file (resolved relative to pipeline YAML) |
| `identity` | string | NO | Written as CLAUDE.md in the node's office folder |
| `rules` | array | NO | List of rule file paths to copy into the node's .claude/rules/ |
| `timeout` | integer | NO | Timeout in seconds (default: 1800) |

## Examples

### Team Pipeline

```yaml
version: "1"
name: Tech Spec Pipeline
slug: tech-spec-pipeline
objective: Design a SaaS subscription management system technical specification
created_at: "2026-03-27T10:00:00+08:00"

nodes:
  - id: "01-research-team"
    team: research-team
    team_path: /Users/dev/projects/teams/research-team
    mode: auto
    prompt: |
      根據提供的主題，研究主流 SaaS 訂閱管理系統的架構模式。
      分析 Stripe Billing、Chargebee、Recurly 的技術實作。
      產出可行性分析報告，涵蓋架構選型、資料模型與整合模式。
    timeout: 1800

  - id: "02-design-team"
    team: design-team
    team_path: /Users/dev/projects/teams/design-team
    mode: gate
    prompt: |
      根據前一階段的研究報告，進行系統架構設計。
      包含：架構圖（mermaid）、核心 API 端點設計、
      資料模型定義（subscription/billing/invoice）、
      以及 Stripe 整合方案。以穩健成熟的架構模式為優先。
    timeout: 1800
```

### Prompt Chain

```yaml
version: "1"
name: Quick Analysis
slug: quick-analysis
objective: 快速分析一個技術主題

nodes:
  - id: 01-research
    mode: auto
    prompt: |
      你是一位技術研究員。
      根據提供的主題，蒐集相關技術現況、工具與框架，
      產出結構化的研究摘要。

  - id: 02-analyze
    mode: auto
    prompt: |
      你是一位資深技術分析師。
      根據前一階段的研究摘要，進行 SWOT 分析，
      找出關鍵決策點和風險因素。

  - id: 03-recommend
    mode: gate
    prompt: |
      你是一位技術顧問。
      根據前一階段的分析結果，產出具體可執行的建議報告。
      每項建議必須附上理由和預期效果。
```

### Mixed Pipeline (Team + Prompt)

```yaml
version: "1"
name: Research then Review
slug: research-then-review
objective: Research with a team, then lightweight review with prompts

nodes:
  - id: 01-research
    team: research-team
    team_path: /path/to/research-team
    mode: auto
    prompt: "Research the topic thoroughly."

  - id: 02-quick-review
    mode: gate
    prompt: |
      你是一位資深審查員。
      審查前一階段的研究報告，檢查完整性和準確性。
    identity: |
      Focus on factual accuracy and source quality.
      Flag unsupported claims.
```

### Prompt Chain with External Files

```yaml
version: "1"
name: Content Pipeline
slug: content-pipeline
objective: Content creation workflow

nodes:
  - id: 01-outline
    mode: auto
    prompt_file: ./prompts/01-outline.md

  - id: 02-draft
    mode: auto
    prompt_file: ./prompts/02-draft.md
    rules:
      - ./rules/writing-style.md

  - id: 03-review
    mode: gate
    prompt_file: ./prompts/03-review.md
    identity: |
      You are a senior editor.
      Apply AP style guidelines.
```

## Validation Rules

- `version` must be `"1"`
- `nodes` must be a non-empty array
- Each node `id` must be unique within the pipeline
- Each node must have `team` (team node) OR `prompt`/`prompt_file` (prompt node)
- Team nodes: `team` must exist in registry, `team_path` must point to directory with CLAUDE.md
- Prompt nodes: `prompt_file` must point to an existing file (resolved relative to pipeline YAML)
- Prompt nodes: `rules` entries must point to existing files
- Each node `mode` must be `"auto"` or `"gate"`
- Empty `prompt` on team nodes triggers a warning (will rely on team CLAUDE.md + entry skill)
- `timeout` must be a positive integer if provided
