"""One-shot helper: prefix every non-empty line in the listed per-lab files
with `# ` so they ship as TODO stubs.

Run once after a dry-run when the lab files are sitting in their
"uncommented, working" state. Idempotent — re-running blindly will
double-prefix code that's already commented.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

FULL_COMMENT = [
    "src/functions/persist_assessment.py",
    "src/functions/notify_reviewer.py",
    "src/functions/process_reviewer.py",
    "src/functions/log_request.py",
    "src/agents/lab02/orchestrator.py",
    "src/agents/lab02/functions_tools.py",
    "src/agents/lab03/ingest_corpus.py",
    "src/agents/lab03/ground_query.py",
]


def comment_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        stripped = line.lstrip()
        if stripped == "" or stripped == "\n":
            out.append(line)
        else:
            # Preserve the trailing newline (if any) so we don't collapse it.
            if line.endswith("\n"):
                out.append("# " + line[:-1] + "\n")
            else:
                out.append("# " + line)
    path.write_text("".join(out), encoding="utf-8")


def main() -> None:
    for rel in FULL_COMMENT:
        p = REPO / rel
        if not p.exists():
            print(f"skip (missing): {rel}")
            continue
        comment_file(p)
        print(f"commented: {rel}")


if __name__ == "__main__":
    main()
