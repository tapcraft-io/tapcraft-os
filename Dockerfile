FROM python:3.12-slim

ENV POETRY_VERSION=1.7.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install build tools and git
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git curl \
    && pip install "poetry==${POETRY_VERSION}" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --no-root --no-directory

COPY src src

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
