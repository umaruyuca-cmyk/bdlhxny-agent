FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN pip install --no-cache-dir "uv==0.12.3" \
    && uv sync --frozen --no-dev

# 当前镜像只验证评测与上下文算法包可构建。私有 case_id API 完成后再提供常驻服务入口。
CMD ["python", "-c", "import bdlh_runtime; print('touchstone-engine image ready')"]
