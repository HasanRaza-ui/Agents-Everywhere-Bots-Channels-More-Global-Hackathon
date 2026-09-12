"""Probe the vision model against a fixture, before src/observer.py exists.

    uv run python scripts/try_observer.py tests/fixtures/lying_floor_1.jpg
    uv run python scripts/try_observer.py tests/fixtures/*.jpg

Prints the raw JSON and the latency for each frame. Use it to tune prompts/observe.md
without touching anyone else's files.
"""
import base64
import json
import pathlib
import sys
import time

from openai import OpenAI

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.config import load_settings, next_openai_key  # noqa: E402

import os  # noqa: E402

load_settings()
PROMPT = pathlib.Path("prompts/observe.md").read_text(encoding="utf-8")
MODEL = os.getenv("VISION_MODEL", "").strip()
if not MODEL:
    raise SystemExit("VISION_MODEL is not set in .env")


def observe(path: pathlib.Path) -> tuple[dict | str, float]:
    b64 = base64.b64encode(path.read_bytes()).decode()
    client = OpenAI(api_key=next_openai_key())
    started = time.perf_counter()
    r = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this frame. No prior description available."},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"}},
            ]},
        ],
    )
    ms = (time.perf_counter() - started) * 1000
    raw = r.choices[0].message.content
    try:
        return json.loads(raw), ms
    except json.JSONDecodeError:
        return raw, ms


def main() -> None:
    paths = [pathlib.Path(p) for p in sys.argv[1:]] or sorted(pathlib.Path("tests/fixtures").glob("*.jpg"))
    if not paths:
        raise SystemExit("no fixtures — run scripts/capture_fixtures.py first")
    for p in paths:
        out, ms = observe(p)
        print(f"\n=== {p.name}   {ms:.0f} ms ===")
        print(json.dumps(out, indent=2) if isinstance(out, dict) else f"MALFORMED: {out}")


if __name__ == "__main__":
    main()
