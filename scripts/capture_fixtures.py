"""Capture labelled test frames from the webcam. Run BEFORE the app exists.

    uv run python scripts/capture_fixtures.py

Press the number key for the label you want, then q to quit. Frames land in
tests/fixtures/ so the observer prompt can be tested without a live camera and the
same inputs can be replayed when measuring accuracy.
"""
import pathlib
import cv2

LABELS = {
    ord("1"): "standing",
    ord("2"): "sitting",
    ord("3"): "lying_floor",
    ord("4"): "lying_sofa",
    ord("5"): "waving",
    ord("6"): "empty_room",
}

OUT = pathlib.Path("tests/fixtures")
OUT.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise SystemExit("no webcam found")

counts = {}
print(__doc__)
print("keys:", ", ".join(f"{chr(k)}={v}" for k, v in LABELS.items()))

while True:
    ok, frame = cap.read()
    if not ok:
        break
    shown = frame.copy()
    cv2.putText(shown, "1 stand  2 sit  3 lying-floor  4 lying-sofa  5 wave  6 empty  q quit",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imshow("capture fixtures", shown)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    if key in LABELS:
        label = LABELS[key]
        n = counts.get(label, 0) + 1
        counts[label] = n
        path = OUT / f"{label}_{n}.jpg"
        h, w = frame.shape[:2]
        scale = 512 / max(h, w)
        if scale < 1:
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        cv2.imwrite(str(path), frame)
        print("saved", path)

cap.release()
cv2.destroyAllWindows()
print("\ncaptured:", counts)
