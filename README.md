# Project title

TODO: Name the project during the hackathon.

## Quickstart

From a clean clone, install the pinned dependencies, create your local configuration, add
at least one OpenAI key to `.env`, and start the infrastructure entrypoint:

```sh
uv sync
cp .env.example .env
uv run python -m src.main
```

On Windows PowerShell, use `Copy-Item .env.example .env` in place of `cp`.

## Built during the hackathon

Pre-existing scaffolding: the uv Python project, environment configuration and OpenAI key
pool, JSON logging and SQLite timing instrumentation, container setup, architecture outline,
and configuration tests.

Built on the day: the project-specific channel integration, agent workflow, policy gate,
approval flow, evidence handling, and measured result.
