FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---- Stage 1: Install system deps & Python packages ----
FROM base AS deps

# Playwright/Chromium runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Chromium shared-lib requirements
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1 \
    # curl_cffi native deps
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

# ---- Stage 2: Final image ----
FROM deps AS final

COPY . .

ENTRYPOINT ["python", "main.py"]
# Default: print help (Cloud Run Job overrides args per execution)
CMD ["--list"]
