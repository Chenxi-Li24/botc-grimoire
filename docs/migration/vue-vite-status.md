# Vue/Vite 迁移状态

- [x] Vue/Vite production shell
- [x] Shared REST and session services
- [x] Join page migrated
- [x] Storyteller desktop shell preview
- [x] Storyteller lobby setup and role assignment
- [x] Storyteller night workflow
- [x] Player page migrated
- [x] Storyteller daytime nomination/voting workflow migrated
- [x] Storyteller traveler/chat/end-game/review administration migrated
- [x] Legacy frontend removed
- [x] Backend routers and domains modularized

生产只托管 `frontend/dist/`。`main.py` 装配 API Router、WebSocket 和静态文件；
`domain/` 承担规则，`application/projections.py` 生成隔离的玩家/说书人视图，
`infrastructure/persistence.py` 原子读写 JSON 存档。

## 说书人 Vue 正式入口

- `/#/storyteller`：Vue 说书人魔典正式入口。
- `/#/storyteller-preview`：自动重定向到正式入口。
- 已迁移的大厅操作：剧本和人数配置、随机发牌二次确认、逐座手动发身份、恶魔伪装、
  酒鬼/疯子认知覆盖、传奇角色、哨兵调整和人未齐强制开局。
- 已迁移的夜晚操作：动态座位夜序、秘密死亡裁定、结构化信息发送与真假标记、
  麻脸巫婆角色变化、限时异常状态、依赖撤销及天亮公开死亡。
- 已迁移的白天操作：公聊/提名阶段切换、混合座位与旅行者提名、实时举手与死亡票、
  结票、处决领先/平票提示、提名历史和结束白天。
- 已迁移旅行者加入/阵营/流放管理、说书人私聊监管、座位与房间存档管理、胜负宣布和复盘标注。
- 页头可打开相应原生管理面板；夜间座位管理单独开启，不干扰夜晚目标点选。

## 玩家 Vue 正式入口

- `/`：加入房间、选座和旅行者加入均在 Vue 中完成，已有身份会直接恢复玩家页。
- 已迁移大厅、身份卡、公开座位盘、统一夜间行动、提名投票、死票确认、私聊、结算与复盘。
- 玩家夜间操作写入与说书人一致的 `night_workflow`，不会再通过旧版 `kill` / `choice` 状态推进。
- 身份失效时会清理本地会话并返回加入页。

## 数据与恢复

- 当前存档架构为 schema v2，角色归属于座位；玩家帐号只负责领取座位。
- 旧存档在加载时自动迁移到 v2，原有未入座角色也会保留。
- 夜晚写接口为 `/api/night/step`、`select`、`outcome`、`information`、`effect`、
  `pit-hag` 和 `undo`，WebSocket 投影中的 `night_workflow` 是界面权威状态。
- 官方三版角色名称和夜序中文来自规范化 `zh-CN` locale；英文角色 ID 保持稳定，方便导入 JSON 剧本。
- 恢复时先停止服务，备份 `backend/data/game.json`；可替换为迁移前备份后重启，加载器会再次执行兼容迁移。
- 迁移完成后运行前端单测/构建、后端单测和隔离端口的完整跨端冒烟；
  现场 8000 服务及真实存档不参与自动化验证。
