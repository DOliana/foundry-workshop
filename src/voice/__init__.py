"""Voice Live demo package.

Importing this package eagerly loads `.env` into `os.environ` so that
`python -m src.voice.voice_agent_demo` picks up the values written by
Lab 00 without the participant having to source the file from the shell.
"""

from src.shared.config import load_env as _load_env

_load_env()
