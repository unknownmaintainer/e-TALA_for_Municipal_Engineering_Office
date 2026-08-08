# Use a slim Python 3.13 image as the base
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set the working directory
WORKDIR /app

# Install system dependencies needed for compiling psycopg2 and general packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Build static assets (WhiteNoise will serve them)
RUN python manage.py collectstatic --no-input

# Set executable permission on entrypoint script
RUN chmod +x /app/entrypoint.sh

# Create non-root user for container security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Start via entrypoint script (runs migrations automatically before gunicorn)
CMD ["/app/entrypoint.sh"]
