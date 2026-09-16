FROM python:3.11-slim

WORKDIR /app

# System deps needed to build common geo/psycopg2 wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PORT=8000
EXPOSE 8000

# Render injects $PORT at runtime; defaults to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
