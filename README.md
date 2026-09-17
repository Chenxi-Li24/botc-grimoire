# BOTC Grimoire 血染钟楼说书人工具

局域网优先的多设备说书人工具:说书人电脑运行本地服务器,玩家手机扫码即可获得私密角色卡。无需域名、无需公网,手机热点 / 路由器 / ESP32 盒子均可兼容。

## 架构

- **后端** `backend/`:Python + FastAPI + WebSocket(游戏状态、实时推送、二维码生成)
- **前端** `frontend/`:纯 HTML/CSS/JS,**零构建零依赖**(加入页 / 玩家角色卡 / 说书人魔典),由 FastAPI 直接托管
- 单端口部署:所有设备访问同一个局域网地址

选择无构建前端的原因:开发机上 443 端口(HTTPS)网络不通,npm 依赖无法安装。纯 JS 版功能与 React 版一致,API 契约不变,网络恢复后想换回 React 随时可迁。

## 快速开始

```bash
# 1. 后端依赖
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
#    (网络不通时:no_proxy='*' NO_PROXY='*' ... -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com)

# 2. 启动(无需任何构建)
cd backend
.venv\Scripts\python run.py
```

- **说书人**:浏览器打开 `http://localhost:8000/#/storyteller`(默认密码 `grimoire`,可用环境变量 `STORYTELLER_PASSWORD` 修改)
- **玩家**:手机连同一 WiFi,扫描说书人界面上的二维码加入
- Windows 首次运行会弹防火墙提示,勾选「专用网络」并**允许**,否则手机连不上

## v1 已实现

- 玩家扫码/输入名字加入,身份存 localStorage,刷新不掉;断线自动重连
- 说书人按暗流涌动官方配置表(5~15 人)随机分配角色,支持男爵 +2 外来者规则
- 玩家手机实时收到私密角色卡(暗流涌动 22 个角色全收录)
- 存活/死亡标记、移除玩家、重置本局,WebSocket 实时同步
- 冒烟测试 `backend/smoke_test.py` 覆盖 REST + WS 全链路(先启动 run.py 再运行)

## 路线图

- [x] v1 最小闭环:扫码加入 → 分配角色 → 私密角色卡 → 存活标记
- [ ] v1 完整:夜晚流程助手、中毒/醉酒/疯狂状态标记、提名投票处决、存档
- [ ] v2 硬件:ESP32-S3 便携热点盒子(≤9 人),GL.iNet 路由 + ESP32 屏幕(10~20 人)
- [ ] v3 公网:云服务器 + 4G,跨场地大局

## 已知限制

- 角色文案为初版速写,校对只改 `backend/app/roles.py`
- 目前仅收录暗流涌动(Trouble Brewing),黯月传奇 / 教派紫月待补
- 状态存内存,服务器重启即重置(存档在路线图中)
- 醉鬼伪装(玩家看到错误角色)未实现,分配后说书人需口头告知
