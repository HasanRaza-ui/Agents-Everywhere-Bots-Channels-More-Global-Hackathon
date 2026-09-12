"""Telegram escalation delivery for Guardian.

Not a medical device. This module sends a caregiver notification containing
visible evidence and a supplied escalation reason; it makes no diagnosis.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import html
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import httpx
from dotenv import load_dotenv


TELEGRAM_API = "https://api.telegram.org"
TEST_FIXTURE = Path("tests/fixtures/lying_floor_1.jpg")


def _caption(
    observation: Mapping[str, Any],
    struck: Sequence[str],
    still_for_seconds: int,
    reason: str,
    timestamp: datetime,
) -> str:
    """Format a readable Telegram HTML caption from supplied evidence."""
    fields = "\n".join(
        f"<b>{html.escape(str(name))}</b>: {html.escape(str(value))}"
        for name, value in observation.items()
    )
    struck_text = "\n".join(f"<s>{html.escape(claim)}</s>" for claim in struck)
    lines = [
        "<b>Guardian escalation</b>",
        f"<b>Timestamp</b>: {timestamp.astimezone(UTC).isoformat()}",
        fields,
        f"<b>Still for</b>: {still_for_seconds} seconds",
        f"<b>Reason</b>: {html.escape(reason)}",
    ]
    if struck_text:
        lines.extend(["<b>Struck claims</b>:", struck_text])
    return "\n".join(lines)


def send_photo(
    frame: bytes,
    observation: Mapping[str, Any],
    struck: Sequence[str],
    still_for_seconds: int,
    reason: str,
    *,
    timestamp: datetime | None = None,
) -> None:
    """Send a caregiver photo notification, raising on any Telegram failure."""
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CAREGIVER_CHAT_ID", "")
    if not token or not chat_id:
        raise RuntimeError("Telegram bot token or caregiver chat ID is not configured.")

    caption = _caption(
        observation,
        struck,
        still_for_seconds,
        reason,
        timestamp or datetime.now(UTC),
    )
    if len(caption) > 1024:
        raise ValueError("Telegram photo caption exceeds 1024 characters.")

    response = httpx.post(
        f"{TELEGRAM_API}/bot{token}/sendPhoto",
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
        files={"photo": ("guardian-frame.jpg", frame, "image/jpeg")},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError("Telegram rejected the photo notification.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a Guardian Telegram test photo.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="send a fixture image to the configured caregiver chat",
    )
    args = parser.parse_args()
    if not args.test:
        parser.error("--test is required")
    if not TEST_FIXTURE.exists():
        raise FileNotFoundError(f"Test fixture is missing: {TEST_FIXTURE}")

    send_photo(
        TEST_FIXTURE.read_bytes(),
        observation={
            "person_visible": True,
            "posture": "lying",
            "on_floor": True,
            "visible_motion": "none",
            "scene_notes": ["fixture image used for notification test"],
            "evidence": ["test fixture provided to the notifier"],
        },
        struck=["test-only unsupported claim"],
        still_for_seconds=6,
        reason="TEST ONLY — Telegram delivery verification; no safety event is inferred.",
    )
    print("Telegram test photo sent.")


if __name__ == "__main__":
    main()