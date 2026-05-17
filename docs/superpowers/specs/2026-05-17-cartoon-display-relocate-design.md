# 卡通展示位置迁移 — 设计文档

**日期**: 2026-05-17
**类型**: 前端 UI/UX 调整

## 背景

当前 Studio 页面在上传图片后，会把后端生成的卡通 NPC 精灵 (`worldSprites`) 叠加到原图上的对应位置 (`position_x`, `position_y`)。同时，对话框 (`ChatPanel`) 的头部头像也接收 `spriteBase64` 用于展示卡通。

观察到的问题：

1. 原图上叠加卡通让画面变拥挤，且并非用户期望的展示方式。
2. 用户进入对话时，对话框头像有时显示的是兜底的圆脸 `PersonaMouth`，而不是卡通。

## 目标

- 卡通**只**在对话框的 40x40 小头像位置展示，不再叠加在原图上。
- 用户进入对话时，能稳定看到该 entity 对应的卡通。

## 非目标

- 不修改 `PersonaMouth` 组件本身（继续作为兜底）。
- 不调整后端 prompt 或 `world_assets` 生成逻辑。
- 不动 `worldBackground`、`worldReady` 等其他 store 字段。
- 不放大或调整对话框头像的显示尺寸。

## 现状分析

### 卡通叠加在原图上的代码

`frontend/src/pages/StudioPage.tsx:244-267` 渲染了一个 SVG，把 `worldSprites` 中的每一项按 `position_x`, `position_y` 放置到原图上。

### 对话框头像降级到圆脸的原因

`StudioPage.tsx:36-38`:

```ts
const chattingSprite = status.kind === 'chatting'
    ? worldSprites.find((s) => s.entity_id === status.entityId)
    : null;
```

`ChatPanel.tsx:138-147` 根据 `spriteBase64` 是否存在决定显示卡通还是 `PersonaMouth`。

最可能的根因：**LLM 按 salience 过滤掉了部分 entity**。`app/prompts/scene_bible.py:18` 的 prompt 写明 "Only use the top 6 entities by salience as NPCs"，如果原图识别出超过 6 个 entity，低 salience 的不会生成 sprite。但 `HotspotOverlay` 接收的是全量 `analysisResult.entities`，用户点击没有 sprite 的 entity 时，`worldSprites.find()` 返回 undefined，对话框降级到圆脸。

次要可能：LLM 没有严格透传 input 的 `id` 作为 `entity_id`，导致 find 匹配失败。

## 设计

### 改动 1: 移除原图上的卡通精灵 overlay

**文件**: `frontend/src/pages/StudioPage.tsx`

删除 244-267 行（渲染 `worldSprites` 的 `<svg>` 块）。`HotspotOverlay` 保留，用户仍可点击原图中的物体。

### 改动 2: HotspotOverlay 仅展示有 sprite 的 entity

**文件**: `frontend/src/pages/StudioPage.tsx`

在传给 `HotspotOverlay` 的 `objects` 上做一次过滤：

```ts
const interactiveEntities = analysisResult.entities.filter(
  (e) => worldSprites.some((s) => s.entity_id === e.id)
);
```

把 `objects={analysisResult.entities}` 改为 `objects={interactiveEntities}`。

**副作用**: 如果 LLM 过滤了某些 entity，那些 entity 在 UI 上完全不可点击。这是有意为之 — 我们不让用户点击一个会降级到圆脸的 entity。

**显示状态指示**:
- "正在生成卡通..." 的进度条目前用 `worldSprites.length / analysisResult.entities.length` 显示，由于 LLM 可能过滤，这个比例可能永远到不了 100%。需要改成 `worldSprites.length` / `(实际 NPC 数)`。但 `实际 NPC 数` 后端没暴露给前端 — 简化处理：用 `worldReady` 标志位作为 "完成" 的唯一信号，进度条文案改成不显示具体数字（仅显示 "Generating cartoons..."），或者保持现状并接受比例不一定到 100%。

  **决策**：保持现状的比例显示（worldSprites/entities）但接受可能不到 100%。`worldReady` 状态依然由后端 `world_ready` SSE 事件决定，到达后过滤后的 hotspot 会出现。

### 改动 3: 诊断日志（防御 LLM 改 id 的情况）

**文件**: `frontend/src/pages/StudioPage.tsx`

在 `chattingSprite` lookup 后加一个 `useEffect`：当 status 进入 `chatting` 但 `chattingSprite` 取不到时，`console.warn` 打印 `entityId` 和 `worldSprites.map(s => s.entity_id)`。便于事后排查 LLM 改 id 的情况。

### 改动 4: 对话框头像保持原样

**文件**: `frontend/src/components/ChatPanel.tsx`

不修改。继续保持 40x40 圆形头像 + speaking 时边框高亮（`isSpeaking ? 'border-honey' : 'border-sand'`）。`PersonaMouth` 兜底保留，理想情况不再触发。

## 测试计划

### 现有测试需要更新

- `frontend/src/pages/StudioPage.test.tsx`：已检查，无关于原图精灵叠加的断言，无需改动。

### 手动验证

1. 上传一张含 ≤6 个 entity 的图：原图上无卡通叠加；hotspot 可全部点击；点击后对话框头像显示卡通（非圆脸）。
2. 上传一张含 >6 个 entity 的图：低 salience 的 hotspot 不出现；高 salience 的 hotspot 仍可点击；点击后对话框显示卡通。
3. 卡通生成中（worldReady=false）：所有 hotspot 灰显（disabled）。

## 风险

- **过滤过严**：如果 LLM 漏掉一些应该有的 NPC，用户可点击的范围会变小。可通过日志监控这种情况发生的频率，必要时后续调整 `max_npcs` 或 prompt。
- **诊断日志只是 console.warn**：在生产中观察不到，仅在开发调试时有用。后续若问题持续可升级为上报。

## 范围

此设计为单一焦点的小型 UI 调整，预计一个 PR 即可完成。
