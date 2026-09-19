# BOTC Grimoire 模块化与 Vue/Vite 迁移设计

## 目标

在不改变现有功能、REST/WebSocket 契约和存档格式的前提下，解决后端业务集中在 `game.py`/`main.py`、前端业务集中在 `app.js`/`styles.css` 的维护问题。

迁移完成后：

- FastAPI 仍是唯一运行时服务和静态文件入口。
- 前端使用 Vue 3 + Vite 开发，生产环境只部署 Vite 构建产物。
- 玩家继续通过同一局域网地址访问，无须安装应用或连接互联网。
- 当前 Python 冒烟测试继续作为跨端回归验收。
- 本阶段不引入数据库、多房间、微服务或新的业务功能。

## 约束

- 保留现有 URL、请求体、响应体和 WebSocket 消息结构。
- 保留 `backend/data/game.json` 的现有存档兼容性。
- 保留单桌、单进程、局域网优先的运行模式。
- 迁移期间旧前端必须保持可回退，不能同时重写前后端核心行为。
- 每个迁移阶段结束时都必须能够启动并通过对应验证。

## 总体架构

```text
浏览器
  ├─ Vue 页面与组件
  ├─ REST 客户端
  └─ WebSocket 客户端
           │
           ▼
FastAPI API Routers
           │
           ▼
Application Services ──→ Domain Game State
           │                    │
           ├─ Persistence       └─ View Projections
           └─ Realtime Hub
```

FastAPI、游戏领域对象和前端保持在一个仓库、一个部署单元内。模块边界用于降低维护成本，不引入进程间通信。

## 前端设计

### 工具与运行方式

- Vue 3 使用 Composition API 和单文件组件。
- Vite 负责开发服务器、依赖处理和生产构建。
- 第一阶段使用 JavaScript，避免在迁移 UI 的同时进行全量 TypeScript 改造。
- 前端构建输出到 `frontend/dist/`，FastAPI 生产环境托管该目录。
- 开发模式下 Vite 将 `/api` 和 `/ws` 代理到 FastAPI。

### 目录结构

```text
frontend/
  package.json
  vite.config.js
  index.html
  src/
    main.js
    App.vue
    router.js
    services/
      api.js
      websocket.js
      session.js
    pages/
      JoinPage.vue
      PlayerPage.vue
      StorytellerPage.vue
    components/
      SeatCircle.vue
      RoleCard.vue
      PhaseHeader.vue
      NominationPanel.vue
      NightPanel.vue
      ChatPanel.vue
      TravelerPanel.vue
      ReviewPanel.vue
    composables/
      useSocketView.js
      useConfirmAction.js
    styles/
      tokens.css
      base.css
      components.css
      player.css
      storyteller.css
  dist/
  legacy/
    app.js
    styles.css
```

`legacy/` 只在迁移期间保留。全部页面完成并通过验证后删除。

### 页面职责

- `JoinPage`：房间号、名字、加入请求和本地会话保存。
- `PlayerPage`：玩家公开信息、私密角色卡、提名投票、夜间行动、私聊和结算。
- `StorytellerPage`：配置、配板、魔典、夜晚流程、提名、旅行者、私聊监管和复盘。
- 组件只通过 props/事件与页面通信，不直接创建 WebSocket。
- 页面拥有当前服务器视图；服务器仍是游戏状态的唯一真相来源。

### 状态与数据流

```text
WebSocket 消息
  → 页面 currentView
  → Vue 响应式渲染

用户操作
  → services/api.js
  → FastAPI 命令接口
  → WebSocket 广播新视图
  → 页面更新
```

REST 响应不作为长期本地状态源，避免 REST 返回值与随后到达的 WebSocket 视图互相覆盖。页面级临时状态（选中的座位、未发送聊天草稿、确认按钮状态）保留在对应组件或页面中。

### 错误处理

- `api.js` 统一解析 FastAPI 错误，包括 422 校验错误。
- WebSocket 对普通断线指数退避重连；身份失效和密码错误停止重连并返回入口页。
- 页面提供连接状态，不因一次断线清空当前视图。
- 单个组件错误不能关闭 WebSocket 或清除本地身份。

## 后端设计

### 目录结构

```text
backend/app/
  main.py
  api/
    dependencies.py
    player.py
    storyteller.py
    chat.py
    websocket.py
  domain/
    game.py
    lobby.py
    night.py
    nomination.py
    chat.py
    review.py
  application/
    services.py
    projections.py
  infrastructure/
    persistence.py
  scripts/
```

### 职责边界

- `api/`：解析 HTTP/WebSocket 输入、身份依赖、状态码转换。
- `domain/`：游戏规则和状态转换，不依赖 FastAPI。
- `application/services.py`：编排一次完整命令，包括规则调用、存档和广播请求。
- `application/projections.py`：生成玩家视图和说书人视图，集中处理信息保密。
- `infrastructure/persistence.py`：现有 JSON 快照的读写和兼容恢复。
- `main.py`：创建应用、注册路由、挂载前端静态目录，不承载业务接口实现。

### 渐进拆分原则

本次不直接重写 `GameManager`。先通过移动职责形成边界，再逐域拆规则：

1. 拆 API Router，仍调用现有 `GameManager`。
2. 抽出持久化读写。
3. 抽出玩家/说书人视图投影。
4. 依次迁移私聊、提名投票、夜晚规则。
5. 最后缩减 `GameManager` 为聚合状态和少量跨域协调。

每一步保持公共方法或提供兼容转发，避免同时改动所有调用方。

### 命令生命周期

所有状态写操作遵循统一顺序：

```text
认证与输入校验
  → 领域规则校验
  → 内存状态更新
  → 事件记录
  → 原子存档
  → WebSocket 广播
```

领域校验失败映射为 400；身份失败映射为 401/403；未知资源映射为 404。失败操作不得写存档或广播半完成状态。

## 迁移阶段

### 阶段一：Vue/Vite 外壳

- 添加 Vite、Vue 和构建配置。
- 建立 API、WebSocket、会话服务。
- FastAPI 支持托管 `frontend/dist/`，开发模式保留旧前端回退。
- 不迁移复杂业务页面。

### 阶段二：加入页与玩家页

- 先迁移加入页并验证入房、刷新恢复和失效清理。
- 再按角色卡、座位圆盘、提名投票、夜间行动、私聊、结算顺序拆玩家组件。
- 玩家页完成后进行移动端人工检查。

### 阶段三：说书人页

- 先迁移页面框架和座位圆盘。
- 再迁移配置/配板、夜晚、投票、旅行者、私聊与复盘。
- 每个面板作为独立组件，避免形成新的巨型 `StorytellerPage.vue`。

### 阶段四：后端路由与基础设施

- 将 `main.py` 中接口分组迁入 Router。
- 抽出 Hub、持久化和视图投影。
- 保持接口契约完全不变。

### 阶段五：领域规则拆分

- 按私聊、提名、夜晚、复盘的顺序迁移。
- 每迁移一个领域，先补领域单元测试，再移动实现。
- 删除旧兼容转发前运行完整回归。

### 阶段六：清理

- 删除 `legacy/` 和兼容分支。
- 更新 README 中的开发、构建、生产启动说明。
- 确认生产环境只需要 Python 和已构建的 `dist/`。

## 测试与验收

每个阶段至少执行：

- 前端生产构建成功。
- Python 模块编译成功。
- 现有 `backend/smoke_test.py` 完整通过。
- 加入页、玩家页和说书人页在手机宽度下人工检查。

新增测试重点：

- API 错误解析和 WebSocket 重连单元测试。
- 关键 Vue 组件的交互测试。
- 玩家视图不能泄露其他玩家的私密角色信息。
- 后端拆分前后的 API JSON 契约快照对比。
- 存档加载和重启恢复回归。

最终验收标准：

- `main.py` 只保留应用装配和静态文件挂载。
- 前端不存在单个承担整个玩家页或说书人页渲染的大型函数。
- 旧 REST/WebSocket 客户端仍能使用原接口。
- 完整冒烟测试通过，主要流程人工验证通过。

## 回退策略

- 每个阶段单独提交，不混合功能开发。
- Vue 页面未完成前保留 `legacy/`，通过环境变量或静态入口切换。
- 后端拆分时保留原公共调用入口，阶段验证完成后再删除转发。
- 任一阶段出现回归时回退该阶段提交，不影响迁移前基线 `6cc6479`。

