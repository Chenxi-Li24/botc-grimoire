# Vue/Vite 迁移状态

- [x] Vue/Vite production shell
- [x] Shared REST and session services
- [x] Join page migrated
- [x] Storyteller desktop shell preview
- [ ] Player page migrated
- [ ] Storyteller page migrated
- [ ] Legacy frontend removed
- [ ] Backend routers and domains modularized

`/legacy/` 是迁移期间的临时同源入口，用于继续提供尚未迁移的玩家页和说书人页。
各页面完成 Vue 迁移并通过完整回归验证后，才能删除该入口及 `frontend/legacy/`。

## 说书人 Vue 预览

- `/#/storyteller`：仍进入功能完整的旧版说书人控制台。
- `/#/storyteller-preview`：Vue 只读迁移预览，包含桌面三栏外壳、实时环形魔典、
  玩家加入二维码和选中玩家详情。
- 配板、发身份、阶段推进等写操作继续通过预览中的“打开完整控制台”完成。

预览用于逐步验证新布局，不会静默取代尚未迁移的旧功能。

迁移前的功能基线是提交 `6cc6479`。本迁移只改变代码组织、开发工具和前端入口，
不改变 REST/WebSocket 契约、游戏规则或 JSON 存档格式。
