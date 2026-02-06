FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./requirements.txt
COPY GoogleFindMyTools/requirements.txt ./GoogleFindMyTools/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# Run as non-root user.
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 9824

CMD ["python", "prometheus_exporter.py"]
