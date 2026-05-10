# PersonaLinguaLive

> Anything you see can teach you English.

一款 Web 端 AI 英语学习应用:用户上传一张图片,图中物体被 AI 拟人化后可点击对话,边玩边学。

## 文档导航
- [产品需求文档(PRD)](docs/prd/2026-05-09-personalingualive-prd.md)
- [技术设计文档](docs/design/2026-05-09-personalingualive-design.md)
- [实现计划路线图](docs/plans/README.md)

## 本地开发

### 前置依赖
- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/)

### 后端

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问 http://localhost:5173,顶部 HealthBadge 应显示绿色 `PersonaLinguaLive v0.1.0 · development`。

## 测试

```bash
# 后端
uv run pytest -v
# 前端
cd frontend && npm test
```

## Docker

```bash
docker build -t pll:dev .
docker run --rm -p 8000:8000 pll:dev
```

访问 http://localhost:8000。

## 目录结构

```
app/        FastAPI 后端
frontend/   Vite + React 前端
tests/      后端测试
docs/       PRD / 设计 / 计划文档
```
