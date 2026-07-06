# Scripts

| Script | Purpose | When to run |
| --- | --- | --- |
| `seed_foundry_project.py` | Upload sample-docs, create AI Search index, register the 5 workshop agents | Once after `azd up`, then before Lab 02 |
| `create-participant-users.ps1` | (Instructor only) Create numbered Entra users and grant each Owner on their matching numbered RG | Before the workshop, when using temporary lab users |
| `remove-participant-users.ps1` | (Instructor only) Delete numbered Entra users created for the workshop | After the workshop, when using temporary lab users |
| `provision-participants.ps1` | (Instructor only) Provision N participant RGs in the instructor's subscription | Day-of, only if a participant cannot run `azd up` themselves |
| `teardown-participants.ps1` | (Instructor only) Tear down the participant RGs | After the workshop |
| `deploy-functions.ps1` | Deploy the Functions app code (`azd deploy functions` wrapper) | After changing any code in `src/functions/` |

## Quickstart after `azd up`

```powershell
azd env get-values > .env
pip install -r src/labs/requirements.txt
python scripts/seed_foundry_project.py
./scripts/deploy-functions.ps1
```
