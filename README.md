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

```text
foundry-workshop/
├── infra/                  Bicep infrastructure (azd)
├── src/
│   ├── functions/          Python Azure Functions app
│   ├── labs/               Lab code (one folder per block) + shared agent prompts
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
- **Quota:** the deployment uses **Sweden Central** and requests a *modest* TPM allocation for `gpt-5-mini`. If your subscription has no quota there, see [`labs/00-setup/README.md`](labs/00-setup/README.md) for fallback options.

See [`labs/00-setup/README.md`](labs/00-setup/README.md) for the lab-by-lab walkthrough.

---

## Deploy the infrastructure

Run every `azd` command from the cloned `foundry-workshop` root directory —
the directory that contains [`azure.yaml`](azure.yaml). If your terminal is in a
lab folder such as `labs/00-setup`, run `cd ../..` first.

The Bicep targets a **resource group** (not a subscription). Pre-create
the RG, then provision into it:

```bash
azd auth login
./scripts/provision-rg.sh -g rg-foundry-01 -l swedencentral
# or, on Windows:
./scripts/provision-rg.ps1 -ResourceGroup rg-foundry-01 -Location swedencentral
```

The script is intentional for the workshop flow. It creates or reuses the
participant RG, sets `AZURE_RESOURCE_GROUP` in the `azd` environment, and
then runs `azd provision` against that RG. This keeps Lab 00 infrastructure-only:
resources are created, but the Functions app code declared in `azure.yaml` is
not deployed until the later integration labs.

Setting `AZURE_RESOURCE_GROUP` is important: if it is missing, `azd` derives a
resource group name from the azd environment name. For example, an azd env named
`rg-fdry-ws-local-devc` can produce a resource group named
`rg-rg-fdry-ws-local-devc`. The provision script avoids that by treating the
resource group name and the local azd environment name as separate values.

If you are doing a solo dry run and want the full application deployed in one
step, `azd up` may be fine after selecting the right subscription and resource
group. Before running `azd up`, set `AZURE_RESOURCE_GROUP` explicitly or choose
an azd environment name that is not already prefixed with `rg-`. For participant
setup, use the provision script so the deployment stays inside the assigned RG
and follows the staged lab flow.

The instructor then grants per-participant data-plane roles inside
the RG with [`scripts/postdeploy-rbac.{ps1,sh}`](scripts/postdeploy-rbac.ps1).

This provisions, in **Sweden Central**:

| Resource | Purpose |
| --- | --- |
| Azure AI Foundry account + project | The hub for all agent work |
| `gpt-5-mini` model deployment | Default chat model (TPM capped to leave room for your own deploys) |
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
| --- | --- | --- |
| 09:00–09:20 | Welcome & setup | [`labs/00-setup`](labs/00-setup) |
| 09:20–10:45 | Block 1 — Your First Agent with Built-In Observability | [`labs/01-first-agent`](labs/01-first-agent) |
| 11:00–12:15 | Block 2 — Multi-Agent Orchestration & HITL | [`labs/02-orchestration-hitl`](labs/02-orchestration-hitl) |
| 13:15–14:30 | Block 3 — Document Understanding & Knowledge Grounding | [`labs/03-knowledge-grounding`](labs/03-knowledge-grounding) |
| 14:45–16:00 | Block 4 — Voice Interaction & Custom Integration | [`labs/04-integration-voice`](labs/04-integration-voice) |
| 16:00–16:45 | Block 5 — Evaluation, Governance & Production Readiness | [`labs/05-evaluation`](labs/05-evaluation) |

---

## Clean up

Run cleanup from the `foundry-workshop` root directory as well:

```bash
azd down --purge
```

---

## Acknowledgements

Lab content draws on Microsoft sample repositories — see [`docs/SOURCES.md`](docs/SOURCES.md) for attribution.

## Pre-workshop dry-run

Before sharing the repo with participants, the instructor must complete [`docs/DRY-RUN-CHECKLIST.md`](docs/DRY-RUN-CHECKLIST.md) in a clean subscription.
