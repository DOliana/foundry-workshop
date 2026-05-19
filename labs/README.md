# Workshop labs — index

Five hands-on labs that build a small NOCLAR (Non-Compliance with Laws
and Regulations) Initial Assessment workflow on Azure AI Foundry,
introducing one Azure service per lab.

| # | Lab | Block | Service introduced | Duration |
|---|---|---|---|---|
| 00 | [Setup & Verification](./00-setup/README.md) | Welcome | Azure AI Foundry, App Insights | 20 min |
| 01 | [Your First Agent](./01-first-agent/README.md) | 1 | Portal-only (no Functions yet) | 50 min |
| 02 | [Orchestration & HITL](./02-orchestration-hitl/README.md) | 2 | Azure Functions, Storage queue | 60 min |
| 03 | [Knowledge Grounding](./03-knowledge-grounding/README.md) | 3 | Azure AI Search, Content Understanding | 60 min |
| 04 | [Integration & Voice](./04-integration-voice/README.md) | 4 | Functions-as-tools, MCP, Voice Live | 60 min |
| 05 | [Evaluation & Governance](./05-evaluation/README.md) | 5 | Evaluation SDK + portal | 50 min |

The story stays the same across labs: a compliance intake team
receives a tip, an agent extracts structured facts, a classifier maps
those facts to regulatory norms, a drafter writes an Initial
Assessment Memo, a human approves it, and it is persisted with an
auditable trail.

Each lab starts with **"uncomment these files"** — the per-lab Python
and Azure Functions code ships fully commented in this repo. You read
the file, then uncomment it, then run it. The first thing that ever
hits a deployed resource is you doing it yourself.

## Instructor docs

- [`00-setup/INSTRUCTOR.md`](./00-setup/INSTRUCTOR.md) — RG flow,
  model quota, `postdeploy-rbac.{ps1,sh}`.
- [`04-integration-voice/INSTRUCTOR.md`](./04-integration-voice/INSTRUCTOR.md)
  — Voice Live demo prep, dry-run, fallback recording.
