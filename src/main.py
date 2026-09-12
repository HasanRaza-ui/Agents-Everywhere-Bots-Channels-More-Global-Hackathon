"""End-to-end Guardian monitoring loop.

Not a medical device. Guardian detects potential safety events, asks the
resident to respond, and escalates only according to deterministic policy.
"""

from __future__ import annotations

import base64
import math
import time
from typing import Any, Mapping

import cv2

from src.camera import Camera
from src.gate import GateResult, SafetyGate
from src.notify import send_photo
from src.obs import configure_logging, timed
from src.observer import observe
from src.overlay import OverlayState, show
from src.voice import CHECK_IN_LINE, speak


CHECK_IN_SECONDS = 20
WINDOW_NAME = "Guardian"


@timed("observe")
def timed_observe(frames_b64: list[str], span_seconds: float) -> dict[str, Any]:
    """Record the vision-call duration without moving policy into the model."""
    return observe(frames_b64, span_seconds)


def is_wave_acknowledging(_frames_b64: list[str]) -> bool:
    """Step 5 hook: replace with the wave detector after its gate is built."""
    return False


def _latest_frame(frames_b64: list[str]) -> Any:
    image_bytes = base64.b64decode(frames_b64[-1])
    image = cv2.imdecode(
        __import__("numpy").frombuffer(image_bytes, dtype=__import__("numpy").uint8),
        cv2.IMREAD_COLOR,
    )
    if image is None:
        raise RuntimeError("Unable to decode the latest sampled camera frame.")
    return image


def _wait_for_acknowledgement(
    frame: Any,
    frames_b64: list[str],
    observation: Mapping[str, Any],
    concern_streak: int,
) -> bool:
    """Use a key press today; the wave hook remains intentionally inactive."""
    deadline = time.monotonic() + CHECK_IN_SECONDS
    while time.monotonic() < deadline:
        remaining = math.ceil(deadline - time.monotonic())
        key = show(
            frame,
            OverlayState("CHECK-IN", concern_streak, observation, remaining),
            WINDOW_NAME,
        )
        if key != 255:
            return True
        if is_wave_acknowledging(frames_b64):
            return True
        time.sleep(0.05)
    return False


def _send_escalation(
    frame_b64: str,
    observation: Mapping[str, Any],
    result: GateResult,
) -> None:
    send_photo(
        base64.b64decode(frame_b64),
        observation,
        struck=[],
        still_for_seconds=result.still_for_seconds,
        reason=result.reason,
    )


def main() -> None:
    """Run the camera, evidence, deterministic policy, check-in, and escalation loop."""
    configure_logging()
    gate = SafetyGate()
    last_frame_b64: str | None = None
    last_observation: Mapping[str, Any] = {}

    try:
        with Camera() as camera:
            print("Guardian watching. Press q in the overlay to stop.")
            while True:
                try:
                    camera.capture_for()
                    frames_b64, span_seconds = camera.sample()
                    last_frame_b64 = frames_b64[-1]
                    observation = timed_observe(frames_b64, span_seconds)
                    last_observation = observation
                    result = gate.process(observation, now=time.monotonic())
                    frame = _latest_frame(frames_b64)
                    key = show(
                        frame,
                        OverlayState(result.action.upper(), result.concern_streak, observation),
                        WINDOW_NAME,
                    )
                    if key == ord("q"):
                        break

                    if result.action == "check_in":
                        speak(CHECK_IN_LINE)
                        if _wait_for_acknowledgement(
                            frame, frames_b64, observation, result.concern_streak
                        ):
                            resolved = gate.acknowledge(now=time.monotonic())
                            show(
                                frame,
                                OverlayState("RESOLVED — NO ALERT SENT", resolved.concern_streak, observation),
                                WINDOW_NAME,
                            )
                            print("Resident acknowledged check-in.")
                        else:
                            result = gate.check_in_expired()
                            _send_escalation(last_frame_b64, observation, result)
                            print("Check-in expired; caregiver notification sent.")
                    elif result.action == "escalate":
                        _send_escalation(last_frame_b64, observation, result)
                        print(f"Pipeline escalation sent: {result.reason}")
                except Exception as error:
                    if last_frame_b64 is None:
                        raise RuntimeError(f"Monitoring failed before any camera frame: {error}") from error
                    failure = gate.process({}, now=time.monotonic())
                    _send_escalation(last_frame_b64, last_observation, failure)
                    print(f"Pipeline escalation sent: {failure.reason}")
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()