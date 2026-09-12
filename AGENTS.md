# AGENTS.md

Instructions for every coding agent working in this repo: Codex CLI, the ChatGPT
coding plugin, Claude Code, Cursor, or anything else. **This is the only instruction
file.** Do not create `CLAUDE.md` — Claude Code reads `AGENTS.md` as a fallback when no
`CLAUDE.md` exists, so a single file keeps all tools on identical instructions and
prevents drift.

## What this is

A hackathon entry for "Agents, Everywhere: Bots, Channels, & More" (OpenAI × AI
Tinkerers, 12 Sep 2026). Built in a 4h15 window. Judged globally on a 2-minute video,
a written description, and this repository.

**Project:** Guardian — a camera agent for people living alone.
**Channel it lives in:** the physical room — a camera to see, a speaker to ask,
Telegram to escalate. Remove it from the room and there is nothing to observe and
nobody to ask.
**The pattern it demonstrates:** **the camera asks before it alarms.** Detection raises
a question, not an alarm. The person resolves the uncertainty. Only silence escalates.

> Not a medical device. Detects potential safety events and asks whether the person needs
> help; it does not diagnose medical conditions. Keep this framing in every prompt, every
> log line and every piece of copy.

## Build order

`PROMPT.md` holds the step order and the verification gate for each step. Follow it. Do not
start a step before the previous gate passes, and do not silently skip a gate.

## Perception rules — read before touching src/observer.py

**The vision model extracts evidence. It never judges.** Prompt it to describe only what is
visible, and explicitly forbid inferring health, consciousness, intent or emergency status.
If it is asked "is this an emergency", the safety decision moves inside a prompt, the gate
owns nothing, and the Verifier has no independent claim to check.

The contract it returns:

```json
{
  "person_visible": true,
  "posture": "standing|sitting|lying|unknown",
  "on_floor": true,
  "visible_motion": "none|slight|normal",
  "scene_notes": ["short factual observations"],
  "evidence": ["what in the image supports each field"]
}
```

- **No confidence score.** Never ask for one; never invent one.
- **No `rapid_descent` field.** At 3–5 second sampling the fall itself is not observable,
  only its aftermath. Claiming otherwise is an unsupported claim in our own contract.
- **`still_for_seconds` is derived by the gate**, as `concern_streak * SAMPLE_SECONDS`.
  Computed in code, never returned by a model.
- Resize frames to 512px and use `detail: "low"`. Temperature near 0, JSON mode on.

## Non-negotiable design rules

These come from the judging rubric. Do not quietly drop them to save time.

1. **The agent that proposes is not the agent that checks.** A Proposer produces
   structured output with an `evidence[]` array. A Challenger — running on a
   *different* model via OpenRouter — strikes every claim the cited evidence does not
   support. Never merge these into one call.
2. **The policy gate is plain code, never a prompt.** Whether an action is allowed is
   decided by an allowlist in Python/TypeScript. A model never decides what it is
   permitted to do.
3. **Nothing irreversible happens without a human.** Mutating actions route through an
   approval step and block until answered.
4. **Every claim in agent output cites its source.** If it cannot cite, it does not ship.
5. **Fail loudly.** On an API error, escalate or say so in the channel. Never silently
   degrade to a plausible-looking guess.

## Working agreement between agents

- **One agent per directory.** Check `git status` before starting; if another tool has
  uncommitted work in the file you want, commit or stash first.
- **Commit before handing work to a different tool**, so any change can be diffed and
  reverted. Small commits, present tense.
- Never rewrite a file wholesale when an edit will do.
- Do not add dependencies without saying so in the commit message.

## Hard constraints

- **Never commit secrets.** Keys live in `.env`, which is git-ignored. Read them via
  environment variables only. Never print a key, never inline one in a code sample.
- **This repository is public.** Assume everything in it is read by judges and by
  strangers. No internal strategy notes, no personal information, no client data.
- Keep the happy path working at all times. A broken main branch at 14:00 is fatal —
  there is no time to recover.

## Model routing

| Role | Where | Why |
|---|---|---|
| Vision perception | OpenAI vision via `VISION_MODEL` | no install risk; sees scene context a pose skeleton cannot |
| Proposer / main reasoning | OpenAI via `OPENAI_API_KEY` | event credits |
| Challenger / verifier | OpenRouter via `OPENROUTER_API_KEY`, **non-OpenAI model** | independence is the point; the same model checking itself is not a check |
| Transcription / vision | OpenAI | |

If OpenAI credits run out mid-build, fall back to OpenRouter for both roles and keep
the models distinct.

## Definition of done

- [ ] The happy path runs end to end, unattended, from a clean clone
- [ ] `README.md` has an architecture diagram and a quickstart that actually works
- [ ] `README.md` states which parts were built during the hackathon and which were starter code
- [ ] One measured number is recorded, with how it was measured
- [ ] No secrets in git history

## The observer prompt lives in a file

`prompts/observe.md` is the single source of the perception prompt. `src/observer.py` must
**read that file** rather than inlining the prompt text, so prompt tuning and code
generation can happen in parallel without merge conflicts. Do not duplicate it.

Test fixtures live in `tests/fixtures/` — captured frames the observer can be tested
against with no live camera. `scripts/try_observer.py` probes a fixture directly.
