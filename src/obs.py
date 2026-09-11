"""Small, dependency-light observability primitives for the hackathon build."""

from __future__ import annotations

import functools
import sqlite3
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, ParamSpec, TypeVar

import structlog

DATABASE_PATH = Path("runs.db")
P = ParamSpec("P")
T = TypeVar("T")


def configure_logging() -> None:
    structlog.configure(
        processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(),
    )


def _record(label: str, started_at: float, duration_ms: float, ok: bool, note: str | None) -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY, label TEXT NOT NULL, started_at REAL NOT NULL,
                duration_ms REAL NOT NULL, ok INTEGER NOT NULL, note TEXT
            )"""
        )
        connection.execute(
            "INSERT INTO runs (label, started_at, duration_ms, ok, note) VALUES (?, ?, ?, ?, ?)",
            (label, started_at, duration_ms, ok, note),
        )


@contextmanager
def timer(label: str, note: str | None = None) -> Iterator[None]:
    """Record elapsed wall-clock time, including failed operations."""
    started_at = time.time()
    started = time.perf_counter()
    try:
        yield
    except BaseException as error:
        _record(label, started_at, (time.perf_counter() - started) * 1000, False, type(error).__name__)
        raise
    else:
        _record(label, started_at, (time.perf_counter() - started) * 1000, True, note)


def timed(label: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorate a synchronous function with a run-timing record."""
    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            with timer(label):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def report() -> None:
    """Print run count, median, and p90 duration for each recorded label."""
    if not DATABASE_PATH.exists():
        return
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute("SELECT label, duration_ms FROM runs ORDER BY label, duration_ms").fetchall()
    grouped: dict[str, list[float]] = {}
    for label, duration in rows:
        grouped.setdefault(label, []).append(duration)
    for label, durations in grouped.items():
        p90 = durations[max(0, (len(durations) * 90 + 99) // 100 - 1)]
        print(f"{label}: count={len(durations)} median_ms={statistics.median(durations):.2f} p90_ms={p90:.2f}")
