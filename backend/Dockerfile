FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

# Bağımlılıkları ayrı katmanda kur — pyproject.toml değişmedikçe cache'ten gelir
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel \
    && pip install --upgrade "typing_extensions>=4.12.2" \
    && pip install -e . \
    && pip install --upgrade "typing_extensions>=4.12.2"

# Playwright browser image'a gömülmeli — cache mount kullanılmaz
RUN python -m playwright install --with-deps chromium

# Kod en son kopyalanır — sadece kod değişince bu katman yeniden çalışır
COPY backend ./backend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
