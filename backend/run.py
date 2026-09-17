"""启动说书人服务器。

用法:在 backend/ 目录下执行 `python run.py`
(Windows 首次运行会弹防火墙提示,勾选「专用网络」并允许,玩家手机才能连上)
"""

import uvicorn

from app.net import get_lan_ip

PORT = 8000


def main() -> None:
    lan_ip = get_lan_ip()
    print("=" * 48)
    print("  BOTC Grimoire · 血染钟楼说书人工具")
    print("=" * 48)
    print(f"  本机(说书人)访问: http://localhost:{PORT}/#/storyteller")
    print(f"  玩家加入地址:       http://{lan_ip}:{PORT}/")
    print("  (玩家手机连同一 WiFi,扫描说书人界面上的二维码)")
    print("=" * 48)
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
