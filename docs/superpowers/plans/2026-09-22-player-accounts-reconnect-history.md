# 玩家账户、续接与历史记录 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 游客可直接加入，账户可自动登录并找回原座位；掉线不丢身份；账户跨局查看仅本人的角色、推测事件和结算。

**Architecture:** 当前局仍由 `GameManager` 和 JSON 存档管理，新增 `game_id` 与可选的 `account_id`。SQLite 保存账户、哈希密码、设备会话、续接码和历史；玩家私有 HTTP/WebSocket 均从 Cookie 会话解析参与者，公开 ID 不再是凭证。Vue 入口从“读 localStorage ID”改为“查询服务端会话”。

**Tech Stack:** Python 3.12、FastAPI、SQLite（标准库 `sqlite3`）、Argon2id（`argon2-cffi`）、Vue 3、Vitest、Python `unittest`；HTTP 集成测试使用 Starlette 当前所需的 `httpx2`。

**Spec:** `docs/superpowers/specs/2026-09-22-player-accounts-reconnect-history-design.md`；玩家推测事件的界面与字段另见 `docs/superpowers/specs/2026-09-21-player-inference-grimoire-design.md`。

## Global Constraints

- 首轮仅为可信局域网 HTTP 测试；页面提示测试专用密码，不把明文 HTTP 暴露到公网。现有 HTTPS 隧道可继续使用。
- 公开参与者 ID、姓名、座位、房号都不是私有接口凭证；不把会话秘密放进 URL、投影或 `localStorage`。
- 说书人可看本局推测，但不能读账户跨局历史、重置账户密码或取得账户会话。
- 未经确认不删除 `backend/data/game.json`；不得让自动化测试写入真实存档或触碰正在运行的 `8000` 服务。
- 保留现有工作区未提交改动；实施前依 `superpowers:using-git-worktrees` 建隔离工作树，并在合并时逐文件处理冲突。
- `frontend/dist` 是已追踪的构建产物；隔离工作树中的构建仅用于验证。合并到包含用户现有未提交前端改动的工作区后，先核对源文件与产物差异，再从合并后的源代码重建，不直接用隔离工作树产物覆盖用户文件。
- 每个行为先写失败测试，见红后最小实现，再跑相关测试和完整套件；每个任务仅提交自己的文件。

## Review Focus

1. 同名不同人加入同局时，第二人必须得到新参与者且不能占原座位（Task 3、4 测试）。
2. 用户名大小写或 Unicode 规范化后重复时，注册须拒绝且不签发会话（Task 2 测试）。
3. Cookie 已过期、缺少 CSRF、跨站 Origin 或 WebSocket 冒用公开 ID 时，均不得读取私有数据（Task 3、4 测试）。
4. 同一续接码被两个设备并发兑换时，只能有一次成功（Task 5 测试）。
5. 归档写入失败或说书人重复触发重置时，不得丢当前局或产生重复历史（Task 6 测试）。

## File Map

- `backend/app/domain/player.py`、`backend/app/state.py`、`backend/app/save_codec.py`、`backend/app/game.py`：参与者账户关联与不可复用的局 ID；原座位仍属于 `SeatState`。
- `backend/app/infrastructure/identity_store.py`：SQLite 建表、账户、会话、续接码和归档的持久化接口；不存原文密码或会话秘密。
- `backend/app/application/identity.py`：密码校验、参与者解析、速率限制和身份绑定规则。
- `backend/app/api/identity.py`、`backend/app/api/dependencies.py`：注册、登录、游客入局、会话查询、找回、历史以及 Cookie/CSRF/Origin 验证。
- `backend/app/api/player.py`、`backend/app/api/chat.py`、`backend/app/api/websocket.py`、`backend/app/application/realtime.py`：所有旧私有入口和实时推送按已验证会话授权。
- `backend/app/api/storyteller.py`：说书人签发／撤销本局续接码、重置前归档。
- `frontend/src/services/api.js`、`frontend/src/services/session.js`、`frontend/src/services/navigation.js`、`frontend/src/App.vue`：Cookie 会话与离线重试；不再保存玩家 ID 作为凭证。
- `frontend/src/pages/JoinPage.vue`、新增账户／历史组件、说书人恢复码组件：游客、注册、登录、找回和历史 UI。
- 新增 `backend/tests/test_identity_*.py`、`frontend/tests/*identity*.test.js`：隔离数据目录的红绿测试；更新依赖旧 `player_id` 信任模型的现有测试。

---

### Task 1: 当前局与参与者有稳定、可迁移的非凭证标识

**Files:** `backend/app/game.py`、`backend/app/domain/player.py`、`backend/app/state.py`、`backend/app/save_codec.py`、`backend/tests/test_identity_save.py`。

**Interfaces:** `GameManager.game_id: str`；`Player.account_id: str | None`；`PlayerAccount.account_id: str | None`。旧存档缺字段时采用新 `game_id`、空 `account_id`，不改写磁盘直到正常保存。

- [ ] **Step 0 — 隔离环境：** 按 `superpowers:using-git-worktrees` 从当前提交建立工作树；在该工作树运行 `uv venv backend/.venv && uv pip install --python backend/.venv/bin/python -r backend/requirements.txt`。检查 `git status --short`，不得清理原工作区的修改。
- [ ] **Step 1 — 红：** 在临时 `SAVE_PATH` 的测试中写入如下断言，另断言无账户的旧 v2 存档可读。

```python
with TemporaryDirectory() as td, patch.object(game_module, "SAVE_PATH", Path(td) / "game.json"):
    game = GameManager()
    first = game.game_id
    player = game.add_player("甲")
    player.account_id = "account-1"
    game.save()
    restored = GameManager()
    self.assertEqual(restored.game_id, first)
    self.assertEqual(restored.players[player.id].account_id, "account-1")
```

- [ ] **Step 2 — 运行：** `cd backend && .venv/bin/python -m unittest tests.test_identity_save -v`；预期因缺少 `game_id` 或 `account_id` 失败。
- [ ] **Step 3 — 绿：** 用 `secrets.token_hex(16)` 生成新局 ID；`save_payload()` 写顶层 `game_id`，`_restore_autosave()` 读取；两个 dataclass 加 `account_id: str | None = None`；`encode_save` 自然序列化，`decode_save` 对旧账号字典补默认值。公开 `Player.public()` 不增加账户 ID。补重置后局 ID 变化、旧存档缺字段测试。

```python
self.game_id = secrets.token_hex(16)                # reset()
payload["game_id"] = self.game_id                  # save_payload()
self.game_id = d.get("game_id", self.game_id)      # _restore_autosave()
account = {**account, "account_id": account.get("account_id")}
state.players[player_id] = PlayerAccount(**account) # decode_save()
```
- [ ] **Step 4 — 验证：** 重跑本文件及 `tests.test_save_codec`，然后 `git diff --check`。
- [ ] **Step 5 — 提交：** `git add backend/app/game.py backend/app/domain/player.py backend/app/state.py backend/app/save_codec.py backend/tests/test_identity_save.py && git commit -m "feat: add stable game and account linkage"`。

### Task 2: SQLite 账户和设备会话，不依赖玩家公开 ID

**Files:** 新增 `backend/app/infrastructure/identity_store.py`、`backend/app/application/identity.py`、`backend/tests/test_identity_store.py`；修改 `backend/requirements.txt`、`.gitignore`；新增 `backend/requirements-dev.txt`（`httpx2`）。

**Interfaces:** `IdentityStore(path)`；`create_account(username, password) -> (account_id, recovery_code)`；`authenticate(username, password) -> account_id | None`；`issue_session(account_id=None, player_id=None, game_id=None) -> (token, csrf)`；`resolve_session(token) -> Session | None`；`revoke_session(token)`；`revoke_account_sessions(account_id)`。`Session` 含 `account_id`、`player_id`、`game_id`、`csrf`、`expires_at`。

- [ ] **Step 1 — 红：** 建临时 SQLite 的测试覆盖以下行为，并用两个独立 `IdentityStore` 实例证明重启可读。

```python
account_id, recovery = store.create_account("Alice", "test-only-password")
self.assertIsNone(store.authenticate("Ａｌｉｃｅ", "wrong"))
self.assertEqual(store.authenticate("alice", "test-only-password"), account_id)
token, csrf = store.issue_session(account_id=account_id)
self.assertNotIn(token, Path(db_path).read_bytes().decode("latin1"))
self.assertEqual(IdentityStore(db_path).resolve_session(token).account_id, account_id)
```

- [ ] **Step 2 — 运行：** `cd backend && .venv/bin/python -m unittest tests.test_identity_store -v`；预期 `IdentityStore` 不存在。
- [ ] **Step 3 — 绿：** 建 `accounts(username_key UNIQUE, password_hash, recovery_digest)`、`sessions(token_digest PRIMARY KEY, account_id, player_id, game_id, csrf, expires_at)`、`login_attempts`、`recovery_codes`、`archives` 表；用户名 `unicodedata.normalize("NFKC", name).casefold()` 后作唯一键。Argon2id 哈希密码；`secrets.token_urlsafe(32)` 生成会话，数据库只存 `sha256(token).hexdigest()`；错误密码返回 `None`，达到速率阈值返回统一限流错误。加入账号密码不落明文、大小写／Unicode 重复、过期与撤销测试。

```python
def username_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name.strip()).casefold()

def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

token = secrets.token_urlsafe(32)
csrf = secrets.token_urlsafe(32)
password_hash = PasswordHasher().hash(password)
```
- [ ] **Step 4 — 验证：** 在隔离环境运行 `uv pip install --python backend/.venv/bin/python -r backend/requirements.txt -r backend/requirements-dev.txt`，重跑测试与 `git diff --check`；不得对原仓库现有 `.venv` 或运行中进程改包。
- [ ] **Step 5 — 提交：** 仅暂存本任务列出的文件，提交 `feat: persist accounts and sessions`。

### Task 3: 加入、注册、登录和 Cookie/CSRF 会话接口

**Files:** 新增 `backend/app/api/identity.py`、`backend/tests/test_identity_api.py`；修改 `backend/app/api/dependencies.py`、`backend/app/api/player.py`、`backend/app/main.py`、`backend/app/application/runtime.py`、`backend/app/domain/lobby.py`。

**Interfaces:** `GET /api/session` 返回 `{account, player_id, csrf_token}`；`POST /api/join` 创建游客或复用已登录账户的本局参与者；`POST /api/account/register|login|logout|change-password|reset-password|logout-all`；`require_player(request) -> str` 和 `require_matching_player(player_id, request) -> str`。成功登录用 `Set-Cookie: botc_session=<token>; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000`；`Secure` 只在明确 HTTPS 配置下开启。`TestClient` 请求统一带 `Origin: http://testserver`，测试全程补丁覆盖 `SAVE_PATH` 与 `runtime.identity_store`。

- [ ] **Step 1 — 红：** `unittest`＋`TestClient` 用临时 `SAVE_PATH` 和 SQLite，给出两人隔离及账户重新登录找回的测试。

```python
client = TestClient(app, headers={"Origin": "http://testserver"})
alice = client.post("/api/join", json={"name": "甲", "room_code": room}).json()["player_id"]
other = TestClient(app, headers={"Origin": "http://testserver"})
self.assertEqual(other.get(f"/api/me/{alice}").status_code, 401)
self.assertEqual(client.get("/api/session").json()["player_id"], alice)
same_name = other.post("/api/join", json={"name": "甲", "room_code": room}).json()["player_id"]
self.assertNotEqual(same_name, alice)
```

- [ ] **Step 2 — 运行：** `cd backend && .venv/bin/python -m unittest tests.test_identity_api -v`；预期旧 `/api/me/{id}` 被无 Cookie 访问的断言失败。
- [ ] **Step 3 — 绿：** `runtime` 创建 `IdentityStore`；身份 API 对 Cookie 做摘要查找，注册时把当前游客原子绑定到账户，已有关联时返回 `409` 而不改座位。带会话的修改请求要求 `X-CSRF-Token` 与数据库记录相符，并校验 `Origin` 与请求 Host；无会话的加入／注册／登录也校验 Origin。`require_matching_player` 先解析会话，再比较 path/query ID；账户会话按 `account_id` 查本局参与者。所有响应使用通用登录错误，不回显密码或 token。

```python
def require_matching_player(player_id: str, request: Request) -> str:
    session = require_session(request)
    actual = resolve_participant(runtime.game, session)
    if actual != player_id:
        raise HTTPException(status_code=403, detail="无权访问该玩家")
    return actual

response.set_cookie("botc_session", token, httponly=True,
                    samesite="lax", secure=secure_cookie_config,
                    max_age=30 * 24 * 60 * 60, path="/")
```
- [ ] **Step 4 — 验证：** 测试无 Cookie、错误 Cookie、过期 Cookie、错误 CSRF、跨站 Origin、登录失败限流、用户名规范化重复、游客绑定与座位冲突；另测账户恢复码只用一次、改密码后旧密码无效、退出所有设备后旧 Cookie 无效。重跑本文件和 `tests.test_join_qr`。
- [ ] **Step 5 — 提交：** 仅暂存本任务列出的文件，提交 `feat: add guest and account sign-in API`。

### Task 4: 所有旧玩家接口和 WebSocket 不再信任公开 ID

**Files:** `backend/app/api/player.py`、`backend/app/api/chat.py`、`backend/app/api/websocket.py`、`backend/app/application/realtime.py`、`backend/app/application/projections.py`、`backend/tests/test_identity_authorization.py`、`backend/tests/test_api_contract_snapshot.py`。

**Interfaces:** 保留兼容路径中的 `player_id` 但 `Depends(require_matching_player)` 必须验证其等于会话解析结果；WebSocket `who` 仅允许说书人旧入口，玩家身份一律由 Cookie 解析。`Hub.connect(verified_player_id, ws)` 只接收已验证标识。

- [ ] **Step 1 — 红：** 两个客户端先各加入并入座，再尝试用甲的公开 ID 读取甲的私有视图、私聊、夜晚操作以及 `/ws?who=<甲ID>`。

```python
self.assertEqual(bob.get(f"/api/me/{alice_id}").status_code, 403)
self.assertEqual(bob.post(f"/api/player/{alice_id}/vote", headers=bob_csrf).status_code, 403)
with self.assertRaises(WebSocketDisconnect):
    with bob.websocket_connect(f"/ws?who={alice_id}") as ws:
        ws.receive_json()
```

- [ ] **Step 2 — 运行：** `cd backend && .venv/bin/python -m unittest tests.test_identity_authorization -v`；预期旧接口泄露导致断言失败。
- [ ] **Step 3 — 绿：** 对 `player.py` 和 `chat.py` 每条玩家私有路由挂 `require_matching_player`，包括 GET 与写操作；WS 在 `accept()` 前验证 Cookie/Origin 和目标参与者，失败关闭 `4001/4003`；`Hub` 仅按已验证 ID 分组。公开投影若仍带 ID，确保该 ID 只用于展示而非权限；更新 OpenAPI 快照哈希并人工审查新增契约。

```python
@router.get("/api/me/{player_id}")
def me(player_id: str, _: str = Depends(require_matching_player)) -> dict[str, Any]:
    return game.player_view(player_id)

actual = resolve_participant(game, require_ws_session(ws))
if actual is None or (who and who != actual):
    await ws.close(code=4003, reason="身份无效")
    return
await hub.connect(actual, ws)
```
- [ ] **Step 4 — 验证：** 两人隔离、说书人旧通道、旅行者操作、被移除玩家连接关闭；运行 `tests.test_player_websocket_session`、`tests.test_api_contract_snapshot` 与完整后端套件。
- [ ] **Step 5 — 提交：** 仅暂存本任务列出的文件，提交 `fix: authorize all player API and websocket access`。

### Task 5: 说书人签发一次性本局续接码

**Files:** `backend/app/infrastructure/identity_store.py`、`backend/app/api/identity.py`、`backend/app/api/storyteller.py`、`backend/tests/test_identity_recovery.py`；`frontend/src/components/storyteller/ContextPanel.vue`、新增 `frontend/src/components/storyteller/RecoveryPanel.vue`、`frontend/src/services/storyteller.js`、`frontend/tests/storyteller-recovery.test.js`。

**Interfaces:** `store.issue_participant_recovery(game_id, player_id, now) -> str`；`store.redeem_participant_recovery(game_id, code, now) -> player_id | None`；`POST /api/st/players/{player_id}/recovery-code` 需说书人密码，返回一次性明文码；`POST /api/recover-participant` 接受 `{room_code, code}`，在同一 SQLite 事务内消耗码并发新会话；`POST /api/st/players/{player_id}/revoke-guest-sessions` 仅撤销本局游客／续接会话，不撤销账户会话。

- [ ] **Step 1 — 红：** 测试码只显示一次、10 分钟过期、错误房号拒绝、同码并发只能成功一次；Vue 测试点击说书人“找回身份”后显示原玩家和续接码，不出现账户密码。

```python
code = store.issue_participant_recovery(game.game_id, alice_id, now=1000)
self.assertEqual(store.redeem_participant_recovery(game.game_id, code, now=1001), alice_id)
self.assertIsNone(store.redeem_participant_recovery(game.game_id, code, now=1002))
expired = store.issue_participant_recovery(game.game_id, alice_id, now=1000)
self.assertIsNone(store.redeem_participant_recovery(game.game_id, expired, now=1601))
```

- [ ] **Step 2 — 运行：** 后端 `tests.test_identity_recovery`、前端 `npm test -- storyteller-recovery.test.js`；预期续接接口／组件不存在。
- [ ] **Step 3 — 绿：** SQLite `BEGIN IMMEDIATE` 原子标记已用码；用 `sha256` 摘要查码，保存局 ID、参与者 ID、到期时间；兑换只发参与者会话，不赋予账户历史权限。说书人组件在玩家名单中选择目标、生成码、复制；避免把明文码放进广播投影或日志。

```sql
BEGIN IMMEDIATE;
UPDATE recovery_codes SET consumed_at = :now
WHERE code_digest = :digest AND game_id = :game_id
  AND consumed_at IS NULL AND expires_at > :now;
-- 只有 rowcount = 1 才读取该行 participant_id 并签发会话，否则回滚/拒绝。
COMMIT;
```
- [ ] **Step 4 — 验证：** 重跑单测，补同码并发兑换、连续错误码限流，并人工核对目标座位、角色与夜晚状态未变化。
- [ ] **Step 5 — 提交：** 仅暂存本任务列出的文件，提交 `feat: add storyteller-approved participant recovery`。

### Task 6: 账户历史在重置前幂等归档

**Files:** `backend/app/infrastructure/identity_store.py`、`backend/app/application/history.py`（新增）、`backend/app/api/identity.py`、`backend/app/api/storyteller.py`、`backend/app/domain/lobby.py`、`backend/tests/test_account_history.py`。

**Interfaces:** `archive_game(game, store) -> None`；`store.upsert_archive(game_id, account_id, record)`；`GET /api/account/history` 只读当前账户的归档；活跃局由 `/api/session` 的本人视图读取。记录为 `{game_id, script_id, seat, roles: [{id, name}], guesses, winner, finished}`，`guesses` 只取本人推测事件，不能从聊天或他人推测补全。推测模块尚未上线时返回空数组；上线后沿已有推测事件接口接入，不在本任务另造推测编辑器。

- [ ] **Step 1 — 红：** 临时 JSON/SQLite 中先建立账户参与者，写入角色与结算，调用重置两次；断言恰有一份历史且私聊文本不出现在 JSON 返回。

```python
archive_game(game, store)
archive_game(game, store)
records = store.list_archives(account_id)
self.assertEqual(len(records), 1)
self.assertEqual(records[0]["game_id"], old_game_id)
self.assertNotIn("messages", records[0])
```

- [ ] **Step 2 — 运行：** `cd backend && .venv/bin/python -m unittest tests.test_account_history -v`；预期 `archive_game` 缺失。
- [ ] **Step 3 — 绿：** 在说书人重置和“已开始／已结算局的配置切换”前先归档；SQLite 以 `(game_id, account_id)` 唯一键幂等写入，失败抛错并阻止清空局；大厅内纯配置调整不归档。新局生成新 ID，旧参与者会话失效，账户会话仍可查历史。角色变化只有现有事件能证明才附时间；未结算标记未完成，不猜胜负。

```python
def archive_game(game: GameManager, store: IdentityStore) -> None:
    for player in game.players.values():
        if player.account_id is None:
            continue
        record = project_own_history(game, player.id)
        store.upsert_archive(game.game_id, player.account_id, record)
```
- [ ] **Step 4 — 验证：** 归档失败、重复重置、未结束配置切换、进程重启、两账户历史隔离测试及完整后端套件。
- [ ] **Step 5 — 提交：** 仅暂存本任务列出的文件，提交 `feat: archive private account game history`。

### Task 7: Vue 自动登录与断网重试，不再保存凭证到 localStorage

**Files:** `frontend/src/App.vue`、`frontend/src/pages/JoinPage.vue`、`frontend/src/services/api.js`、`frontend/src/services/session.js`、`frontend/src/services/navigation.js`、`frontend/src/composables/usePlayerView.js`、`frontend/src/services/websocket.js`；新增 `frontend/src/pages/AccountPage.vue`、`frontend/tests/account-entry.test.js`；更新 `frontend/tests/{session,join-page,app-routing,player-routing,player-view,player-service}.test.js`。

**Interfaces:** `api('/api/session')` 获取 `{account, player_id, csrf_token}`；内存保存 CSRF token，写请求自动带 `X-CSRF-Token`，浏览器自动带 HttpOnly Cookie；`openSocket` 对玩家不再拼 `who=<player_id>`。入口状态为 `loading | offline | join | player | account`；只有明确 `401` 清理当前身份。

- [ ] **Step 0 — 前端依赖：** 在隔离工作树运行 `cd frontend && npm ci`，不重写锁文件。
- [ ] **Step 1 — 红：** Vue 测试让 `/api/session` 抛网络错误、再成功，断言一直显示可重试状态而不丢身份；另断言只有 `401` 回加入页。

```javascript
api.mockRejectedValueOnce(new TypeError('Failed to fetch'))
const wrapper = mount(App)
await flushPromises()
expect(wrapper.find('[data-retry-session]').exists()).toBe(true)
expect(localStorage.getItem('botc_player_id')).toBeNull()
```

- [ ] **Step 2 — 运行：** `cd frontend && npm test -- account-entry.test.js`；预期旧入口把网络错误当成 join，测试失败。
- [ ] **Step 3 — 绿：** 用 `/api/session` 代替 `getPlayerId()` 决定玩家页；网络错误进入 `offline` 并保留 Cookie，不调用注销；前端 `api` 写请求从内存 CSRF 状态加请求头；游客加入返回后直接刷新会话；注册／登录页显示 HTTP 测试密码提示；页面既可注册新账户也可让游客绑定。玩家 WebSocket 仅依赖 Cookie。更新旧测试，不删除说书人密码存储逻辑。

```javascript
try {
  const session = await api('/api/session')
  setCsrfToken(session.csrf_token)
  activePlayerId.value = session.player_id
  page.value = session.player_id ? 'player' : 'join'
} catch (error) {
  page.value = error.status === 401 ? 'join' : 'offline'
}
```
- [ ] **Step 4 — 验证：** 跑入口、会话、加入、WebSocket 等相关 Vitest，确认断网刷新、同来源自动登录、401、注册／登录冲突分支。
- [ ] **Step 5 — 提交：** 仅暂存本任务列出的文件，提交 `feat: add optional account entry and resilient session routing`。

### Task 8: 玩家找回与历史页面、完整回归

**Files:** 新增 `frontend/src/pages/AccountHistoryPage.vue`、`frontend/src/components/player/RecoverIdentity.vue`、`frontend/tests/account-history.test.js`、`frontend/tests/player-recovery.test.js`；修改 `frontend/src/App.vue`、`frontend/src/pages/PlayerPage.vue`、`frontend/src/components/player/PlayerShell.vue`、`frontend/src/pages/JoinPage.vue`、`frontend/src/styles/player.css`、`README.md`、`backend/tests/test_api_contract_snapshot.py`。

**Interfaces:** 历史页调用 `GET /api/account/history`；找回页调用 `POST /api/recover-participant`；注册后一次性展示账户恢复码，找回本局只展示说书人续接码输入。历史卡只显示本人角色、本人推测和胜负／未完成状态。

- [ ] **Step 1 — 红：** 测试账户只看到自己的历史、游客没有跨局历史入口、找回码成功后重新打开原座位；测试当前局仍可从返回按钮进入原游戏。

```javascript
api.mockResolvedValueOnce([{ game_id: 'g1', roles: [{ id: 'chef', name: '厨师' }], guesses: [], winner: 'good' }])
const wrapper = mount(AccountHistoryPage)
await flushPromises()
expect(wrapper.text()).toContain('厨师')
expect(wrapper.text()).not.toContain('私聊')
```

- [ ] **Step 2 — 运行：** `cd frontend && npm test -- account-history.test.js player-recovery.test.js`；预期组件不存在。
- [ ] **Step 3 — 绿：** 加“我的历史”和“找回本局身份”入口；成功续接后重新查询 `/api/session` 而非把码存本地；账户恢复码只在注册完成页展示一次，切页后不再显示。README 写明 `backend/data/accounts.sqlite3` 和 `game.json` 必须一起备份、HTTP 仅测试、HTTPS 升级只需部署／Cookie 配置。

```javascript
async function recoverParticipant(roomCode, code) {
  await api('/api/recover-participant', {
    method: 'POST', body: JSON.stringify({ room_code: roomCode, code }),
  })
  return api('/api/session')
}
```
- [ ] **Step 4 — 验证：** 在隔离工作树运行 `cd backend && .venv/bin/python -m unittest discover -s tests -v`、`cd frontend && npm test`、`cd frontend && npm run build`；检查所有失败，特别是现有 API 快照、夜晚流程、私聊与前端路由；用 `git diff --check` 验证。只在隔离的临时服务器做手机宽度手动验证，不碰 `8000` 真实服务／存档。
- [ ] **Step 5 — 提交：** 仅暂存本任务列出的文件，提交 `feat: show player recovery and private account history`；记录测试数量、未解决失败和部署所需动作。

## Execution Order and Exit Criteria

按 Task 1→8 逐项红绿测试和提交。先完成身份边界再打开私有历史接口；若已有玩家推理模块，则 Task 6 直接消费其事件，否则历史中的推测列表保持空，后续按已批准的推理魔典规格接入。此计划不把完整推测编辑器伪装成已完成。最终交付须能用两个浏览器证明：甲掉线后回原座位，乙凭公开 ID 无法读甲，账户跨局仅看到本人的历史。上线前仍需另做 HTTPS 部署，HTTP 版只用于用户指定的小规模测试。
