"""Multi-frame visual evidence extraction for Guardian.

Not a medical device. This component describes visible evidence; it does not
diagnose health, consciousness, intent, or emergency status.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.config import load_settings, next_openai_key


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "observe.md"
REQUIRED_FIELDS = {
    "person_visible",
    "posture",
    "on_floor",
    "visible_motion",
    "scene_notes",
    "evidence",
}
POSTURES = {"standing", "sitting", "lying", "unknown"}
MOTION_LEVELS = {"none", "slight", "normal", "unknown"}


def _load_prompt() -> str:
    """Read the single-source perception prompt."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def _validate_observation(value: Any) -> dict[str, Any]:
    """Reject output that does not meet the fixed evidence contract."""
    if not isinstance(value, dict) or set(value) != REQUIRED_FIELDS:
        raise ValueError("Model response does not match the observation contract.")
    if not isinstance(value["person_visible"], bool):
        raise ValueError("person_visible must be a boolean.")
    if not isinstance(value["on_floor"], bool):
        raise ValueError("on_floor must be a boolean.")
    if value["posture"] not in POSTURES:
        raise ValueError("posture is invalid.")
    if value["visible_motion"] not in MOTION_LEVELS:
        raise ValueError("visible_motion is invalid.")
    if not all(isinstance(item, str) for item in value["scene_notes"]):
        raise ValueError("scene_notes must contain strings.")
    if not all(isinstance(item, str) for item in value["evidence"]):
        raise ValueError("evidence must contain strings.")
    if not value["evidence"]:
        raise ValueError("evidence must not be empty.")
    return value


def observe(frames_b64: list[str], span_seconds: float) -> dict[str, Any]:
    """Extract visible evidence from five chronological JPEG frames.

    Malformed JSON receives one retry. API failures and contract violations are
    intentionally raised so the escalation path can report them.
    """
    if len(frames_b64) != 5:
        raise ValueError("observe() requires exactly five frames.")
    if span_seconds < 0:
        raise ValueError("span_seconds cannot be negative.")

    load_settings()
    model = os.getenv("VISION_MODEL", "").strip()
    if not model:
        raise RuntimeError("VISION_MODEL is not configured.")

    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"These 5 frames span the last {span_seconds:.1f} seconds, earliest first. "
                "Describe only directly visible evidence across them."
            ),
        }
    ]
    content.extend(
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{frame}",
                "detail": "low",
            },
        }
        for frame in frames_b64
    )

    for attempt in range(2):
        response = OpenAI(api_key=next_openai_key()).chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _load_prompt()},
                {"role": "user", "content": content},
            ],
        )
        raw = response.choices[0].message.content
        try:
            return _validate_observation(json.loads(raw or ""))
        except json.JSONDecodeError:
            if attempt == 1:
                raise RuntimeError("Model returned malformed JSON after one retry.")

    raise RuntimeError("Malformed JSON retry loop ended unexpectedly.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract visible evidence from a fixture.")
    parser.add_argument("fixture", type=Path, help="JPEG fixture to submit five times")
    args = parser.parse_args()

    image_b64 = base64.b64encode(args.fixture.read_bytes()).decode("ascii")
    observation = observe([image_b64] * 5, span_seconds=0.0)
    print(json.dumps(observation, indent=2))


if __name__ == "__main__":
    main()