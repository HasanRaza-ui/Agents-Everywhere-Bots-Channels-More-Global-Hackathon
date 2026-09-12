"""Blocking OS text-to-speech for Guardian check-ins.

Not a medical device. This module speaks a scripted check-in; it does not
interpret a person's response or make any safety decision.
"""

from __future__ import annotations

import pyttsx3


CHECK_IN_LINE = "Max, are you okay? Please wave at the camera."


def speak(text: str) -> None:
    """Speak ``text`` through the OS engine and wait until playback finishes."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def main() -> None:
    speak(CHECK_IN_LINE)
    print("Check-in line spoken.")


if __name__ == "__main__":
    main()