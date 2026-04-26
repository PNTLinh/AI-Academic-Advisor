FROM python:3.11-slim

WORKDIR /app

# Install ONLY psycopg2 runtime deps (not build tools)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Build dependencies layer (install + clean)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc build-essential libpq-dev \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements ONLY (not data)
COPY requirements.txt /tmp/requirements.txt
COPY src/server/requirements.txt /tmp/src_server_requirements.txt

# Install Python deps with cached build
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/src_server_requirements.txt

# Remove build dependencies to shrink image
RUN apt-get remove -y gcc build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy source code ONLY (slim)
COPY src /app/src

# Create empty data directories (no files copied)
RUN mkdir -p /app/data/uploads /app/data/regulations

WORKDIR /app

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.server.main:app --host 0.0.0.0 --port ${PORT}"]
