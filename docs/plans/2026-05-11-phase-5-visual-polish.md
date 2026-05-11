# Phase 5: Visual Polish & Experience Upgrade

> **Status:** 🔨 In Progress
> **Planned date:** 2026-05-11
> **PRD reference:** `docs/prd/2026-05-09-personalingualive-prd.md` v0.1 (V2 modules)
> **Design reference:** `docs/design/2026-05-09-personalingualive-design.md` v0.1

## Context

Phase 4 completed the V1 MVP feature set — the app works end-to-end: upload → analyze → chat → summary → review vocab. But two rough edges remain:

1. **PersonaMouth lives in the sidebar, not on the object.** The design doc envisioned the mouth "growing onto" the detected object when it starts speaking. Currently `PersonaMouth` is a standalone avatar inside `ChatPanel`'s header — disconnected from the image. Users see a face in a panel, not "the cup is talking to me."

2. **State management is scattered `useState`/`useRef`.** The design doc (Section 1.1) explicitly prescribed Zustand as the state layer. `StudioPage` has grown to 280 lines with one giant discriminated-union `status` state, three refs, and ad-hoc prop threading. Adding any feature (like mouth-on-object) requires more drilling or more refs.

3. **No built-in scenes.** Users must upload a photo every time. PRD V2 calls for a built-in scene gallery so users can start practicing immediately without a camera.

4. **Static persona faces.** `PersonaMouth` has a fixed expression — no blinking, no gaze direction. Adding subtle eye animation makes the persona feel alive.

**Phase 5 goal:** tighten the visual experience so the persona *feels* like it lives inside the image, and clean up the frontend architecture to match the original design intent.

---

## Goals

1. Migrate StudioPage state to a Zustand store, matching the design doc's architecture.
2. Render `PersonaMouth` on the selected object's bounding box in the image — the mouth "grows onto" the object.
3. Add subtle eye animation (blink, gaze) to `PersonaMouth` so the face feels alive.
4. Add a built-in scene gallery so users can start without uploading a photo.

Non-goals: multi-persona chat, pronunciation scoring, cross-device sync, account system. These remain deferred to later phases.

---

## Sub-phase 5.1 — Zustand State Migration

Replace the `useState`/`useRef` sprawl in `StudioPage` with a single Zustand store.

**New file**
- `frontend/src/lib/store.ts` — Zustand store with `useStudioStore` hook.

**Store shape**

```ts
interface StudioState {
  // Upload & image
  file: File | null;
  imageSize: ImageReadyInfo | null;
  
  // Analysis
  status: StudioStatus; // discriminated union, same shape as current
  analysisResult: VisionAnalyzeResponse | null;
  errorMessage: string;
  
  // Persona & session
  selectedObject: DetectedObject | null;
  sessionId: string;
  personaName: string;
  personaId: string;
  
  // Chat plumbing (non-serializable, kept in refs inside the store via subscribeWithSelector or separate)
  chatClient: ChatClient | null;
  
  // Conversation persistence
  conversation: ConversationData | null;
  
  // User level
  level: UserLevel;
  
  // Audio wiring (set by ChatPanel, read by PersonaMouth on image)
  analyserNode: AnalyserNode | undefined;

  // Actions
  setFile: (f: File | null) => void;
  setLevel: (level: UserLevel) => void;
  setStatus: (s: StudioStatus) => void;
  setAnalysisResult: (r: VisionAnalyzeResponse) => void;
  startChat: (sessionId: string, personaName: string, personaId: string) => void;
  endChat: () => void;
  setAnalyserNode: (n: AnalyserNode | undefined) => void;
  reset: () => void;
}
```

**Files modified**
- `frontend/src/pages/StudioPage.tsx` — delete inline `useState`/`useRef` declarations; call `useStudioStore()` instead. Actions (`handleFile`, `handleSelectObject`, `handleEndChat`, etc.) become standalone functions or store actions.
- `frontend/src/components/ChatPanel.tsx` — remove `analyserNode` from local state; write it into the store via `setAnalyserNode`.
- `frontend/src/lib/store.ts` — NEW
- `frontend/src/lib/store.test.ts` — NEW

**Verification:** All existing StudioPage and ChatPanel tests pass without modification since component APIs stay the same. New store unit tests cover action transitions.

---

## Sub-phase 5.2 — PersonaMouth on Object Bbox

When the user clicks an object and chat starts, `PersonaMouth` appears *on the image* at that object's bounding box — not just in the sidebar.

**Approach:** Create a `SpeakingOverlay` component rendered as a sibling to `HotspotOverlay` (same SVG coordinate space). When `status.kind === 'chatting'` and we have a `selectedObject`, render `PersonaMouth` positioned at the object's bbox.

**Files created**
- `frontend/src/components/SpeakingOverlay.tsx` — reads `selectedObject`, `imageSize`, `analyserNode`, `isSpeaking` from the Zustand store. Renders an SVG `<foreignObject>` at the bbox position containing `PersonaMouth`.
- `frontend/src/components/SpeakingOverlay.test.tsx`

**Files modified**
- `frontend/src/components/PersonaMouth.tsx` — accept optional `size` prop to scale the SVG; remove the fixed `w-28 h-28` class and make it responsive.
- `frontend/src/pages/StudioPage.tsx` — render `<SpeakingOverlay />` alongside `<HotspotOverlay>` when the image is visible and chat is active. Pass `isSpeaking` state down (or read from store).
- `frontend/src/components/ChatPanel.tsx` — the `PersonaMouth` in the header becomes optional or is removed when mouth-on-object is active. Keep it for the "no image visible" or "small screen" fallback.

**Positioning math:** The object's bbox uses normalized coordinates (0-1). Scale to image rendered size. Place `PersonaMouth` centered horizontally, near the top of the bbox. Size = `min(w, h) * 0.6` to fit inside.

**Edge cases:**
- Object bbox too small (< 60px either dimension): hide the mouth on image, show only in ChatPanel.
- User switches objects mid-chat: `SpeakingOverlay` moves to the new object's bbox.
- Audio not yet started (`analyserNode` undefined): show the pulse fallback animation.

**Verification:** Click an object → mouth SVG appears on the image at the correct position. Send a message → mouth animates with audio amplitude. End chat → mouth disappears from image.

---

## Sub-phase 5.3 — Expression & Eye Animation

Add blinking and subtle eye movement to `PersonaMouth` so it looks alive rather than static.

**Files modified**
- `frontend/src/components/PersonaMouth.tsx` — add blink animation (eyes briefly close every 2-5s at random intervals) and subtle gaze drift (pupils shift ±3px over time).

**Animation specs:**
- **Blink:** Every 2000-5000ms (random per blink), eyes close for 150ms (quick close → 100ms hold → quick open). Use `setTimeout` chain, not `requestAnimationFrame`.
- **Gaze:** Pupils drift slowly (lerp over 3-5s to a random offset within ±3px of center). Use `requestAnimationFrame` with a separate interval.
- **When speaking:** blink rate increases (every 800-2000ms). Eyes widen slightly (ry: 5→7).

**Verification:** Render `PersonaMouth` for 10+ seconds → eyes blink at irregular intervals. Start speaking → blink rate noticeably increases.

---

## Sub-phase 5.4 — Built-in Scene Gallery

Add a set of curated scene images so users can start a session without uploading a photo.

**Files created**
- `frontend/src/components/SceneGallery.tsx` — grid of 4-6 preset scene cards. Each card shows a thumbnail + scene name. Clicking one loads a bundled image and triggers the same analysis flow as a file upload.
- `frontend/src/components/SceneGallery.test.tsx`

**Scenes (bundled as static assets):**
1. Kitchen — counter with appliances, utensils, ingredients
2. Study Desk — laptop, books, stationery, coffee mug
3. Living Room — sofa, TV, plants, bookshelf
4. Cafe — coffee cup, pastry, newspaper, laptop
5. Park — bench, tree, bicycle, fountain
6. Bedroom — bed, wardrobe, mirror, lamp

**Assets:** Store scenes in `frontend/public/scenes/` as optimized WebP (~200KB each). Include a `scenes.json` manifest listing names, filenames, and brief descriptions.

**Files modified**
- `frontend/src/pages/StudioPage.tsx` — render `<SceneGallery />` in the idle/upload state as a secondary option below `UploadZone`. Selecting a scene fetches `/scenes/{filename}` as a Blob, then feeds it through the same `handleFile` pipeline.
- `frontend/src/pages/HomePage.tsx` — add a "Browse Scenes" shortcut that navigates to `#/studio` and auto-opens the gallery section.

**Edge case:** Scene image fails to load → show an error toast, keep the upload option available.

**Verification:** On Studio page (idle state), scene gallery is visible below upload zone. Click a scene → image appears on canvas → hotspots render → user can click objects and chat.

---

## Sub-phase 5.5 — Integration & Polish

**Files modified**
- `frontend/src/pages/StudioPage.tsx` — final cleanup after 5.1-5.4: remove any remaining unused imports, ensure all store-read values are stable.
- `README.md` — update with Phase 5 changes: Zustand architecture, mouth-on-object, scene gallery, expression animation.
- `docs/plans/README.md` — mark Phase 5 in the roadmap table.

---

## Critical Files Touched

**New (7 files)**
- `frontend/src/lib/store.ts`
- `frontend/src/lib/store.test.ts`
- `frontend/src/components/SpeakingOverlay.tsx`
- `frontend/src/components/SpeakingOverlay.test.tsx`
- `frontend/src/components/SceneGallery.tsx`
- `frontend/src/components/SceneGallery.test.tsx`
- `docs/plans/2026-05-11-phase-5-visual-polish.md`

**Modified (7 files)**
- `frontend/src/pages/StudioPage.tsx` — primary refactor target
- `frontend/src/components/ChatPanel.tsx` — remove analyserNode from local state
- `frontend/src/components/PersonaMouth.tsx` — size prop, expression animation
- `frontend/src/pages/HomePage.tsx` — scene gallery shortcut
- `README.md`
- `docs/plans/README.md`

**Assets (new)**
- `frontend/public/scenes/` — 6 WebP scene images + `scenes.json` manifest

**Dependencies**
- `zustand` — add to `package.json`

---

## Verification

| Check | Command |
|---|---|
| Frontend tests | `npm test -- --run` (target: 105 existing + ~20 new pass) |
| TypeScript | `npx tsc --noEmit` |
| Build size | `npm run build` (budget: ≤ 240 KB / 75 KB gz, +20KB for scene thumbnails) |

**E2E manual flow:**
1. Open app → HomePage shows "Browse Scenes" button → click it → Studio opens with scene gallery.
2. Click a scene card → image loads → hotspots appear → click an object.
3. ChatPanel opens → PersonaMouth appears ON the image at the object's bbox (not just in sidebar).
4. Send a message → mouth on image animates with audio. Eyes blink naturally. Blink rate increases while speaking.
5. End chat → mouth disappears from image. Summary card shows.
6. Refresh page → Zustand store reinitializes cleanly (no stale state).
7. Upload own image → still works end-to-end (regression check).
