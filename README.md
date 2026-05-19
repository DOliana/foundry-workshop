# Azure AI Foundry — Hands-On Workshop

A hands-on workshop exploring the core capabilities of **Azure AI Foundry** through a realistic assurance / compliance scenario: building an AI-assisted document intake and assessment workflow.

> The scenario (a compliance intake process) is the vehicle — the goal is hands-on experience with the platform capabilities: multi-agent orchestration, document grounding, voice interaction, custom integration, and evaluation.

---

## What you'll learn

By the end of the day you will have built and run a multi-agent workflow that demonstrates:

1. **Voice & chat interaction** — the same agent works across both channels without re-training.
2. **Document grounding (RAG)** — agents answer with citations from a knowledge base; structured facts are extracted from long documents using Content Understanding.
3. **Multi-agent orchestration** — specialist agents (intake, classification, drafting) are coordinated with explicit **human-in-the-loop** approval gates.
4. **Custom integration via Azure Functions** — persistence, governance logging, and reviewer routing wired as agent tools.
5. **Observability & evaluation** — tracing from request #1, content safety guardrails, and an evaluation run against a frozen dataset.

The scenario throughout is a document-heavy compliance intake process — chosen because it exercises all five capabilities in a realistic way.

---

## Repo layout

```
foundry-workshop/
├── infra/                  Bicep infrastructure (azd)
├── src/
│   ├── functions/          Python Azure Functions app
│   ├── agents/             Microsoft Agent Framework agents + tools
│   ├── voice/              Voice Live SDK demo
│   └── shared/             Schemas, config helpers
├── data/
│   ├── sample-docs/        Fictional NOCLAR corpus (DE/EN)
│   ├── memo-template/      German Initial Assessment Memo template
│   └── eval/               Evaluation datasets
├── labs/                   Step-by-step lab guides (one folder per block)
└── scripts/                Helper scripts (provisioning, deployment, indexing)
```

---

## Prerequisites

- **Azure subscription** with permission to create resources
- **Tools:**
  - [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) `>= 2.60`
  - [Azure Developer CLI (azd)](https://aka.ms/install-azd) `>= 1.10`
  - [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) v4
  - Python 3.11+
  - Git
- **Quota:** the deployment uses **Sweden Central** and requests a *modest* TPM allocation for `gpt-4.1-mini`. If your subscription has no quota there, see [`labs/00-setup/README.md`](labs/00-setup/README.md) for fallback options.

See [`PARTICIPANT-SETUP.md`](PARTICIPANT-SETUP.md) for the 1-page quickstart.

---

## Deploy the infrastructure

The Bicep targets a **resource group** (not a subscription). Pre-create
the RG, then provision into it:

```bash
azd auth login
./scripts/provision-rg.sh -g rg-foundry-<yourinitials> -l swedencentral
# or, on Windows:
./scripts/provision-rg.ps1 -ResourceGroup rg-foundry-<yourinitials> -Location swedencentral
```

The instructor then grants per-participant data-plane roles inside
the RG with [`scripts/postdeploy-rbac.{ps1,sh}`](scripts/postdeploy-rbac.ps1).

This provisions, in **Sweden Central**:

| Resource | Purpose |
|---|---|
| Azure AI Foundry account + project | The hub for all agent work |
| `gpt-4.1-mini` model deployment | Default chat model (TPM capped to leave room for your own deploys) |
| `text-embedding-3-small` model deployment | Embedding model for the Lab 03 hybrid index |
| Azure AI Search (Basic) | Hybrid (vector + keyword + filter) knowledge base |
| Storage Account | Sample docs, assessment outputs, function state |
| Azure Functions (Flex, Python 3.11) | Persistence + governance logging + reviewer routing |
| Azure Communication Services | Voice Live SDK demo |
| Log Analytics + Application Insights | Tracing & telemetry from request #1 |
| Managed Identity + RBAC | Functions ↔ Foundry/Search/Storage pre-wired |

Total provisioning time: ~10 minutes.

---

## Workshop agenda

| Time | Block | Lab |
|---|---|---|
| 09:00–09:20 | Welcome & setup | [`labs/00-setup`](labs/00-setup) |
| 09:20–10:45 | Block 1 — Your First Agent with Built-In Observability | [`labs/01-first-agent`](labs/01-first-agent) |
| 11:00–12:15 | Block 2 — Multi-Agent Orchestration & HITL | [`labs/02-orchestration-hitl`](labs/02-orchestration-hitl) |
| 13:15–14:30 | Block 3 — Document Understanding & Knowledge Grounding | [`labs/03-knowledge-grounding`](labs/03-knowledge-grounding) |
| 14:45–16:00 | Block 4 — Voice Interaction & Custom Integration | [`labs/04-integration-voice`](labs/04-integration-voice) |
| 16:00–16:45 | Block 5 — Evaluation, Governance & Production Readiness | [`labs/05-evaluation`](labs/05-evaluation) |

---

## Clean up

```bash
azd down --purge
```

---

## Acknowledgements

Lab content draws on Microsoft sample repositories — see [`docs/SOURCES.md`](docs/SOURCES.md) for attribution.

## Pre-workshop dry-run

Before sharing the repo with participants, the instructor must complete [`docs/DRY-RUN-CHECKLIST.md`](docs/DRY-RUN-CHECKLIST.md) in a clean subscription.
