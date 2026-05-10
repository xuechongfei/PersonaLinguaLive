# PersonaLinguaLive V1 MVP 实现计划路线图

> 创建日期:2026-05-09
> 对应 PRD:`docs/prd/2026-05-09-personalingualive-prd.md` v0.1
> 对应设计文档:`docs/design/2026-05-09-personalingualive-design.md` v0.1

## 为什么分多个 Plan

V1 MVP(M1-M10)横跨前端、后端、AI 编排、数据持久化等多个独立子系统。把它写成单一计划会有 200+ 个步骤、几千行,不利于执行与审阅。
按 `superpowers:writing-plans` 的 scope check 建议,我们把 V1 切成 **5 个纵向 Phase,每个 Phase 完成后软件都能跑、能展示、能测试**(增量交付而非垂直分层先做完)。

## 5 个 Phase 总览

| Phase | 主题 | 涉及模块 | 完成后能演示什么 | 状态 |
|-------|------|----------|------------------|------|
| 1 | 项目地基 | — | `docker run` 起服务,前端能打开,/healthz 通,CI 绿 | ✅ 已完成:`2026-05-09-phase-1-foundation.md` |
| 2 | 视觉链路 | M1 + M2 + M3 | 上传图片 → 安全检查 → 显示可点击热区 | ✅ 已完成:`2026-05-09-phase-2-vision-pipeline.md` |
| 3 | 对话引擎 | M4 + M5 + M6 + M7 + M8 + M9 + M10 | 点击热区 → 生成人设 → WebSocket 语音对话 → 学习卡片 → 总结卡 | ✅ 已完成:`2026-05-09-phase-3-conversation-engine.md` |

## 执行原则(所有 Phase 通用)

1. **TDD 优先**:每个功能先红(写失败测试)→ 绿(最小实现)→ commit。
2. **小步频繁提交**:平均每 15-30 分钟一次 commit,commit message 用 conventional commits(`feat: ...`、`test: ...`)。
3. **完成 = 测试通过 + 手动验收 + Push**:Phase 视为完成,必须满足 PRD 第 8 节对应的验收项。
4. **设计文档是事实来源**:任何"实现觉得设计不对"的情况,先改设计文档(升 v0.x),再写代码。

## 开始执行

进入对应 Plan 文件,按 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 子技能逐任务执行。
