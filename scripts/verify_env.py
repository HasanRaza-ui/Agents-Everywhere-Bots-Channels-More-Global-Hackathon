"""Check every configured service with one real call. Prints a status table.

    uv run python scripts/verify_env.py

Run it tonight after filling in .env, and again at the venue tomorrow morning.
Never prints key material.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 15.0
results: list[tuple[str, bool | None, str]] = []


def record(name: str, ok: bool | None, detail: str) -> None:
    results.append((name, ok, detail))


def check(name: str, env_var: str, fn) -> None:
    token = os.getenv(env_var, "").strip()
    if not token:
        record(name, None, f"{env_var} not set")
        return
    try:
        record(name, *fn(token))
    except Exception as exc:  # noqa: BLE001 - report, never crash the run
        record(name, False, f"{type(exc).__name__}: {exc}")


def openai_check(token: str) -> tuple[bool, str]:
    r = httpx.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return True, f"{len(r.json().get('data', []))} models visible"
    return False, f"HTTP {r.status_code} - {r.text[:120]}"


def openrouter_check(token: str) -> tuple[bool, str]:
    r = httpx.get(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        data = r.json().get("data", {})
        limit = data.get("limit")
        used = data.get("usage")
        return True, f"usage={used} limit={limit}"
    if r.status_code == 404:
        return None, "endpoint moved - check manually, key may still be fine"
    return False, f"HTTP {r.status_code} - {r.text[:120]}"


def exa_check(token: str) -> tuple[bool, str]:
    r = httpx.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": token, "Content-Type": "application/json"},
        json={"query": "site reliability incident postmortem", "numResults": 1},
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return True, f"{len(r.json().get('results', []))} result(s)"
    return False, f"HTTP {r.status_code} - {r.text[:120]}"


def telegram_check(token: str) -> tuple[bool, str]:
    r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=TIMEOUT)
    if r.status_code != 200 or not r.json().get("ok"):
        return False, f"HTTP {r.status_code} - {r.text[:120]}"
    me = r.json()["result"]
    u = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=TIMEOUT)
    n = len(u.json().get("result", [])) if u.status_code == 200 else 0
    hint = "" if n else "  <-- no updates: send a plain group message; if still 0, privacy mode is ON"
    return True, f"@{me.get('username')}, {n} pending update(s){hint}"


def slack_check(token: str) -> tuple[bool, str]:
    r = httpx.post(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    body = r.json()
    if body.get("ok"):
        return True, f"team={body.get('team')} bot={body.get('user')}"
    return False, f"{body.get('error')}"


def slack_app_token_check(token: str) -> tuple[bool, str]:
    if token.startswith("xapp-"):
        return True, "looks like an app-level token (not verified until Socket Mode connects)"
    return False, "should start with xapp- ; you may have pasted the bot token"


def main() -> int:
    check("OpenAI (key 1)", "OPENAI_API_KEY", openai_check)
    check("OpenAI (key 2)", "OPENAI_API_KEY_2", openai_check)
    check("OpenAI (key 3)", "OPENAI_API_KEY_3", openai_check)
    check("OpenRouter", "OPENROUTER_API_KEY", openrouter_check)
    check("Exa", "EXA_API_KEY", exa_check)
    check("Telegram", "TELEGRAM_BOT_TOKEN", telegram_check)
    check("Slack bot token", "SLACK_BOT_TOKEN", slack_check)
    check("Slack app token", "SLACK_APP_TOKEN", slack_app_token_check)

    width = max(len(n) for n, _, _ in results)
    print()
    failed = 0
    for name, ok, detail in results:
        mark = "OK  " if ok else ("--  " if ok is None else "FAIL")
        if ok is False:
            failed += 1
        print(f"  {mark}  {name.ljust(width)}   {detail}")

    model = os.getenv("CHALLENGER_MODEL", "").strip()
    print()
    if not model:
        print("  note: CHALLENGER_MODEL is not set. The Challenger must be a NON-OpenAI model.")
    elif "gpt" in model.lower() or "openai" in model.lower():
        print(f"  WARNING: CHALLENGER_MODEL={model} looks like an OpenAI model.")
        print("           A model checking its own work is not a check. See AGENTS.md rule 1.")
    else:
        print(f"  Challenger model: {model}")

    print()
    print(f"  {failed} failing, {sum(1 for _, ok, _ in results if ok is None)} not configured")
    print()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
