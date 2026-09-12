from src.gate import SAMPLE_SECONDS, SafetyGate


CONCERN = {"on_floor": True, "visible_motion": "none"}
CLEAR = {"on_floor": False, "visible_motion": "normal"}


def test_one_concern_sample_does_not_begin_check_in() -> None:
    gate = SafetyGate()

    result = gate.process(CONCERN, now=0)

    assert result.action == "watching"
    assert result.concern_streak == 1
    assert result.still_for_seconds == SAMPLE_SECONDS


def test_two_consecutive_concerns_begin_check_in() -> None:
    gate = SafetyGate()

    gate.process(CONCERN, now=0)
    result = gate.process(CONCERN, now=SAMPLE_SECONDS)

    assert result.action == "check_in"
    assert result.concern_streak == 2
    assert result.still_for_seconds == 2 * SAMPLE_SECONDS


def test_acknowledgement_cancels_check_in_and_starts_cooldown() -> None:
    gate = SafetyGate(cooldown_seconds=30)
    gate.process(CONCERN, now=0)
    gate.process(CONCERN, now=SAMPLE_SECONDS)

    result = gate.acknowledge(now=10)

    assert result.action == "resolved"
    assert result.concern_streak == 0
    assert result.cooldown_until == 40


def test_cooldown_suppresses_retrigger() -> None:
    gate = SafetyGate(cooldown_seconds=30)
    gate.process(CONCERN, now=0)
    gate.process(CONCERN, now=SAMPLE_SECONDS)
    gate.acknowledge(now=10)

    gate.process(CONCERN, now=11)
    result = gate.process(CONCERN, now=11 + SAMPLE_SECONDS)

    assert result.action == "watching"
    assert result.cooldown_until == 40


def test_exception_escalates_with_error_text() -> None:
    gate = SafetyGate()

    result = gate.process({"on_floor": True}, now=0)

    assert result.action == "escalate"
    assert "visible_motion" in result.reason