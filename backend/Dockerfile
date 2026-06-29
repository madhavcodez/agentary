FROM python:3.14-slim

WORKDIR /app

# System deps for psycopg2 + weasyprint (PDF export)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first so the layer caches when only app code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application source. Build context is ./backend so this is everything in the
# backend module.
COPY . .

ENV PYTHONPATH=/app

# Migrations + server. Alembic raises a clear error if the DB isn't reachable;
# init_db (in app/database.py) also verifies connectivity loudly at startup
# so a degraded boot never silently succeeds.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
