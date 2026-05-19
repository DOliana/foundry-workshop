"""Voice Live SDK demo (Block 4).

A small browser-mic-driven demo that:
  1. Calls `log_request` first (governance — voice channel).
  2. Connects to Voice Live with the existing `noclar-intake` agent.
  3. Streams audio in both directions through the default device.

Note: This is a *demo*, not a full lab. The workshop deliberately avoids
Azure Communication Services (telephony) — the demo runs entirely over the
internet via a WebSocket from the demo laptop to the Foundry Voice Live
endpoint, using the local microphone and speakers. No phone number, no
ACS resource, no PSTN.

Run locally:
    pip install -r src/voice/requirements.txt
    python -m src.voice.voice_agent_demo
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import httpx
from azure.identity.aio import DefaultAzureCredential

from src.shared.config import get_settings


def _log_request(conversation_id: str, channel: str = "voice", locale: str = "en-US") -> None:
    host = os.environ.get("AZURE_FUNCTION_APP_HOSTNAME")
    if not host:
        return
    if not host.startswith("http"):
        host = f"https://{host}"
    key = os.environ.get("AZURE_FUNCTION_KEY")
    params = {"code": key} if key else {}
    try:
        httpx.post(
            f"{host}/api/log_request",
            json={"conversation_id": conversation_id, "channel": channel, "locale": locale},
            params=params,
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"log_request failed (non-fatal for demo): {exc!r}", file=sys.stderr)


async def _stream_voice(conversation_id: str) -> None:
    """Connect to Voice Live and stream microphone audio.

    This uses `azure-ai-voicelive` (preview). The package + API surface may
    change; the lab README points participants at the latest sample.
    """
    try:
        from azure.ai.voicelive.aio import VoiceLiveClient  # type: ignore
    except ImportError:
        print(
            "azure-ai-voicelive not installed. Install with:\n"
            "    pip install azure-ai-voicelive --pre\n",
            file=sys.stderr,
        )
        return

    settings = get_settings()
    credential = DefaultAzureCredential()

    async with VoiceLiveClient(
        endpoint=settings.foundry_project_endpoint,
        credential=credential,
    ) as client:
        # Connect with `noclar-voice-intake` — a *separate* agent from the
        # JSON-mode `noclar-intake` used by the Lab 02 orchestrator. The
        # voice channel needs conversational, plain-text replies (the TTS
        # reads them aloud), so the voice agent ships with its own prompt
        # (`src/agents/prompts/voice_intake.md`) and Response format=Text.
        #
        # `model` must reference a *realtime* (speech-to-speech) deployment
        # — provisioned by infra/modules/foundry.bicep as
        # `gpt-4o-mini-realtime-preview` and surfaced via the
        # AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT env var. Without a realtime
        # model Voice Live falls back to cascaded STT → LLM → TTS, which
        # is noticeably laggy and lacks barge-in.
        realtime_deployment = (
            settings.foundry_realtime_deployment
            or os.environ.get("AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT")
        )
        if not realtime_deployment:
            print(
                "AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT is not set. Re-run "
                "`azd env get-values > .env` after `azd provision`, or "
                "deploy a realtime model manually.",
                file=sys.stderr,
            )
            return
        async with client.connect(
            agent_name="noclar-voice-intake",
            model=realtime_deployment,
            voice="alloy",
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            turn_detection={"type": "server_vad", "threshold": 0.5},
        ) as session:
            print(f"--- voice conversation {conversation_id} ---")
            print("Start speaking. Ctrl+C to quit.\n")
            await session.start_microphone()
            async for event in session:
                if event.type == "response.audio_transcript.delta":
                    print(event.delta, end="", flush=True)
                elif event.type == "response.done":
                    print()


def main() -> None:
    conversation_id = str(uuid.uuid4())
    _log_request(conversation_id=conversation_id, channel="voice", locale="en-US")
    try:
        asyncio.run(_stream_voice(conversation_id))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
