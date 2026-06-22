FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev || uv sync --no-dev

COPY src ./src

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "inventory_booking_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
