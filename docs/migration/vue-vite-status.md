# Vue/Vite 迁移状态

- [x] Vue/Vite production shell
- [x] Shared REST and session services
- [x] Join page migrated
- [x] Storyteller desktop shell preview
- [x] Storyteller lobby setup and role assignment
- [x] Storyteller night workflow
- [ ] Player page migrated
- [ ] Storyteller day/review tools migrated
- [ ] Legacy frontend removed
- [ ] Backend routers and domains modularized

`/legacy/` 是迁移期间的临时同源入口，用于继续提供玩家页及尚未迁移的白天/复盘工具。
各页面完成 Vue 迁移并通过完整回归验证后，才能删除该入口及 `frontend/legacy/`。

## 说书人 Vue 正式入口

- `/#/storyteller`：Vue 说书人魔典正式入口。
- `/#/storyteller-preview`：自动重定向到正式入口。
- 已迁移的大厅操作：剧本和人数配置、随机发牌二次确认、逐座手动发身份、恶魔伪装、
  酒鬼/疯子认知覆盖、传奇角色、哨兵调整和人未齐强制开局。
- 已迁移的夜晚操作：动态座位夜序、秘密死亡裁定、结构化信息发送与真假标记、
  麻脸巫婆角色变化、限时异常状态、依赖撤销及天亮公开死亡。
- 白天、提名投票、旅行者、聊天及结束复盘暂时通过“旧版白天与复盘工具”进入。
- 旧版夜晚操作已改为只读跳转页，不能再推进或修改夜晚状态。

## 数据与恢复

- 当前存档架构为 schema v2，角色归属于座位；玩家帐号只负责领取座位。
- 旧存档在加载时自动迁移到 v2，原有未入座角色也会保留。
- 夜晚写接口为 `/api/night/step`、`select`、`outcome`、`information`、`effect`、
  `pit-hag` 和 `undo`，WebSocket 投影中的 `night_workflow` 是界面权威状态。
- 官方三版角色名称和夜序中文来自规范化 `zh-CN` locale；英文角色 ID 保持稳定，方便导入 JSON 剧本。
- 恢复时先停止服务，备份 `backend/data/game.json`；可替换为迁移前备份后重启，加载器会再次执行兼容迁移。
- 第 12 阶段自动化回归按用户要求跳过，本轮由说书人端手动验收。
