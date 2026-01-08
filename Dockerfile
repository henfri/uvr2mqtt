FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime deps (keep small)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps early for layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only application code (not user config or XML)
COPY uvr.py uvr_fetch.py uvr_parse.py uvr_mqtt.py /app/

# Use non-root user
RUN useradd -m uvr && chown -R uvr:uvr /app
USER uvr

# Default command (can be overridden in docker-compose)
CMD ["python", "uvr.py"]
