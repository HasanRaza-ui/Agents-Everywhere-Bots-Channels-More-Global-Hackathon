"""Webcam capture and a ten-second rolling frame buffer."""

from __future__ import annotations

import argparse
import base64
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

import cv2


CAPTURE_FPS = 5
WINDOW_SECONDS = 10
SAMPLE_COUNT = 5


@dataclass(frozen=True)
class BufferedFrame:
    """A frame retained with the moment it was captured."""

    captured_at: float
    image: Any


class Camera:
    """Capture webcam frames at a fixed rate into a rolling ten-second buffer."""

    def __init__(self, device_index: int = 0) -> None:
        self._device_index = device_index
        self._frames: deque[BufferedFrame] = deque(
            maxlen=CAPTURE_FPS * WINDOW_SECONDS
        )
        self._capture: cv2.VideoCapture | None = None

    def start(self) -> None:
        """Open the camera, raising clearly when it cannot be used."""
        if self._capture is not None:
            return

        capture = cv2.VideoCapture(self._device_index)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Unable to open camera device {self._device_index}.")
        self._capture = capture

    def close(self) -> None:
        """Release the underlying camera device."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def capture_for(self, seconds: float = WINDOW_SECONDS) -> None:
        """Capture at 5 fps for ``seconds`` and retain the newest ten seconds."""
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        if self._capture is None:
            self.start()
        assert self._capture is not None

        interval = 1 / CAPTURE_FPS
        deadline = time.monotonic() + seconds
        next_capture = time.monotonic()
        consecutive_failures = 0
        while next_capture < deadline:
            delay = next_capture - time.monotonic()
            if delay > 0:
                time.sleep(delay)

            ok, image = self._capture.read()
            captured_at = time.monotonic()
            if not ok or image is None:
                consecutive_failures += 1
                if consecutive_failures > 5:
                    raise RuntimeError("Camera frame capture failed six times in a row.")
            else:
                consecutive_failures = 0
                self._frames.append(BufferedFrame(captured_at, image))
            next_capture += interval

    def sample(self) -> tuple[list[str], float]:
        """Return five sampled JPEGs and their actual elapsed capture time."""
        if len(self._frames) < SAMPLE_COUNT:
            raise RuntimeError(
                f"Need at least {SAMPLE_COUNT} captured frames before sampling; "
                f"have {len(self._frames)}."
            )

        frames = list(self._frames)
        last_index = len(frames) - 1
        positions = [round(index * last_index / (SAMPLE_COUNT - 1)) for index in range(SAMPLE_COUNT)]
        sampled_frames = [frames[index] for index in positions]
        span_seconds = sampled_frames[-1].captured_at - sampled_frames[0].captured_at
        return (
            [self._as_base64_jpeg(frame.image) for frame in sampled_frames],
            span_seconds,
        )

    @staticmethod
    def _as_base64_jpeg(image: Any) -> str:
        height, width = image.shape[:2]
        longest_edge = max(height, width)
        if longest_edge > 512:
            scale = 512 / longest_edge
            image = cv2.resize(
                image,
                (round(width * scale), round(height * scale)),
                interpolation=cv2.INTER_AREA,
            )

        ok, encoded = cv2.imencode(".jpg", image)
        if not ok:
            raise RuntimeError("JPEG encoding failed.")
        return base64.b64encode(encoded.tobytes()).decode("ascii")

    def __enter__(self) -> Camera:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def dump_samples(output_dir: Path) -> None:
    """Capture a full window and write its five sampled JPEGs for visual inspection."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with Camera() as camera:
        camera.capture_for()
        frames_b64, span_seconds = camera.sample()
        for number, encoded in enumerate(frames_b64, start=1):
            (output_dir / f"sample_{number}.jpg").write_bytes(base64.b64decode(encoded))
    print(f"Sample span: {span_seconds:.2f} seconds")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture and inspect webcam samples.")
    parser.add_argument(
        "--dump",
        action="store_true",
        help="write five evenly sampled JPEGs to tmp/",
    )
    args = parser.parse_args()
    if not args.dump:
        parser.error("--dump is required")

    output_dir = Path("tmp")
    dump_samples(output_dir)
    print(f"Wrote {SAMPLE_COUNT} sampled frames to {output_dir.resolve()}")

if __name__ == "__main__":
    main()
