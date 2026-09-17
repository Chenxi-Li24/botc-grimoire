"""局域网地址探测。"""

import socket


def get_lan_ip() -> str:
    """UDP connect 技巧:不真正发包,只让系统选出默认出口网卡。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
