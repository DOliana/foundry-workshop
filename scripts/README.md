# Scripts

| Script | Purpose | When to run |
|---|---|---|
| `seed_foundry_project.py` | Upload sample-docs, create AI Search index, register the 5 workshop agents | Once after `azd up`, then before Lab 02 |
| `provision-participants.ps1` | (Instructor only) Provision N participant RGs in the instructor's subscription | Day-of, only if a participant cannot run `azd up` themselves |
| `teardown-participants.ps1` | (Instructor only) Tear down the participant RGs | After the workshop |
| `deploy-functions.ps1` | Deploy the Functions app code (`azd deploy functions` wrapper) | After changing any code in `src/functions/` |

## Quickstart after `azd up`

```powershell
azd env get-values > .env
pip install -r src/agents/requirements.txt
python scripts/seed_foundry_project.py
./scripts/deploy-functions.ps1
```
