"""Voice Live demo (Block 4) — workshop version.

Adapted from Microsoft's `model-quickstart.py` Voice Live sample
(https://github.com/microsoft-foundry/voicelive-samples/), trimmed to
the bits the workshop needs:

* Reads the Foundry endpoint + realtime deployment from our settings.
* Loads the `noclar-voice-intake` system prompt from disk.
* Opens a governance log entry before the WebSocket session starts.

Run on the **host** (not the devcontainer — audio devices aren't
forwarded):

    pip install -r src/voice/requirements.txt
    python -m src.voice.voice_agent_demo
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import queue
import sys
import uuid
from pathlib import Path
from typing import Optional, Union

import httpx

from src.shared.config import get_settings

# 24 kHz PCM16 mono — what Voice Live expects and emits.
SAMPLE_RATE = 24_000
CHUNK_MS = 50
CHUNK_FRAMES = SAMPLE_RATE * CHUNK_MS // 1000  # 1200 frames

logger = logging.getLogger(__name__)


def _log_request(conversation_id: str) -> None:
    """Open the workshop's governance log entry for this voice session."""
    host = os.environ.get("AZURE_FUNCTION_APP_HOSTNAME")
    if not host:
        return
    if not host.startswith("http"):
        host = f"https://{host}"
    key = os.environ.get("AZURE_FUNCTION_KEY")
    try:
        httpx.post(
            f"{host}/api/log_request",
            json={
                "conversation_id": conversation_id,
                "channel": "voice",
                "locale": "en-US",
            },
            params={"code": key} if key else None,
            timeout=15,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"log_request failed (non-fatal for demo): {exc!r}", file=sys.stderr)


class AudioProcessor:
    """Mic capture + speaker playback, modelled on the MS sample.

    PyAudio drives capture/playback on its own threads; capture pushes
    audio into the active asyncio loop, playback pulls from a thread-safe
    queue. Skips on barge-in are sequence-numbered so already-queued
    packets are dropped instead of played out after the user interrupts.
    """

    class _Packet:
        def __init__(self, seq_num: int, data: Optional[bytes]) -> None:
            self.seq_num = seq_num
            self.data = data

    def __init__(self, connection) -> None:
        import pyaudio

        self.connection = connection
        self.audio = pyaudio.PyAudio()
        self.format = pyaudio.paInt16
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        self.playback_queue: "queue.Queue[AudioProcessor._Packet]" = queue.Queue()
        self.playback_base = 0
        self.next_seq_num = 0
        self.loop: asyncio.AbstractEventLoop

    def start_capture(self) -> None:
        import pyaudio

        if self.input_stream:
            return
        self.loop = asyncio.get_event_loop()

        def _capture_callback(in_data, _frames, _time_info, _status):
            audio_b64 = base64.b64encode(in_data).decode("utf-8")
            asyncio.run_coroutine_threadsafe(
                self.connection.input_audio_buffer.append(audio=audio_b64), self.loop
            )
            return (None, pyaudio.paContinue)

        self.input_stream = self.audio.open(
            format=self.format,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_FRAMES,
            stream_callback=_capture_callback,
        )

    def start_playback(self) -> None:
        import pyaudio

        if self.output_stream:
            return
        remaining = bytes()

        def _playback_callback(_in_data, frame_count, _time_info, _status):
            nonlocal remaining
            frame_count *= pyaudio.get_sample_size(pyaudio.paInt16)
            out = remaining[:frame_count]
            remaining = remaining[frame_count:]
            while len(out) < frame_count:
                try:
                    pkt = self.playback_queue.get_nowait()
                except queue.Empty:
                    out += bytes(frame_count - len(out))
                    continue
                if not pkt or not pkt.data:
                    break
                if pkt.seq_num < self.playback_base:
                    if remaining:
                        remaining = bytes()
                    continue
                take = frame_count - len(out)
                out += pkt.data[:take]
                remaining = pkt.data[take:]
            return (
                (out, pyaudio.paContinue)
                if len(out) >= frame_count
                else (out, pyaudio.paComplete)
            )

        self.output_stream = self.audio.open(
            format=self.format,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_FRAMES,
            stream_callback=_playback_callback,
        )

    def _next_seq(self) -> int:
        seq = self.next_seq_num
        self.next_seq_num += 1
        return seq

    def queue_audio(self, data: Optional[bytes]) -> None:
        self.playback_queue.put(AudioProcessor._Packet(self._next_seq(), data))

    def skip_pending_audio(self) -> None:
        self.playback_base = self._next_seq()

    def shutdown(self) -> None:
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
        if self.output_stream:
            self.skip_pending_audio()
            self.queue_audio(None)
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None
        if self.audio:
            self.audio.terminate()


async def _stream_voice(conversation_id: str) -> None:
    try:
        from azure.ai.voicelive.aio import connect
        from azure.ai.voicelive.models import (
            AudioEchoCancellation,
            AudioNoiseReduction,
            AzureStandardVoice,
            InputAudioFormat,
            Modality,
            OutputAudioFormat,
            RequestSession,
            ServerEventType,
            ServerVad,
        )
        from azure.core.credentials import AzureKeyCredential
        from azure.core.credentials_async import AsyncTokenCredential
        from azure.identity.aio import DefaultAzureCredential
    except ImportError as exc:
        print(
            f"Voice deps not installed ({exc}). Install with:\n"
            "    pip install -r src/voice/requirements.txt",
            file=sys.stderr,
        )
        return

    settings = get_settings()
    # Voice Live accepts either a managed catalog model (`gpt-realtime`)
    # or a Foundry *deployment name* if you've deployed a realtime model
    # into your project. The workshop provisions `gpt-realtime-1.5` as a
    # deployment, so default to that.
    realtime_model = (
        os.environ.get("AZURE_VOICELIVE_MODEL")
        or settings.foundry_realtime_deployment
        or os.environ.get("AZURE_AI_FOUNDRY_REALTIME_DEPLOYMENT")
        or "gpt-realtime"
    )

    prompt_path = (
        Path(__file__).resolve().parents[1] / "agents" / "prompts" / "voice_intake.md"
    )
    instructions = prompt_path.read_text(encoding="utf-8")

    # Voice Live (GA SDK 1.1.0) takes the Foundry/AIServices account
    # endpoint directly as HTTPS — the SDK switches scheme to wss and
    # appends `/voice-live/realtime` itself. Strip the project path; the
    # account-level URL is what `/voice-live/realtime` is rooted at.
    account_endpoint = (
        settings.foundry_project_endpoint.split("/api/projects/", 1)[0].rstrip("/") + "/"
    )
    voicelive_endpoint = os.environ.get("AZURE_VOICELIVE_ENDPOINT", account_endpoint)

    # AAD via async DefaultAzureCredential. Voice Live in this workshop
    # rejects the Foundry account key (403); AAD with `Cognitive Services
    # User` + `Azure AI User` (Foundry User) is required.
    credential: Union[AzureKeyCredential, AsyncTokenCredential] = DefaultAzureCredential()

    print(f"--- voice conversation {conversation_id} ---")
    print(f"Connecting to Voice Live at {voicelive_endpoint} (model={realtime_model}) ...")

    active_response = {"flag": False}

    async with connect(
        endpoint=voicelive_endpoint,
        credential=credential,
        model=realtime_model,
    ) as conn:
        ap = AudioProcessor(conn)
        try:
            await conn.session.update(
                session=RequestSession(
                    modalities=[Modality.TEXT, Modality.AUDIO],
                    instructions=instructions,
                    voice=AzureStandardVoice(name="en-US-Ava:DragonHDLatestNeural"),
                    input_audio_format=InputAudioFormat.PCM16,
                    output_audio_format=OutputAudioFormat.PCM16,
                    turn_detection=ServerVad(
                        threshold=0.5,
                        prefix_padding_ms=300,
                        silence_duration_ms=500,
                    ),
                    input_audio_echo_cancellation=AudioEchoCancellation(),
                    input_audio_noise_reduction=AudioNoiseReduction(
                        type="azure_deep_noise_suppression"
                    ),
                )
            )
            ap.start_playback()

            print("\n" + "=" * 60)
            print("🎤 Voice assistant ready — start speaking. Ctrl+C to quit.")
            print("=" * 60 + "\n")

            async for event in conn:
                etype = event.type
                if etype == ServerEventType.SESSION_UPDATED:
                    ap.start_capture()
                elif etype == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
                    print("🎤 Listening...")
                    ap.skip_pending_audio()
                    if active_response["flag"]:
                        try:
                            await conn.response.cancel()
                        except Exception as exc:  # noqa: BLE001
                            if "no active response" not in str(exc).lower():
                                logger.warning("Cancel failed: %s", exc)
                elif etype == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
                    print("🤔 Processing...")
                elif etype == ServerEventType.RESPONSE_CREATED:
                    active_response["flag"] = True
                elif etype == ServerEventType.RESPONSE_AUDIO_DELTA:
                    ap.queue_audio(event.delta)
                elif etype == ServerEventType.RESPONSE_DONE:
                    active_response["flag"] = False
                elif etype == ServerEventType.ERROR:
                    msg = event.error.message
                    if "no active response" not in msg.lower():
                        print(f"❌ {msg}", file=sys.stderr)
        finally:
            ap.shutdown()
            await credential.close()


def main() -> None:
    conversation_id = str(uuid.uuid4())
    _log_request(conversation_id)
    try:
        asyncio.run(_stream_voice(conversation_id))
    except KeyboardInterrupt:
        print("\n👋 Voice assistant shut down. Goodbye!")


if __name__ == "__main__":
    main()
