FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/deps --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

COPY --from=builder /deps /usr/local
COPY . .

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8090
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8090}
