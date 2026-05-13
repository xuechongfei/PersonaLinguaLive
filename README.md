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
- **Provider 切换**:LLM / TTS / STT 均支持 `fake` / `openai` / 国产厂商切换,默认为 `fake`。

## Phase 4: Adaptive Coach

- **Learner Profile**:`LevelSelector` 在首页显示,选择的英语水平(beginner / intermediate / advanced)经 IndexedDB 持久化,跨刷新保留并注入到 Persona 生成与对话 system prompt。
- **会话历史**:每次完成对话后自动写入 IndexedDB,`#/history` 路由按时间倒序列出过往会话,点击行打开只读 Summary。
- **个人生词本**:对话总结里的 `new_words` 变为 `{word, definition, example}` 结构;`SummaryCard` 自动入库,`#/vocab` 提供 “All / Review” 两个 Tab。
- **SM2-lite 间隔复习**:复习页提供 Again / Hard / Good / Easy 四档评分,SRS 调度更新 `ease / intervalDays / dueAt`,再次保存同一单词不会重置进度。
- **自适应提示词**:开始对话前前端 `collectLearnerContext()` 收集最近 20 个生词与最近一次会话的 `areasToImprove`,作为 system role 消息前置注入到 LLM 上下文,Persona 会自然复用学过的词。
- **首字音频低延迟**:`ChatOrchestrator` 在 `</speak>` 闭合的瞬间用 `asyncio.create_task` 启动 TTS,边继续流式 `learning / followup` 边等音频;新增 `speak_text` / `audio` 两个事件,音频先到、`result` 后到。
- **口型同步**:`ChatPanel` 内部持有一个懒加载的 `AudioContext + AnalyserNode`,将播放的 `<audio>` 元素接入 Web Audio,`PersonaMouth` 用频谱平均值驱动嘴部张合。

## Phase 5: Visual Polish & Experience Upgrade

- **Zustand 状态管理**:将 StudioPage 中分散的 `useState`/`useRef` 迁移至 Zustand store (`frontend/src/lib/store.ts`),匹配设计文档原先规划的架构。
- **物体口型叠加 (SpeakingOverlay)** :对话时 `PersonaMouth` 直接渲染在图片被点击物体上,通过 SVG `<foreignObject>` 定位到物体 bbox,和 HotspotOverlay 共享同一坐标空间。
- **ChatPanel 口型联动**:`AnalyserNode` 和 `isSpeaking` 状态从 ChatPanel 提升至 Zustand store,Sidebar 头像与物体嘴巴同时随音频动。
- **表情动画**:`PersonaMouth` 新增眨眼(2-5s 随机间隔,说话时加速)、眼球注视漂移(±3px lerp)、说话时眼睛放大。
- **内置场景图库 (SceneGallery)** :免拍照即可上手,提供 Kitchen / Study Desk / Living Room / Cafe / Park / Bedroom 6 个预设场景,点击后走与上传相同的分析流水线。
- **架构改进**:图片与聊天面板不再互斥——对话时图片、热区、口型叠加层、侧边栏同屏显示,支持中途点击其他物体切换角色。

## Provider / Adapter Matrix

| Capability | Adapters available |
|---|---|
| Vision | `fake`, `openai` (gpt-4o), `qwen` (qwen-vl-max-latest, DashScope) |
| LLM    | `fake`, `openai` (gpt-4o-mini), `deepseek` (deepseek-v4-flash) |
| TTS    | `fake`, `openai` (tts-1-hd), `minimax` (speech-02-hd, 300+ voices) |
| STT    | `fake`, `openai` (whisper-1); frontend uses Web Speech API as primary |

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
