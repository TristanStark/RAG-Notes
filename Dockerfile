# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

# Système: dépendances Playwright + build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcb1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 fonts-liberation libu2f-udev libvulkan1 \
    ca-certificates curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ruff.toml* /app/
RUN pip install -U pip && pip install .[dev]

# Installer navigateur pour Playwright
RUN python -m playwright install --with-deps chromium

# Copier la base de code
COPY . /app

# Pré-init
RUN python scripts/init_dirs.py && python scripts/init_dbs.py || true

ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
