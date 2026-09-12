# Codex prompts — one per step

**Do not paste a giant prompt.** One step, run the gate, then the next. That is what the
gates are for, and it is the only way anyone can tell which layer broke.

All context lives in the repo, so the prompts are short enough to **type** — no clipboard
fighting. Run `codex` from the repo root.

---

## The loop

```
1. type the step prompt
2. Codex builds, stops, prints the verification command
3. YOU run the gate yourself — never take Codex's word for it
4. gate passes  -> next step
   gate fails   -> "The gate failed with: <paste error>. Fix Step N only."
```

---

## Step 0 — foundations

No Codex needed. Run these yourself:

```
uv run python scripts/verify_env.py
uv run python scripts/capture_fixtures.py
uv run python scripts/try_observer.py
```

Tune `prompts/observe.md` until every fixture classifies correctly. **Do not start Step 1
until it does.**

---

## Step 1 — camera and rolling buffer

```
Read PROMPT.md Step 1, AGENTS.md, and docs/architecture.md.
Implement Step 1 only — src/camera.py. Do not start Step 2.
Add a --dump flag that writes the 5 sampled frames to tmp/ so I can inspect them.
Stop when done, print the verification command, and show git status. Do not commit.
```

## Step 2 — vision extraction, multi-frame

```
Read PROMPT.md Step 2, AGENTS.md (Perception rules), and docs/architecture.md.
Implement Step 2 only — src/observer.py. Do not start Step 3.
The prompt MUST be read from prompts/observe.md, never inlined.
Send all 5 frames in one call, earliest first, and say in the user message that they span
the last 10 seconds so visible_motion is observable.
Stop when done, print the verification command, and show git status. Do not commit.
```

## Step 3 — the gate

```
Read PROMPT.md Step 3, AGENTS.md, and docs/architecture.md.
Implement Step 3 only — src/gate.py and tests/test_gate.py. Do not start Step 4.
No model calls anywhere in src/gate.py. still_for_seconds is derived here, never read from
the model's output. Any exception must escalate, not pass silently.
Write the tests first, then the implementation.
Stop when done, print the verification command, and show git status. Do not commit.
```

## Step 4 — speak

```
Read PROMPT.md Step 4.
Implement Step 4 only — src/voice.py. Do not start Step 5.
Blocking speak(text) through the OS speech engine. No new dependencies beyond pyttsx3.
Stop when done, print the verification command, and show git status. Do not commit.
```

## Step 5 — acknowledgement

```
Read PROMPT.md Step 5, AGENTS.md, and docs/architecture.md.
Implement Step 5 only. Do not start Step 6.
Two paths, both required: is_acknowledging() in src/observer.py using the same vision model
with a gesture prompt, AND a key press in the overlay window. No speech recognition.
Stop when done, print the verification command, and show git status. Do not commit.
```

## Step 6 — Telegram escalation

```
Read PROMPT.md Step 6 and docs/architecture.md.
Implement Step 6 only — src/notify.py. Do not start Step 7.
sendPhoto with the frame. Caption must carry timestamp, the observation fields, struck
claims shown struck through, still_for_seconds, and the escalation reason.
Add a --test flag that sends one message so I can verify without a fall.
Stop when done, print the verification command, and show git status. Do not commit.
```

## Step 7 — end to end

```
Read PROMPT.md Step 7, AGENTS.md, and docs/architecture.md.
Implement Step 7 only — src/main.py and src/overlay.py. Do not start Step 8.
Wrap the observe and verify calls with @timed from src/obs.py.
The overlay is what gets filmed: state, concern streak, the evidence booleans, and a large
countdown during check-in. Readable at video resolution. No Streamlit.
Stop when done, print the verification command, and show git status. Do not commit.
```

**After Step 7 passes, you have a demo. Record it before starting Step 8.**

## Step 8 — the Verifier

```
Read PROMPT.md Step 8, AGENTS.md rule 1, and docs/architecture.md.
Implement Step 8 only — src/verifier.py and tests/test_verifier.py.
Text only — NEVER send the images to the verifier. That independence is the whole point.
Include the test case from PROMPT.md: an observation claiming "appears to be unconscious"
with evidence only "torso is horizontal on the floor" must be struck.
Stop when done, print the verification command, and show git status. Do not commit.
```

## Step 9 — escalation ladder

```
Read PROMPT.md Step 9 and docs/architecture.md.
Implement Step 9 only — second attempt, then emergency contact, and the explicit-yes path.
The ladder lives in src/gate.py as plain code. Extend tests/test_gate.py to cover it.
Stop when done, print the verification command, and show git status. Do not commit.
```

---

## When a gate fails

```
The gate for Step N failed:

<paste the exact error>

Fix Step N only. Do not refactor anything else and do not start the next step.
```

## When Codex drifts

If it starts building ahead, or moves a responsibility across a component boundary:

```
Stop. Re-read docs/architecture.md.
You have moved <X> out of <component>. The architecture puts it in <component> because
<reason>. Revert that and keep the boundary.
```
