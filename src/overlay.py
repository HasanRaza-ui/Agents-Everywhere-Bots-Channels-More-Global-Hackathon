"""High-contrast OpenCV overlay for the filmed Guardian demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import cv2


@dataclass(frozen=True)
class OverlayState:
    state: str
    concern_streak: int
    observation: Mapping[str, Any] | None = None
    countdown_seconds: int | None = None


def draw(frame: Any, status: OverlayState) -> Any:
    """Return a high-contrast annotated frame suitable for video capture."""
    canvas = frame.copy()
    height, width = canvas.shape[:2]
    cv2.rectangle(canvas, (0, 0), (width, min(height, 240)), (18, 18, 18), -1)

    cv2.putText(
        canvas,
        f"GUARDIAN  |  {status.state}",
        (28, 52),
        cv2.FONT_HERSHEY_DUPLEX,
        1.1,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        f"Concern streak: {status.concern_streak}",
        (28, 98),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (220, 220, 220),
        2,
        cv2.LINE_AA,
    )

    observation = status.observation or {}
    facts = (
        f"PERSON: {observation.get('person_visible', 'unknown')}   "
        f"ON FLOOR: {observation.get('on_floor', 'unknown')}   "
        f"MOTION: {observation.get('visible_motion', 'unknown')}"
    )
    cv2.putText(
        canvas,
        facts.upper(),
        (28, 143),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (110, 230, 220),
        2,
        cv2.LINE_AA,
    )

    if status.countdown_seconds is not None:
        cv2.rectangle(canvas, (0, 240), (width, min(height, 420)), (0, 80, 180), -1)
        cv2.putText(
            canvas,
            f"CHECK-IN: {status.countdown_seconds}s",
            (28, 345),
            cv2.FONT_HERSHEY_DUPLEX,
            1.7,
            (255, 255, 255),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            "Press any key to acknowledge",
            (30, 395),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return canvas


def show(frame: Any, status: OverlayState, window_name: str = "Guardian") -> int:
    """Draw and display the overlay, returning the pressed key code if any."""
    cv2.imshow(window_name, draw(frame, status))
    return cv2.waitKey(1) & 0xFF