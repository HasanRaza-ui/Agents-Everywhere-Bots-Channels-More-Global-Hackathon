FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN pip install --no-cache-dir uv \
    && useradd --create-home --uid 10001 app

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src ./src
RUN chown -R app:app /app

USER app
EXPOSE $PORT
CMD [".venv/bin/python", "-m", "src.main"]
