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

## Node Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | YES | Unique node identifier, format: `{NN}-{team-slug}` |
| `team` | string | YES | Team slug (must exist in registry) |
| `team_path` | string | YES | Absolute path to team directory |
| `mode` | string | YES | Execution mode: `"auto"` or `"gate"` |
| `prompt` | string | YES | Instructions for this node |
| `timeout` | integer | NO | Timeout in seconds (default: 1800) |

## Example

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

  - id: "03-writing-team"
    team: writing-team
    team_path: /Users/dev/projects/teams/writing-team
    mode: auto
    prompt: |
      將前一階段的架構設計轉化為完整的技術規格文件。
      遵循團隊格式規範。補充錯誤處理流程、部署架構與監控指標。
    timeout: 1800

  - id: "04-review-team"
    team: review-team
    team_path: /Users/dev/projects/teams/review-team
    mode: gate
    prompt: |
      審查前一階段產出的技術規格文件。
      驗證：API 設計一致性、資料模型完整性、
      是否過度工程化、遺漏的邊界情況。
      產出審查報告，將問題分為阻塞性與非阻塞性兩類。
    timeout: 1800
```

## Validation Rules

- `version` must be `"1"`
- `nodes` must be a non-empty array
- Each node `id` must be unique within the pipeline
- Each node `team` must exist in the global registry (`~/.o-team/registry.json`)
- Each node `team_path` must point to an existing directory with CLAUDE.md
- Each node `mode` must be `"auto"` or `"gate"`
- Empty `prompt` triggers a warning (node will rely solely on team CLAUDE.md)
- `timeout` must be a positive integer if provided
