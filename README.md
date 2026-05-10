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

## Phase 2: Vision Pipeline

- 默认使用 `fake` Vision Adapter,无需联网即可端到端跑通。
- 切换到 OpenAI:在 `.env` 设置 `PLL_AI_VISION_PROVIDER=openai` 与 `PLL_OPENAI_API_KEY=...`。
- 上传约束:JPEG / PNG / WebP,单张 ≤ 8MB,默认 6 次/分钟/IP。
- Fake Adapter 触发字节前缀(便于本地手动验证):
  - `PLL_FAKE_FACE`:返回 UNSAFE(模拟人脸)
  - `PLL_FAKE_TEXT`:返回 UNSAFE(模拟整页文字)
  - `unsafe_` 文件名前缀同效

## Phase 3: Conversation Engine

- 点击图片中的物体即可生成 AI 拟人化角色并与之对话。
- **Persona 生成**:LLM 根据物体名称和场景描述生成角色名称、外貌描述和系统提示词,缓存最近 100 个角色。
- **3 段式对话**:每次 LLM 回复包含 `<speak>`(口语对话)、`<learning>`(知识点)、`<followup>`(追问练习)三个段落。
- **流式输出**:LLM 流式 Token 通过 WebSocket 实时推送至前端,支持打字机效果。
- **TTS 语音合成**:助手回复自动转为语音播放,前端 PersonaMouth 组件根据 AnalyserNode 做口型同步。
- **语音输入 (STT)**:MicButton 组件调用浏览器 Web Speech API,支持语音转文字输入。
- **上下文管理**:每个会话维护最近 10 轮对话的滑动窗口,超出后由 LLM 自动总结压缩。
- **学习卡片**:每次回复中的 `<learning>` 和 `<followup>` 以可折叠卡片展示。
- **对话总结**:结束对话后生成总结卡片,包含生词、语法点、流利度评分(1-10)。
- **本地持久化**:对话记录、用户偏好通过 IndexedDB 存储在浏览器端。
- **Provider 切换**:LLM / TTS / STT 均支持 `fake` ↔ `openai` 切换,默认为 `fake`。

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
