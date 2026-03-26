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
      Research mainstream SaaS subscription management system architecture patterns.
      Analyze Stripe Billing, Chargebee, and Recurly technical implementations.
      Produce a feasibility analysis report covering architecture choices,
      data models, and integration patterns.
    timeout: 1800

  - id: "02-design-team"
    team: design-team
    team_path: /Users/dev/projects/teams/design-team
    mode: gate
    prompt: |
      Based on the research report in input.md, design the system architecture.
      Include: architecture diagram (mermaid), core API endpoint design,
      data model definitions (subscription/billing/invoice),
      and Stripe integration approach.
      Prioritize proven architecture patterns over novel approaches.
    timeout: 1800

  - id: "03-writing-team"
    team: writing-team
    team_path: /Users/dev/projects/teams/writing-team
    mode: auto
    prompt: |
      Transform the architecture design in input.md into a complete
      technical specification document. Follow team formatting standards.
      Add error handling flows, deployment architecture,
      and monitoring metrics.
    timeout: 1800

  - id: "04-review-team"
    team: review-team
    team_path: /Users/dev/projects/teams/review-team
    mode: gate
    prompt: |
      Review the technical specification in input.md.
      Verify: API design consistency, data model completeness,
      over-engineering detection, missing edge cases.
      Produce a review report with blocking and non-blocking issues.
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
