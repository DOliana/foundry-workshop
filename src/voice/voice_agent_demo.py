"""Voice Live SDK demo (Block 4).

A small browser-mic-driven demo that:
  1. Calls `log_request` first (governance — voice channel).
  2. Connects to Voice Live with the existing `noclar-intake` agent.
  3. Streams audio in both directions through the default device.

Note: This is a *demo*, not a full lab. The C# ACSVoiceAgent repo is the
production-grade reference; this script keeps the workshop in a single
language (Python).

Run locally:
    pip install -r src/voice/requirements.txt
    python -m src.voice.voice_agent_demo
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from azure.identity.aio import DefaultAzureCredential

from src.agents.tools.functions_tools import log_request
from src.shared.config import get_settings


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
        # Connect with the existing intake agent so the prompt and tools are reused.
        async with client.connect(
            agent_name="noclar-intake",
            model=settings.foundry_model_deployment,
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
    log_request(conversation_id=conversation_id, channel="voice", locale="en-US")
    try:
        asyncio.run(_stream_voice(conversation_id))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
