# PLL v0.3 — Living Scene 模式设计

> 版本：v0.3 草案 · 创建日期：2026-05-13 · 状态：待 review
> 取代当前"看图点物体聊天"的 v0.2 形态。本文档定义 P1 + P2 的合并设计，P3（用户化身可走动探索）延后到独立项目。

---

## 1. 背景与动机

### 1.1 v0.2 现状的问题

测试发现现有方案"拟人化感不够、不身临其境"。根因有三：

1. **图片只是物体目录**：vision 抽 bbox + 1 句 `scene_summary`，scene_summary 在聊天阶段根本没注入到 LLM 上下文里
2. **persona 是"贴在物体上的说话牌"**：prompt 反复强调 *Stay in character as the object*，AI 像一个会说话的杯子在念台词，跟所处场景脱钩
3. **没有"世界"**：没有空间感、感官细节、时间天气、其他实体的存在感；NPC 与 NPC 之间互不知晓

### 1.2 新方向

把"看图聊天"重塑为 **Living Scene（活的小世界）**：

- 上传照片 → AI 把它**卡通化**为一张"小世界"插画（image-to-image）
- 照片里的**主要实体（物 + 人）都被保留**为有"灵魂"的 NPC
- 背景被 AI **补完润色**（窗户、光线、天气、远景）
- 用户点任意 NPC → 进入对话；**其他 NPC 同时"活着"**：眨眼、idle 浮动、偶尔互相看一眼、偶尔冒一句悄悄话
- 真人脸不再被拒，而是在卡通化阶段被替换为卡通角色 → 同时解决肖像权

### 1.3 范围声明

| 包含（P1+P2） | 不包含 |
|---|---|
| 卡通场景生成 | 用户化身在场景里走动（P3） |
| 多 NPC personas + 共享 scene bible | NPC 之间相互对话 / 群聊（V3） |
| NPC sprite 5 帧（default/blink/mouth_a/b/c） | 持久化场景资产到对象存储 |
| Parallax 视差层 | AR 实时摄像头 |
| 环境音 + BGM（精品库） | AI 生成 BGM / 环境音 |
| Ambient loop（glance/gesture/mumble） | 角色记忆跨次对话持久化 |
| 多 NPC 切换（同 session 不同 npc 独立上下文） | viseme 级口型同步 |

---

## 2. 核心概念：Scene Bible

整个会话的所有 LLM 输入和图像生成 prompt 共享一个中心生成产物：**Scene Bible**。它取代当前散落的 `scene_summary` 字符串，是所有下游生成的锚点。

### 2.1 Scene Bible 数据形状

```json
{
  "world": {
    "place": "a cozy independent bookshop café",
    "time_of_day": "late afternoon",
    "weather": "light rain outside",
    "mood": "warm, slightly drowsy",
    "ambient_sounds": ["rain_on_window", "espresso_machine", "page_turns"],
    "bgm_mood": "warm",
    "art_style_prompt": "soft watercolor cartoon, Studio Ghibli inspired, warm palette"
  },
  "npcs": [
    {
      "entity_id": "e1",
      "kind": "object",
      "persona_name": "Mocha",
      "role_in_scene": "the user's regular afternoon coffee, today extra warm",
      "relationship_to_user": "loyal companion who's been with them all week",
      "personality": "warm, slightly philosophical, fond of metaphors",
      "voice_traits": {"gender": "female", "age": "adult", "tone": "warm"},
      "vocab_focus": ["cozy", "steam", "linger", "savor"],
      "ambient_actions": ["takes a slow sip-like steam puff", "hums softly"]
    },
    {
      "entity_id": "e3",
      "kind": "character",
      "persona_name": "Iris",
      "role_in_scene": "a librarian on her afternoon break",
      "relationship_to_user": "a kind regular who recognizes you from yesterday",
      "personality": "thoughtful, observant, fond of book quotes",
      "voice_traits": {"gender": "female", "age": "adult", "tone": "warm"},
      "vocab_focus": ["chapter", "verse", "borrow", "return"],
      "ambient_actions": ["turns a page", "glances out the window"]
    }
  ],
  "cross_relationships": [
    {"from": "e1", "to": "e3", "note": "Iris ordered Mocha this morning; they've spent the afternoon together."}
  ]
}
```

### 2.2 Scene Bible 的下游用途

- **背景生成 prompt**：`art_style_prompt` + `place` + `time_of_day` + `weather`，**强制 erase real people**
- **Sprite 生成 prompt**：每个 NPC 用同一个 `art_style_prompt` 锁画风 + 自身 `role_in_scene` 描述
- **Persona system prompt**（chat）：注入完整 `world` + 当前 NPC 自身条目 + `cross_relationships` 中跟自己相关的项
- **Ambient mumble prompt**：注入 `world` + 该 NPC 的 `personality` + `ambient_actions`
- **环境音/BGM**：`ambient_sounds` 和 `bgm_mood` 受约束只能从音频库 ID 列表里选

---

## 3. 生成管线

### 3.1 全流程

```
上传照片
   ↓
POST /api/vision/analyze
   → Vision LLM：安全检查 + 实体识别（人也算实体）
   → 返回 entities[] + raw_scene 给前端
   → server 后台：触发 scene bible 生成 + world assets 生成
   → 返回 world_id
   ↓
前端 GET /api/world/{world_id} (SSE)
   → 流式收到：scene_bible_ready → background_ready → npc_sprite_ready (×N)
   ↓
ready 状态：用户看到完整 Living Scene，点击进入对话
```

### 3.2 Vision 阶段改造

`app/prompts/vision_safety.py` 重写：

**新规则**：
- 真人脸**不再触发** `is_safe=false`。仅 NSFW / 暴力 / 武器 / 敏感符号 / 主导文字触发不安全
- 输出从 `objects[]` 改名为 `entities[]`，新增字段 `kind: "object" | "character"` 和 `salience: float`
- `entities` 上限 12，scene bible 阶段会按 salience 截前 4-6 个做 NPC

**新 schema**（`app/schemas/vision.py`）：

```python
class Entity(BaseModel):
    id: str
    kind: Literal["object", "character"]
    label: str
    bbox: BBox
    confidence: float
    salience: float = Field(ge=0.0, le=1.0)
    seed: str | None = None
```

`VisionResult.objects` 字段保留为兼容空数组，新增 `entities` 字段。前端切到 `entities`。

### 3.3 Scene Bible 服务

新文件：

- `app/prompts/scene_bible.py` — prompt 模板，输出严格 JSON
- `app/services/scene_bible.py` — `SceneBibleService`，负责调用 LLM + 解析 + cache

**质量保障**：双跑（temperature 0.7 + 0.4），用一个简短的 judge prompt 选更连贯的那份。多花一次 LLM 调用，scene bible 是整个会话的锚，值得这个保险。

**Cache key**：`(image_hash, user_level)`，`image_hash` 在 `POST /api/vision/analyze` 阶段计算后随 `world_id` 一起传给后台 bible 生成任务。LRU，100 条，server 内存，重启即失。

### 3.4 World Assets（背景 + Sprites）

新增适配器层 `app/adapters/imagegen/`：

```
imagegen/
  base.py        # Protocol: text_to_image(prompt) / image_to_image(image, prompt)
  fake.py        # 返回固定 placeholder PNG
  openai.py      # DALL-E / gpt-image-1
  qwen.py        # Qwen-Image-Edit (DashScope)
```

走 `factory.py` 现有套路，env `PLL_AI_IMAGEGEN_PROVIDER` 选择。

新服务 `app/services/world_assets.py`：

```python
class WorldAssetsService:
    async def generate_world(self, bible: SceneBible, original_image: bytes) -> WorldAssets:
        # 并发：
        #   - 背景生成：image-to-image，跑 3 张候选，LLM judge 选最佳
        #   - 每个 NPC sprite 生成：串行 5 帧（reference-image 绑定）
        # N 个 NPC 之间并行
        ...
```

**5 帧 sprite 流程**（单 NPC）：
1. 生成 `default` 帧（text-to-image，用 `art_style_prompt` + NPC 描述）
2. 用 `default` 作为 reference image，生成 `blink`（"same character, eyes closed"）
3. 同样生成 `mouth_a`、`mouth_b`、`mouth_c`
4. 5 帧打包成 `WorldAssets.sprites[entity_id]`

**输出**：所有图像 base64 内联返回。MVP 不引入对象存储。**未来扩展**：当成本 / 流量超阈值时切到 CDN。

**单 NPC 失败处理**：某个 NPC 的 sprite 生成失败（重生 2 次仍失败），降级为只发 `default` 帧；若 `default` 也失败，则该 NPC 退出本场景（前端不渲染），SSE 推送 `error` 事件标注 entity_id。背景生成失败则整个 world 标记失败，让用户重试。

### 3.5 LLM Judge（候选评估）

新 prompt `app/prompts/judge.py` + 函数 `pick_best_candidate(candidates, criteria)`。用于：
- Scene bible 双跑选最佳
- 背景 3 张候选选最佳

```
You are an art director evaluating {N} candidates for {criteria}.
Score each on: {dimensions}. Output JSON: {"best_index": int, "reason": "..."}
```

---

## 4. API 与 Schema 变化

### 4.1 端点变化

| 端点 | 状态 | 说明 |
|---|---|---|
| `POST /api/vision/analyze` | 修改 | 返回 `entities[]`、`world_id`；不返回 personas |
| `GET /api/world/{world_id}` | 新增 | SSE 流式状态 + 资产 |
| `POST /api/persona/generate` | 废弃 | personas 由 scene bible 一次性产出 |
| `WS /api/chat` | 修改 | init frame 改用 `world_id` + `npc_id` |
| `WS /api/chat/ambient` | 新增 | 服务端推送其他 NPC 的 ambient 事件 |
| `POST /api/chat/summary` | 不变 | 摘要逻辑沿用 |

### 4.2 GET /api/world/{world_id} SSE 事件流

```
event: scene_bible_ready
data: {"bible": {...}}

event: background_ready
data: {"image_base64": "...", "width": 1024, "height": 1024}

event: npc_sprite_ready
data: {"entity_id": "e1", "sprites": {"default": "...", "blink": "...", "mouth_a": "...", "mouth_b": "...", "mouth_c": "..."}, "position": {"x": 0.4, "y": 0.6}}

event: world_ready
data: {}

event: error
data: {"stage": "background", "message": "..."}
```

前端按事件渐进式渲染，不等齐。

### 4.3 WS /api/chat init frame

```json
{
  "type": "init",
  "world_id": "w_abc123",
  "npc_id": "e1",
  "user_level": "beginner"
}
```

server 从 `SceneBibleService.get(world_id)` 取 bible 装配 system prompt。

### 4.4 WS /api/chat/ambient

订阅一次贯穿整个聊天 session。事件：

```json
{"type": "ambient", "npc_id": "e3", "event": "glance",  "target": "e1",  "duration_ms": 1000}
{"type": "ambient", "npc_id": "e3", "event": "gesture", "duration_ms": 800}
{"type": "ambient", "npc_id": "e3", "event": "mumble",  "text": "Just one more chapter…", "duration_ms": 3000}
```

频率：15-45s/次（jitter）。规则：
- glance 70% / gesture 20% / mumble 10%
- mumble 走 LLM 现生（轻量 prompt，注入 world + npc personality + 最近主对话上下文摘要）
- mid-response 阶段跳过该 tick（不要打断主对话）
- 优先选与主 NPC 有 cross_relationship 的 NPC

---

## 5. 聊天编排（ChatOrchestrator 改造）

### 5.1 Persona System Prompt 重写

`app/prompts/chat_system.py` 改为从 scene bible 装配：

```
You are {persona_name}, {role_in_scene}.

WORLD:
You exist in {world.place}, it's {world.time_of_day}, {world.weather}.
The mood here is {world.mood}.
You can hear: {world.ambient_sounds (rendered as English phrases)}.

YOUR CHARACTER:
{personality}
Your relationship to the user: {relationship_to_user}.

OTHER SOULS HERE:
{for each other npc in world: "{name}, {role_in_scene}. {cross_relationship_note if any}"}
You CAN reference them naturally ("Iris is reading next to me", "the laptop just sighed again").
You CANNOT speak for them.

GROUNDING RULES:
- Speak as if physically present in this scene. Reference what's around you when natural.
- React to sensory details (the rain, the smell of coffee, the light through the window).
- When the user asks where you are, describe THIS scene from your vantage point.
- Stay in character as {persona_name}, even when teaching.

USER LEVEL ({user_level}): {level_instr}

You MUST format EVERY response with these XML tags:
<speak>...</speak>
<learning>...</learning>
<followup>...</followup>

Rules:
- Always respond in English
- <speak> must be at least 1 sentence
- <learning> can be empty if no teaching point applies
- Keep total response under 5 sentences
```

**Token 体量影响**：system prompt 从 ~250 token 增长到 ~600-900 token。可接受。

### 5.2 多 NPC 切换

- `ContextManager` cache key 从 `session_id` 改为 `(session_id, npc_id)`
- 同一个 `session_id` 内切换 NPC：前端 WS reinit，server 切换 system prompt 与历史
- 前端过场：A sprite 挥手淡出 highlight → B sprite 放大 highlight

### 5.3 Ambient Scheduler

新文件 `app/services/ambient_scheduler.py`：

```python
class AmbientScheduler:
    async def run(self, session_id: str, world_id: str, active_npc_id: str,
                  is_streaming: Callable[[], bool], ws_send: Callable):
        # per-session coroutine, 在 WS 主对话 connect 后启动，disconnect 时取消
        while not cancelled:
            await asyncio.sleep(random.uniform(15, 45))
            if is_streaming():  # ChatOrchestrator 暴露一个 per-session 标志
                continue
            npc_id = pick_npc(world_id, active_npc_id)  # 加权 cross_relationship
            event = weighted_choice({"glance": 0.7, "gesture": 0.2, "mumble": 0.1})
            payload = await build_event(event, npc_id, world_id)
            await ws_send(payload)
```

**streaming 标志**：`ChatOrchestrator` 在 `chat_stream()` 进入流式 LLM 阶段时把 `session_streaming[session_id] = True`，最后 yield `result` 后置 False。`AmbientScheduler` 通过注入的 `is_streaming` callback 查询，避免直接耦合两者。

**已知风险**：mumble 不设上限，成本随 session 时长线性增长。记入 telemetry。

---

## 6. 前端改造

### 6.1 状态机

`StudioStatus` 重写：

```
idle 
  → analyzing       (vision + scene bible 并发)
  → world_loading   (背景 + sprites 渐进到位；部分 NPC 已可点)
  → ready           (用户看到完整 living scene)
  → chatting        (选了某 NPC，主 WS + ambient WS 双通道运行)
  → summary
```

`world_loading` 与 `ready` 可叠加：部分资产到位即可进入交互态。

### 6.2 LivingScene 组件结构

```tsx
<LivingScene worldId={...}>
  <BackgroundLayer src={bg} parallax={0.2} />
  <FarParticles type={world.weather} />     // 雨/雪/光斑
  <NPCLayer parallax={0.6}>
    {npcs.map(npc => <NPCSprite key={npc.id} {...} />)}
  </NPCLayer>
  <UILayer>
    <NameTags />
    <SelectionHalo />
    <MainBubble />
    <MumbleBubbles />
  </UILayer>
  <AudioMixer ambient={world.ambient_sounds} bgm={world.bgm_mood} />
</LivingScene>
```

### 6.3 NPCSprite 行为表

| 行为 | 触发 | 实现 |
|---|---|---|
| idle 浮动 | 永远 | CSS `@keyframes`，±3px / 2.5s，相位随机 |
| blink | 每 4-8s | 切 `blink` 帧 80ms 再切回 `default` |
| talk | TTS 播放中 | `analyserNode` 振幅 → 3 档 mouth |
| selected | 点击 | scale 1.0→1.08 + drop-shadow，他者透明度 0.6 |
| glance | ambient 事件 | 1s `rotateY(±10deg) translateX(±4px)` 朝目标 |
| gesture | ambient 事件 | 切 alt 帧（暂用 `mouth_a` 替代 idle）或微弹 |
| mumble | ambient 事件 | 头顶 `<MumbleBubble text>` 3s 淡出 |

### 6.4 音频

新组件 `<AudioMixer>`：
- `/public/audio/ambient/{id}.mp3` — 预制环境音库（30-50 段）
- `/public/audio/bgm/{mood}.mp3` — 预制 BGM（10-15 首，按 mood 分组）
- 用户可一键静音；默认 ambient 50% / bgm 30% 音量

未来切 AI 音频走 `AudioAssetProvider` 接口，本期实现 `CuratedLibraryProvider`。

### 6.5 加载仪式

`world_loading` 阶段不是冷冰冰的 spinner，而是一段"召唤世界"动画：

- 阶段 1（0-3s）："Summoning this world's inhabitants…"
- 阶段 2（3-12s）：背景 fade-in，NPC 位置出现剪影占位
- 阶段 3（12-30s）：NPC `default` 帧逐个 fade-in，先到的可点
- 阶段 4（30-60s）：blink / mouth 帧到位后**静默替换**到 sprite，用户感觉它"慢慢活过来"

---

## 7. 文件清单

### 7.1 新增

```
app/adapters/imagegen/
  __init__.py
  base.py
  fake.py
  openai.py
  qwen.py
app/services/scene_bible.py
app/services/world_assets.py
app/services/ambient_scheduler.py
app/prompts/scene_bible.py
app/prompts/judge.py
app/prompts/ambient_mumble.py
app/api/world.py
app/schemas/world.py
frontend/src/components/LivingScene/
  LivingScene.tsx
  BackgroundLayer.tsx
  NPCLayer.tsx
  NPCSprite.tsx
  FarParticles.tsx
  MumbleBubble.tsx
  AudioMixer.tsx
  *.test.tsx
frontend/src/lib/worldClient.ts        // SSE for /api/world/{id}
frontend/src/lib/ambientClient.ts      // WS for /api/chat/ambient
frontend/public/audio/ambient/...
frontend/public/audio/bgm/...
```

### 7.2 修改

```
app/prompts/vision_safety.py       # 不再拒人脸，entities 替代 objects
app/prompts/chat_system.py         # 注入 scene bible 三段式
app/schemas/vision.py              # Entity + kind + salience
app/schemas/persona.py             # 部分字段并入 scene bible，本文件可能保留为兼容
app/services/chat_orchestrator.py  # context key 从 session_id → (session_id, npc_id)
app/services/context_manager.py    # 同上
app/api/vision.py                  # 返回 world_id，后台触发 bible+assets
app/api/chat.py                    # WS init 改 world_id + npc_id；ambient 通道
app/config.py                      # 新增 PLL_AI_IMAGEGEN_* 系列
app/adapters/factory.py            # 新增 imagegen factory
frontend/src/lib/store.ts          # StudioStatus 增加 world_loading；chatClient/ambientClient
frontend/src/pages/StudioPage.tsx  # 切到 LivingScene 渲染
frontend/src/lib/chat.ts           # init frame 字段
```

### 7.3 废弃

```
app/api/persona.py                 # 端点废弃，文件保留为空 stub 或删除
app/services/persona_service.py    # 同上
app/prompts/persona_gen.py         # 同上
```

---

## 8. 测试策略

| 层 | 测试方式 |
|---|---|
| Vision prompt | 单测 prompt 装配；mock LLM 返回包含真人脸的 entities，断言 `is_safe=true` 且 `kind="character"` |
| Scene bible | mock LLM 双跑场景，验证 judge 选取；strict JSON 解析失败重试一次 |
| ImageGen 适配器 | 与现有 vision/tts 同款：每条 HTTP 路径一个测试，验证 auth/payload，错误抛 `UpstreamFailureError(provider=...)` |
| WorldAssetsService | mock 适配器加人为延迟，断言总耗时 ≈ max(子任务)，不是 sum；5 帧 sprite 串行约束 |
| Ambient scheduler | patch `asyncio.sleep` + fake LLM，验证 mid-response 跳过、cross_relationship 加权、3 种 event 分布 |
| ChatOrchestrator | context key 切换正确，同 session 不同 npc 历史隔离 |
| LivingScene | vitest + RTL：sprite 渲染、selected 高亮、ambient 事件 → DOM 变化、parallax transform 计算正确 |
| 集成 E2E | happy path：上传 → vision → bible → assets → 选 NPC → 1 轮聊天 → 1 次 ambient → summary；全程 fake 适配器 |

新增 `FakeImageGenAdapter`：返回固定的 1×1 透明像素 base64。

---

## 9. 已知风险与缓解

| 风险 | 缓解 |
|---|---|
| 首屏 30-60s / 完整 60-120s | 渐进呈现 + "召唤世界"仪式动画 + `default` 帧到位即可聊 |
| Sprite 5 帧画风漂移 | 强制 reference-image 绑定，judge 评估，不达标重生（重生上限 2 次） |
| Scene bible JSON 解析失败 | strict JSON 模式 + 1 次自动重试 + fallback 到最小 bible |
| Ambient mumble 成本无上限 | telemetry 监控，阈值告警；未来可降级 |
| 卡通化破坏原图人物身份 | image-to-image prompt 强制 erase all real people；sprite 生成完全脱离原人脸特征。**法务安全是设计目标** |
| ImageGen API 限流 | adapter 内置指数退避 + 单 NPC 串行（已是设计） |
| MiniMax voice 与推荐音色不匹配 | `voice_picker` 现有 3 级 fallback 兼容 |
| Context Manager key 改造影响旧会话 | MVP 无持久化，server 重启即清；frontend IndexedDB 历史按旧格式只读保留 |
| ambient WS 与主 WS 并发竞态 | 主 WS 在 streaming 时设置一个 per-session flag，scheduler tick 时检查跳过 |

---

## 10. 决策日志

| # | 决策 | 备选 | 选择理由 |
|---|---|---|---|
| D1 | 对话主体 = "场景里的多个灵魂"，物 + 人都是 NPC | 仅物体拟人 / 仅场景里人 / 双模式 | 用户明确希望"人和物都有灵魂、游戏感" |
| D2 | 范围 = P1 + P2 合并设计 | 只做 P1 / 一口气做到 P3 | 用户选择"先别动 P3，重设计 P1+P2" |
| D3 | 卡通化 = image-to-image 全图重生 + 分层（背景 + sprite） | 一张图全烤 / 混合滤镜 | 仅分层可支撑 P2 的 NPC 动效 |
| D4 | 卡通场景 = 保留主体 + 环境补完 | 全 AI 重绘 / 严格保留构图 | 用户认得"自己的东西"且有沉浸场景感 |
| D5 | NPC 协作 = 主体专注 + 周边环境反应 | 多主体混聊 / 严格一对一 | 学习场景需要主对话清晰，又要"世界活着" |
| D6 | Sprite = 5 帧 + reference-image 锁定 | 单帧 + 前端廉价合成 / 跳过表情 | 用户要求"最高标准、不考虑成本" |
| D7 | 背景生成 = 3 张候选 + LLM judge 选优 | 单跑 / 5 张候选 | 平衡质量与延迟 |
| D8 | Scene bible = 双跑 + judge 选优 | 单跑 / 不评估 | 它是所有下游的锚，值得加保险 |
| D9 | Ambient mumble = 不设上限、运行时现生 | 5 句上限 / 预生 20 句池 | 用户要求"哪种质量高用哪个"，现生最贴上下文 |
| D10 | 环境音 / BGM = 精品库而非 AI 生成 | AI 生成 BGM | 当前 AI 音频天花板低于精品库；用接口预留未来切换 |
| D11 | 资产存储 = base64 内联（MVP） | 对象存储 + URL | MVP 不引入存储依赖；未来按流量切换 |
| D12 | Vision 不再拒真人脸 | 维持现状 | 卡通化在背景生成阶段已抹除真人，肖像权由 image gen prompt 守护 |

---

## 11. 后续工作

设计通过后，下一步是**实施计划**（通过 `superpowers:writing-plans` 生成）。计划应按以下顺序：

1. ImageGen 适配器层（fake + 一个真适配器）—— 基础设施
2. Vision prompt 改造 + Entity schema —— 上游
3. Scene Bible 服务（prompt + service + judge）—— 核心生成
4. World Assets 服务（并行编排）—— 资产生成
5. /api/world SSE 端点
6. ChatOrchestrator 与 ambient scheduler
7. 前端 LivingScene 组件族
8. 前端 worldClient / ambientClient
9. 音频库素材整理 + AudioMixer
10. 集成 E2E + 加载仪式打磨

P3（用户化身走动探索）作为独立项目，等本期上线后再启动。
