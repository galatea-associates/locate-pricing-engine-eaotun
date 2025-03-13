# syntax=docker/dockerfile:1.4

# Use a multi-stage build to reduce the final image size
# --- Builder Stage ---
FROM python:3.11-slim AS builder
# Description: Build stage for compiling dependencies and preparing the application

# Set working directory
WORKDIR /app
# Step: Set working directory to /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Step: Install build dependencies (gcc, python3-dev, etc.)

# Copy requirements.txt
COPY ./requirements.txt .
# Step: Copy requirements.txt to container

# Create Python wheel packages for all dependencies
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt
# Step: Create Python wheel packages for all dependencies

# --- Runtime Stage ---
FROM python:3.11-slim AS runtime
# Description: Runtime stage for the final container image

# Set working directory
WORKDIR /app
# Step: Set working directory to /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
# Step: Set environment variables for Python (PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED)

# Copy wheels from builder stage
COPY --from=builder /app/wheels /app/wheels
COPY --from=builder /app/requirements.txt .
# Step: Copy wheels from builder stage

# Install wheels with pip (no network access needed)
RUN pip install --no-cache-dir --no-index --find-links=/app/wheels -r requirements.txt
# Step: Install wheels with pip (no network access needed)

# Remove wheel directory to reduce image size
RUN rm -rf /app/wheels
# Step: Remove wheel directory to reduce image size

# Copy application code
COPY ./app /app
# Step: Copy application code to container

# Create and switch to non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
USER appuser
# Step: Create and switch to non-root user

# Expose port 8000
EXPOSE 8000
# Step: Expose port 8000 for the API

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl --fail http://localhost:8000/api/v1/health || exit 1
# Step: Set health check command

# Define entry point
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "120", "--keep-alive", "5", "--log-level", "info", "main:app"]
# Step: Define entry point using gunicorn with appropriate worker configuration