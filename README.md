# Guardian

**A camera agent that asks before it alarms.**

Built for *Agents, Everywhere: Bots, Channels, & More* — OpenAI × AI Tinkerers, 12 Sep 2026.

> Not a medical device. Guardian detects potential safety events and asks whether the person
> needs help. It does not diagnose medical conditions.

---

## The problem

Camera monitoring for people living alone either records footage nobody watches, or alarms so
often that the family switches it off. The failure that matters is not the missed fall — it is
the forty false alarms that destroy trust in the system.

Every existing product handles a false positive by routing it to a **human call-centre
operator** who phones in and asks "are you okay?".

## What Guardian does differently

It moves that verification step into the agent and into the room.

**Detect → ask → listen → escalate only on silence.**

The camera decides nothing. It raises a question, the person answers it, and only silence
escalates to a caregiver. Which means the detector is *allowed* to be imprecise — being wrong
costs one spoken question instead of a false alarm to someone's daughter.

**The pattern: the camera asks before it alarms.**

## Architecture

Full diagram, trade-offs and design rationale: **[`docs/architecture.md`](docs/architecture.md)**

<img src="docs/architecture.svg" alt="Guardian architecture" width="520">

**Grey** = deterministic code · **teal** = model inference · **amber** = human in the loop.

Three things hold this together:

1. **The vision model extracts, it never judges.** It is prompted to describe only what is
   visible and forbidden from inferring health, consciousness or intent.
2. **The safety gate is plain Python.** Two consecutive concern samples plus a cooldown, both
   counters. A single frame can never raise an alarm.
3. **Failure escalates, it does not go quiet.** A dropped camera or a failed API call notifies
   the caregiver with the error. A monitoring system that fails silently is worse than none,
   because it is trusted.

## Quickstart

```bash
git clone <this repo>
cd agents-everywhere
uv sync
cp .env.example .env          # Windows: Copy-Item .env.example .env
# fill in .env, then:
uv run python scripts/verify_env.py    # checks every key with one real call
uv run python -m src.main
```

`verify_env.py` prints a status table and never prints key material. Run it before you start
and again before you record.

## The integration contract

Agreed at minute 20, never renegotiated. Every component reads or writes this shape:

```json
{
  "person_visible": true,
  "posture": "lying",
  "on_floor": true,
  "visible_motion": "none",
  "scene_notes": ["chair overturned beside the person"],
  "evidence": [
    "torso is horizontal and in contact with the floor",
    "limb positions unchanged from the previous sample"
  ]
}
```

`still_for_seconds` is **not** in this payload — the gate derives it as
`concern_streak * SAMPLE_SECONDS`. Computed in code, never claimed by a model.

No confidence score. The model is not asked for one and could not calibrate it.

## Who builds what

| Lane | Owner | Files | Done when |
|---|---|---|---|
| **Perception** | | `src/camera.py`, `src/observer.py` | a frame produces valid contract JSON |
| **Reasoning** | | `src/agent.py`, `src/verifier.py` | unsupported claims come back struck |
| **Safety** | | `src/gate.py`, `tests/test_gate.py` | gate tests pass with no network |
| **Interaction** | | `src/voice.py`, `src/notify.py`, overlay | speaks, counts down, sends to Telegram |

Put your name in the table when you take a lane. One person per file — check `git status`
before you start, and commit before handing a file to another agent or teammate.

## Environment

See `.env.example`. You need, at minimum: `OPENAI_API_KEY`, `VISION_MODEL`,
`OPENROUTER_API_KEY`, `CHALLENGER_MODEL`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CAREGIVER_CHAT_ID`.

Each team member redeems their own $50 event credit and adds it as `OPENAI_API_KEY_2` / `_3`.
The key pool fails over automatically on quota and rate-limit errors — one exhausted key will
not stop the demo.

## Agent instructions

Every coding agent working here reads **[`AGENTS.md`](AGENTS.md)** — Codex natively, Claude
Code as a fallback. One file, no `CLAUDE.md`, no drift. Read it before your first prompt.

## Built during the hackathon

**Scaffolded beforehand** (permitted starter code): the uv project, environment config and the
OpenAI key pool, JSON logging and SQLite timing instrumentation, the Dockerfile, the
environment verification script, and the agent instruction file.

**Built on the day:** vision perception and the evidence contract, the agent and verifier, the
safety gate and its tests, the spoken check-in, the acknowledgement paths, Telegram
escalation, and the measured result below.

## Measured result

_TODO before submitting — from `runs.db` via `src/obs.py report()`._

## Prior art

[SafelyYou](https://www.safely-you.com/) does AI video fall detection in senior living.
[Vayyar](https://vayyar.com/) does it with radar. [ElliQ](https://elliq.com/) is a deployed
conversational eldercare companion doing proactive check-ins and medication reminders.

Detection is commodity and companionship is commercially served. Guardian's contribution is
narrower: the **verification loop** — the agent resolving its own uncertainty by asking the
person, instead of routing every false positive to a human operator.

## Licence

MIT.
