FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN pip install --no-cache-dir "uv==0.12.3" \
    && uv sync --frozen --no-dev

CMD ["python", "-m", "uvicorn", "bdlh_runtime.run_api:app", "--host", "0.0.0.0", "--port", "8090"]
