"""MCP 服务的 ASGI 入口。

启动方式（与 WSGI 主服务同镜像、独立进程）：

    uvicorn project.apps.mcp.asgi:app --host 0.0.0.0 --port 8001
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.settings')

import django  # noqa: E402

django.setup()

from .server import build_asgi_app  # noqa: E402  必须在 django.setup() 之后导入

app = build_asgi_app()
