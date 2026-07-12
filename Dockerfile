FROM python:3.13-slim

WORKDIR /workspace

# Install requirements
COPY requirements.txt .
RUN python -m venv .venv && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Use dynamic shell variable for PORT compatibility with Render/Railway
CMD ["sh", "-c", ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
