FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - gcc, libpq-dev: for psycopg2 (PostgreSQL driver)
# - libpango*, libcairo2, libgdk-pixbuf*, libffi-dev, shared-mime-info: for WeasyPrint (PDF reports)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (much smaller than full CUDA version)
# Railway has no GPU, so CUDA support is unnecessary bloat
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Pre-download CodeBERT model during build
# This happens once at build time, not on every cold start

# Create entrypoint script that runs migrations and collectstatic at startup

ENTRYPOINT ["/app/entrypoint.sh"]

# Run with Daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
