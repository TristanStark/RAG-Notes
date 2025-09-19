# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

# Dépendances système requises par Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcb1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 fonts-liberation libu2f-udev libvulkan1 \
    ca-certificates curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Étape cache-friendly : métadonnées d'abord
COPY pyproject.toml ruff.toml* README.md ./
COPY .env.example ./.env.example

# Copier le code (src/scripts/tests) — requis pour l'installation (src layout)
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests

# Installer dépendances du projet (dev pour ruff/pytest dans l'image)
RUN python -m pip install -U pip && pip install .[dev]

# Installer Chromium pour Playwright
RUN python -m playwright install --with-deps chromium

# Pré-init idempotent
RUN python scripts/init_dirs.py && python scripts/init_dbs.py || true

ENV PYTHONUNBUFFERED=1

# Lancer le bot en tant que module du package
CMD ["python", "-m", "rag_notes.bot"]
