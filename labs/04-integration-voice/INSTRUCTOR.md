# Lab 04 — Instructor notes (Voice Live demo)

Voice is a **demo**, not an individual build. The participants
already finished the hands-on bits (Functions-as-tools, MCP, custom
tool). The job here is to make a 10-minute voice demo that *works*
in the room.

---

## Days before the workshop

- **Confirm Voice Live SDK regional availability *and* realtime-model
  quota.** The demo uses an end-to-end speech-to-speech model
  (`gpt-4o-mini-realtime-preview` by default — provisioned by
  `infra/modules/foundry.bicep`). Without it Voice Live falls back to
  cascaded STT → LLM → TTS, which has ~1–3 s lag and no barge-in. If
  Sweden Central does not currently carry this model, swap the
  `realtimeModelName` param in `main.bicep` to whatever your region
  does carry (`gpt-realtime`, `gpt-4o-realtime-preview`) or fall back
  to West Europe for the Foundry account and cross-region for the
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

### Create the `noclar-voice-intake` agent (one-off, before the workshop)

The voice demo uses a **separate** agent from the JSON-mode
`noclar-intake` used in Labs 01/02. Voice needs plain-text,
conversational replies because the realtime TTS speaks whatever the
agent emits — JSON-as-audio is unusable.

In the Foundry portal, **Build → Agents → + New agent**:

- **Name:** `noclar-voice-intake`
- **Model deployment:** the realtime deployment (default
  `gpt-4o-mini-realtime-preview` — value of
  `AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT`)
- **Response format:** **Text** (the default — do *not* switch to
  JSON object)
- **Instructions:** paste the contents of
  [`src/agents/prompts/voice_intake.md`](../../src/agents/prompts/voice_intake.md)
- Tools / Knowledge: (none) — voice scope is intake conversation only

> The voice agent shares no state with `noclar-intake`. That is
> intentional: when a real product wires voice into the orchestrator,
> a back-end transcript handler hands the verbatim transcript to
> `noclar-intake` (JSON mode) for structured extraction. The voice
> agent's job is just the conversation.

### Demo machine env vars

```bash
pip install -r src/voice/requirements.txt
# Voice Live reuses the Foundry project endpoint — no separate voice
# resource and no key needed. Auth is via DefaultAzureCredential
# (your `az login` identity).
export AZURE_AI_FOUNDRY_PROJECT_ENDPOINT=...    # from `azd env get-values`
export AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT=... # provisioned by Bicep
export AZURE_FUNCTION_APP_HOSTNAME=...          # for the log_request call
export AZURE_FUNCTION_KEY=...
```

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
