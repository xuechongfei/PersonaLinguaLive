# ===== Stage 1: Build frontend =====
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: Python runtime =====
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLL_ENVIRONMENT=production \
    PLL_FRONTEND_DIST_DIR=/app/frontend/dist

WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv==0.5.0

# 先拷依赖文件做依赖层缓存
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# 拷代码
COPY app/ ./app/

# 拷前端构建产物
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
