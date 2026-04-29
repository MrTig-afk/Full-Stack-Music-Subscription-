FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install uv and project dependencies from pyproject/lock
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --frozen --no-dev

# Copy application
COPY . /app

# Re-sync in case source tree adds local package files
RUN uv sync --frozen --no-dev

EXPOSE 80

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers"]
