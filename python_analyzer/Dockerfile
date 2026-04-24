FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --prefix=/deps --no-cache-dir -r requirements.txt

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY --from=builder /deps /usr/local
COPY . .

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8090
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8090}
