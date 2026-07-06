# Lab 04 — Instructor notes (Voice Live demo)

Voice is a **demo**, not an individual build. The participants
already finished the hands-on bits (Functions-as-tools, MCP, custom
tool). The job here is to make a 10-minute voice demo that *works*
in the room.

---

## Days before the workshop

- **Confirm Voice Live SDK regional availability *and* realtime-model
  quota.** The demo uses an end-to-end speech-to-speech model
  (`gpt-realtime-1.5` by default). The realtime deployment is
  opt-in so participant environments do not fail on quota; enable it
  only after confirming quota:

  ```bash
  azd env set DEPLOY_REALTIME_MODEL true
  azd provision
  ```

  Without it Voice Live falls back to cascaded STT → LLM → TTS, which
  has ~1–3 s lag and no barge-in. If Sweden Central does not currently
  carry this model, swap the `realtimeModelName` param in `main.bicep`
  to whatever your region does carry (`gpt-realtime`,
  `gpt-4o-mini-realtime-preview`, `gpt-4o-realtime-preview`) or fall
  back to West Europe for the Foundry account and cross-region for the
  rest. **No ACS / no phone number** — the demo is purely
  internet-based: laptop microphone → WebSocket → Foundry Voice
  Live endpoint → laptop speakers.
- **Microphone + speakers** — confirmed in the OS. Test from the
  actual machine you'll demo from. No browser required (the demo
  script uses the system default audio device).
- **Network** — corporate guest WiFi will sometimes block the WS
  upgrade Voice Live uses. Try once on the venue's actual network
  beforehand if you can. Tethering off a phone is a reliable
  fallback.

## One-time setup on the demo machine

### Voice agent setup (none required for the slim demo)

The workshop demo uses the GA `azure-ai-voicelive>=1.1.0` SDK and
talks straight to the realtime *deployment* in your Foundry project
(`gpt-realtime-1.5` by default when `DEPLOY_REALTIME_MODEL=true`). It
bypasses Foundry's voice-agent
abstraction entirely, loading the same system prompt from
[`src/labs/prompts/voice_intake.md`](../../src/labs/prompts/voice_intake.md)
and passing it as `RequestSession.instructions`.

That means **you do not need to create a `noclar-voice-intake` agent
in the Foundry portal** for the demo to work. Auth is AAD-only —
the Foundry account key is rejected by Voice Live in this workshop's
configuration. `scripts/postdeploy-rbac.{ps1,sh}` grants the two
roles Voice Live requires: `Cognitive Services User` and
`Azure AI User` (a.k.a. *Foundry User*) on the Foundry account.

> The audience-facing pitch ("same agent, different channel") still
> holds: it's the same prompt and the same realtime deployment that
> back Lab 02's foundry agent for its chat channel. When a real
> product wires voice into the orchestrator, a back-end transcript
> handler hands the verbatim transcript to `noclar-intake` (JSON
> mode) for structured extraction. The voice loop's job is just the
> conversation.

### Demo machine env vars

The voice demo reads its config from `os.environ` (and from a `.env`
file in the repo root, via `python-dotenv`). If you ran `azd
provision` inside the devcontainer, the `.azure/` folder is on disk
and `azd env get-values` works on the host too — no need to re-run
anything in Azure.

bash:

```bash
pip install -r src/voice/requirements.txt
# Voice Live reuses the Foundry project endpoint — no separate voice
# resource and no key needed. Auth is via DefaultAzureCredential
# (your `az login` identity).
#
# Pull every env var azd recorded for this environment in one go:
azd env get-values > .env
# …then source it for the current shell (the demo also picks .env up
# automatically via python-dotenv, so this is only needed if you
# want them set for ad-hoc CLI commands):
set -a; source .env; set +a
```

PowerShell:

```powershell
pip install -r src/voice/requirements.txt
# Voice Live reuses the Foundry project endpoint — no separate voice
# resource and no key needed. Auth is via DefaultAzureCredential
# (your `az login` identity).
#
# Pull every env var azd recorded for this environment in one go:
azd env get-values | Out-File -Encoding utf8 .env
# …then load it into the current PowerShell session (the demo also
# picks .env up automatically via python-dotenv, so this is only
# needed if you want them set for ad-hoc CLI commands):
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([^#=]+?)\s*=\s*"?(.*?)"?\s*$') {
    [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
  }
}
```

The vars the demo actually reads:

- `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT` — Voice Live WS endpoint.
- `AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT` — realtime model deployment
  name (`gpt-realtime-1.5` by default when `DEPLOY_REALTIME_MODEL=true`).
- `AZURE_FUNCTION_APP_HOSTNAME`, `AZURE_FUNCTION_KEY` — for the
  governance `log_request` call at session start.

## Dry-run script (run the day before)

```bash
python -m src.voice.voice_agent_demo
```

- Speak your opening line (see below).
- Stopwatch from "go" to "first audible response" — should be < 3 s
  on the venue network. If > 5 s, you have a network issue worth
  diagnosing now rather than in the room.
- Speak the second intake line, watch the log blob land.
- **Tear down** any logs that contain dry-run PII so the participant
  Live-Metrics walk-through is clean.

## In-room checklist

- [ ] Microphone unmuted on the OS *and* in the SDK.
- [ ] Speakers loud enough for the back row.
- [ ] App Insights Live Metrics open on a second screen.
- [ ] Fallback MP4 (next bullet) at hand.
- [ ] You've muted notifications and Slack on the demo laptop.

## Fallback recording

If Voice Live fails on the day, drop in the pre-recorded MP4:

```
labs/04-integration-voice/assets/voice-demo-fallback.mp4
```

(Record this yourself during the dry-run; gitignored or
small-enough-to-commit depending on your repo's policy.)

## Opening line (verbatim)

> "Hello, this is the intake assistant. I have an intake from
> Contoso Manufacturing. The reporter says a sales manager
> negotiated a consultancy contract above the policy threshold
> without going through procurement. Can you take it from here?"

Keep this consistent with the chat opening lines used in Labs 01 /
02 so the audience gets the "same agent, different channel"
moment.

## Post-demo cleanup

- Stop the SDK session (Ctrl-C; confirm the process exited).
- If the demo blob contains PII, delete it:
  ```bash
  az storage blob delete --container-name logs --name <blob> ...
  ```
- No telephony costs to reconcile — the demo never leaves the
  internet path.
