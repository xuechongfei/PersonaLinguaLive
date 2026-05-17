# Cartoon Display Relocate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把生成的卡通从原图叠加层移除，仅在对话框的 40x40 小头像中展示，并确保进入对话时小头像稳定显示卡通而非圆脸兜底。

**Architecture:** 单文件前端调整。`StudioPage.tsx` 删除原图上的 worldSprites SVG 叠加；同时把 `HotspotOverlay` 接收的 entities 过滤为「在 worldSprites 中存在对应 sprite 的 entity」；并在 chattingSprite 取不到时打 console.warn 用于诊断。

**Tech Stack:** React + TypeScript + Vite + Zustand + Vitest + Testing Library

**Spec:** `docs/superpowers/specs/2026-05-17-cartoon-display-relocate-design.md`

---

## File Structure

**Modified:**
- `frontend/src/pages/StudioPage.tsx` — 删除 sprite overlay；hotspot 过滤；加诊断 warn
- `frontend/src/pages/StudioPage.test.tsx` — 现有测试需要补充 worldSprites 注入；新增过滤行为测试和诊断 warn 测试

**Unchanged but related:**
- `frontend/src/components/HotspotOverlay.tsx` — props 接口不变
- `frontend/src/components/ChatPanel.tsx` — 头像逻辑已就绪，不动
- `frontend/src/lib/store.ts` — 已有 `addWorldSprite` action，无需新增

---

## Task 1: 让现有测试给 worldSprites 添加 fixtures

**Files:**
- Modify: `frontend/src/pages/StudioPage.test.tsx`

**Background:** 现有测试在 `beforeEach` 调用了 `setWorldReady(true)` 但没注入任何 sprite。Task 2 引入「按 sprite 过滤 hotspot」后，原 entity `obj_1` 没有 sprite 会导致 hotspot 不渲染，所有依赖点击 hotspot 的测试都会断。先把测试 fixture 改对，避免被后续改动连带打断。

- [ ] **Step 1: 在测试文件顶部添加一个 sprite mock fixture**

把现有的 `mockAnalyzeResponse` 常量保持不变，新增一个 sprite 常量。在第 89 行 `};` 之后（`mockSummaryResponse` 之前）插入：

```typescript
const mockSpriteForObj1 = {
  entity_id: 'obj_1',
  sprites: {
    default: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
    blink: '',
    mouth_a: '',
    mouth_b: '',
    mouth_c: '',
  },
  position_x: 0.2,
  position_y: 0.2,
};
```

- [ ] **Step 2: 在 beforeEach 中注入 sprite**

修改 `beforeEach`（第 92-102 行），在 `setWorldReady(true)` 之后增加一行：

```typescript
beforeEach(() => {
  vi.clearAllMocks();
  useStudioStore.getState().reset();
  useStudioStore.getState().setWorldReady(true);
  useStudioStore.getState().addWorldSprite(mockSpriteForObj1);
  URL.createObjectURL = vi.fn(() => 'blob:fake') as typeof URL.createObjectURL;
  URL.revokeObjectURL = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();

  (analyzeImage as any).mockResolvedValue(mockAnalyzeResponse);
  (fetchSummary as any).mockResolvedValue(mockSummaryResponse);
});
```

- [ ] **Step 3: 运行测试确认无回归**

Run: `cd frontend && npm test -- --run StudioPage`
Expected: 所有现有 5 个用例继续 PASS（此时还没引入过滤，但 sprite 注入也不影响任何断言）

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/StudioPage.test.tsx
git commit -m "test(studio): preload worldSprite fixture in beforeEach"
```

---

## Task 2: HotspotOverlay 按 sprite 可用性过滤 entities

**Files:**
- Modify: `frontend/src/pages/StudioPage.tsx:233-241` (HotspotOverlay 渲染处)
- Test: `frontend/src/pages/StudioPage.test.tsx`

- [ ] **Step 1: 写一个新的失败测试 — 没有 sprite 的 entity 不渲染 hotspot**

在 `StudioPage.test.tsx` 文件末尾 `describe('StudioPage', () => {` 块内（最后一个 `it` 之后，闭合 `});` 之前）追加：

```typescript
it('hides hotspot for entities without a matching sprite', async () => {
  // Override beforeEach: clear sprites so obj_1 has no matching sprite.
  useStudioStore.getState().reset();
  useStudioStore.getState().setWorldReady(true);
  // No addWorldSprite call here — worldSprites stays empty.

  setupImageUpload();
  await waitForImageLoad();

  // Wait a tick for analyze to settle, then assert no hotspot button exists.
  await waitFor(() => {
    expect(screen.queryByRole('button', { name: /teacup/i })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm test -- --run StudioPage -t "hides hotspot"`
Expected: FAIL — `expect(...).not.toBeInTheDocument()` 失败，因为当前 HotspotOverlay 接收全部 entities，hotspot 仍然渲染。

- [ ] **Step 3: 在 StudioPage.tsx 实现过滤**

在 `StudioPage.tsx` 中，把 `chattingSprite` 计算附近（第 36-38 行附近）新增一个派生：

定位到这段代码：

```typescript
const chattingSprite = status.kind === 'chatting'
    ? worldSprites.find((s) => s.entity_id === status.entityId)
    : null;
```

在它下面新增：

```typescript
const interactiveEntities = analysisResult
  ? analysisResult.entities.filter(
      (e) => worldSprites.some((s) => s.entity_id === e.id)
    )
  : [];
```

然后在第 234 行附近找到 `HotspotOverlay` 使用处：

```tsx
{(status.kind === 'ready' || status.kind === 'chatting') && imageSize && analysisResult && (
  <HotspotOverlay
    renderedWidth={imageSize.renderedWidth}
    renderedHeight={imageSize.renderedHeight}
    objects={analysisResult.entities}
    onSelect={handleSelectObject}
    disabled={!worldReady}
  />
)}
```

把 `objects={analysisResult.entities}` 改为 `objects={interactiveEntities}`：

```tsx
{(status.kind === 'ready' || status.kind === 'chatting') && imageSize && analysisResult && (
  <HotspotOverlay
    renderedWidth={imageSize.renderedWidth}
    renderedHeight={imageSize.renderedHeight}
    objects={interactiveEntities}
    onSelect={handleSelectObject}
    disabled={!worldReady}
  />
)}
```

- [ ] **Step 4: 运行新测试确认通过**

Run: `cd frontend && npm test -- --run StudioPage -t "hides hotspot"`
Expected: PASS

- [ ] **Step 5: 运行整组测试确认无回归**

Run: `cd frontend && npm test -- --run StudioPage`
Expected: 全部 6 个用例 PASS（5 原有 + 1 新增）

- [ ] **Step 6: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无 type error

- [ ] **Step 7: 提交**

```bash
git add frontend/src/pages/StudioPage.tsx frontend/src/pages/StudioPage.test.tsx
git commit -m "feat(studio): hide hotspots for entities without a sprite"
```

---

## Task 3: 移除原图上的卡通精灵 SVG 叠加

**Files:**
- Modify: `frontend/src/pages/StudioPage.tsx:243-267` (sprite overlay SVG 块)

- [ ] **Step 1: 删除 worldSprites 渲染块**

在 `StudioPage.tsx` 中定位下面这段（约 243-267 行），整段删除：

```tsx
{/* NPC sprites overlay */}
{worldSprites.length > 0 && imageSize && (
  <svg
    className="absolute inset-0 pointer-events-none"
    width={imageSize.renderedWidth}
    height={imageSize.renderedHeight}
    viewBox={`0 0 ${imageSize.renderedWidth} ${imageSize.renderedHeight}`}
  >
    {worldSprites.map((s) => {
      const sx = s.position_x * imageSize.renderedWidth;
      const sy = s.position_y * imageSize.renderedHeight;
      const size = Math.min(imageSize.renderedWidth, imageSize.renderedHeight) * 0.15;
      return (
        <image
          key={s.entity_id}
          href={`data:${s.sprites.default.startsWith('/9j/') ? 'image/jpeg' : 'image/png'};base64,${s.sprites.default}`}
          x={sx - size / 2}
          y={sy - size / 2}
          width={size}
          height={size}
        />
      );
    })}
  </svg>
)}

```

删除后，紧接在 `HotspotOverlay` 的结束括号 `)}` 下面应该直接是 `</div>` （包裹 ImageCanvas 的容器闭合标签前）。

- [ ] **Step 2: 运行测试确认无回归**

Run: `cd frontend && npm test -- --run StudioPage`
Expected: 全部 6 个用例 PASS

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无 type error

- [ ] **Step 4: 浏览器手动验证**

启动后端和前端：

```bash
# Terminal 1
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

打开 `http://localhost:5173`，上传一张含多个物体的照片，验证：
- 原图上**不再**显示任何卡通精灵叠加
- hotspot 矩形框仍能显示并可点击
- 点击 hotspot 进入对话后，对话框左上角的小头像显示**卡通**（不是圆脸）

如果对话框依然显示圆脸：检查浏览器 console 是否有诊断 warn（Task 4 会加），但此时 Task 4 还没做。可以暂时容忍，由 Task 4 帮助诊断。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/StudioPage.tsx
git commit -m "refactor(studio): remove cartoon sprite overlay from source image"
```

---

## Task 4: 添加 chattingSprite 缺失时的诊断日志

**Files:**
- Modify: `frontend/src/pages/StudioPage.tsx` (新增 useEffect)
- Test: `frontend/src/pages/StudioPage.test.tsx`

- [ ] **Step 1: 写一个失败测试 — sprite 缺失时 console.warn 应被调用**

在 `StudioPage.test.tsx` 文件末尾 `describe('StudioPage', () => {` 块内追加：

```typescript
it('warns when chatting starts but no sprite matches entity', async () => {
  // Override beforeEach: install a sprite for a different entity, so obj_1 has no match.
  useStudioStore.getState().reset();
  useStudioStore.getState().setWorldReady(true);
  useStudioStore.getState().addWorldSprite({
    entity_id: 'obj_OTHER',
    sprites: { default: 'X', blink: '', mouth_a: '', mouth_b: '', mouth_c: '' },
    position_x: 0,
    position_y: 0,
  });

  const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

  setupImageUpload();
  await waitForImageLoad();

  // No hotspot for obj_1 (Task 2 filter hides it), so we directly drive the store
  // into the chatting state to simulate a stale entity_id condition.
  useStudioStore.getState().setStatus({
    kind: 'chatting',
    personaName: 'teacup (object)',
    sessionId: 's',
    entityId: 'obj_1',
  });

  await waitFor(() => {
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('chattingSprite'),
      expect.objectContaining({ entityId: 'obj_1' })
    );
  });

  warnSpy.mockRestore();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm test -- --run StudioPage -t "warns when chatting"`
Expected: FAIL — `warnSpy` 未被调用，因为还没有诊断 useEffect。

- [ ] **Step 3: 在 StudioPage.tsx 添加诊断 useEffect**

在 `StudioPage.tsx` 已有的 `useEffect(() => { loadProfile()... }, []);` 之后追加：

```typescript
useEffect(() => {
  if (status.kind === 'chatting' && !chattingSprite) {
    console.warn('chattingSprite missing for entity', {
      entityId: status.entityId,
      availableSpriteIds: worldSprites.map((s) => s.entity_id),
    });
  }
}, [status, chattingSprite, worldSprites]);
```

注意需要把 `useEffect` 导入到顶部 import — 文件第 1 行已有 `import { useEffect } from 'react';`，无需修改。

- [ ] **Step 4: 运行新测试确认通过**

Run: `cd frontend && npm test -- --run StudioPage -t "warns when chatting"`
Expected: PASS

- [ ] **Step 5: 运行整组测试确认无回归**

Run: `cd frontend && npm test -- --run StudioPage`
Expected: 全部 7 个用例 PASS（6 之前 + 1 新增）

- [ ] **Step 6: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无 type error

- [ ] **Step 7: 提交**

```bash
git add frontend/src/pages/StudioPage.tsx frontend/src/pages/StudioPage.test.tsx
git commit -m "feat(studio): warn when chattingSprite is missing"
```

---

## 完工验证

- [ ] **Step 1: 全量前端测试**

Run: `cd frontend && npm test -- --run`
Expected: 全部 PASS

- [ ] **Step 2: Lint（如果项目有 ESLint）**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无 error

- [ ] **Step 3: 浏览器端到端验证**

启动 backend (`uv run uvicorn app.main:app --reload --port 8000`) 和 frontend (`cd frontend && npm run dev`)。

验证矩阵：

| 场景 | 期望行为 |
|---|---|
| 上传含 ≤6 entity 的照片 | 原图无卡通；所有 hotspot 可点击；点击后小头像显示卡通 |
| 上传含 >6 entity 的照片 | 低 salience entity 的 hotspot 不出现；高 salience 的可点击；小头像显示卡通 |
| 卡通生成中（worldReady=false） | 所有 hotspot 灰显（disabled） |
| 万一进对话仍显示圆脸 | F12 console 应能看到 `chattingSprite missing for entity` warn |
