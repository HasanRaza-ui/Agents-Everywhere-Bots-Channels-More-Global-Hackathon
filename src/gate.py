"""Deterministic safety policy gate for Guardian.

Not a medical device. This module applies the fixed check-in and escalation
policy to observation fields; it makes no medical judgement and calls no model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


SAMPLE_SECONDS = 3
CONFIRMATIONS_REQUIRED = 2
DEFAULT_COOLDOWN_SECONDS = 60


@dataclass(frozen=True)
class GateResult:
    """A deterministic instruction for the caller to carry out."""

    action: str
    reason: str
    concern_streak: int
    still_for_seconds: int
    cooldown_until: float | None


class SafetyGate:
    """Apply the two-confirmation and cooldown policy in plain Python."""

    def __init__(self, cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")
        self._cooldown_seconds = cooldown_seconds
        self._concern_streak = 0
        self._cooldown_until: float | None = None
        self._check_in_active = False

    def process(self, observation: Mapping[str, object], *, now: float) -> GateResult:
        """Process an observation; any failure becomes an escalation instruction."""
        try:
            if self._in_cooldown(now):
                self._concern_streak = 0
                return self._result("watching", "cooldown active")

            concern = (
                observation["on_floor"] is True
                and observation["visible_motion"] == "none"
            )
            self._concern_streak = self._concern_streak + 1 if concern else 0

            if self._check_in_active:
                return self._result("watching", "check-in already active")
            if self._concern_streak >= CONFIRMATIONS_REQUIRED:
                self._check_in_active = True
                return self._result("check_in", "two consecutive concern observations")
            return self._result("watching", "awaiting another concern observation")
        except Exception as error:
            return self._escalate(error)

    def acknowledge(self, *, now: float) -> GateResult:
        """Resolve a check-in and begin the deterministic cooldown."""
        try:
            self._check_in_active = False
            self._concern_streak = 0
            self._cooldown_until = now + self._cooldown_seconds
            return self._result("resolved", "resident acknowledged check-in")
        except Exception as error:
            return self._escalate(error)

    def check_in_expired(self) -> GateResult:
        """Escalate when an active check-in receives no acknowledgement."""
        try:
            if not self._check_in_active:
                raise RuntimeError("check-in expiry received without an active check-in")
            self._check_in_active = False
            return self._result("escalate", "check-in window expired without acknowledgement")
        except Exception as error:
            return self._escalate(error)

    def _in_cooldown(self, now: float) -> bool:
        return self._cooldown_until is not None and now < self._cooldown_until

    def _result(self, action: str, reason: str) -> GateResult:
        return GateResult(
            action=action,
            reason=reason,
            concern_streak=self._concern_streak,
            still_for_seconds=self._concern_streak * SAMPLE_SECONDS,
            cooldown_until=self._cooldown_until,
        )

    def _escalate(self, error: Exception) -> GateResult:
        self._check_in_active = False
        return self._result("escalate", f"pipeline error: {error}")