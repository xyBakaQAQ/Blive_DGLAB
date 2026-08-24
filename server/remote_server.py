import asyncio
import json
import logging
import os
import time
import yaml
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("remote_server")

# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "remote_server.yaml")
if not os.path.exists(CONFIG_PATH):
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "remote_server.yaml.example")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

SERVER_CONFIG = config.get("server", {})
LIMITS = config.get("limits", {})

HOST = SERVER_CONFIG.get("host", "0.0.0.0")
PORT = SERVER_CONFIG.get("port", 9878)
TOKEN = str(SERVER_CONFIG.get("token", "")).strip()

MAX_STRENGTH = int(LIMITS.get("max_strength", 20))
MAX_DURATION = float(LIMITS.get("max_duration", 60))
COOLDOWN = float(LIMITS.get("cooldown", 2))

# 全局状态
modules = set()  # 连接的 remote_module 客户端 WebSocket
last_command_time = 0

def verify_auth(request):
    """
    针对已部署客户端的强兼容性鉴权 (自动剔除引号，并优先从 Query 参数获取)
    """
    # 1. 优先尝试从 Query 参数获取
    supplied_token = request.query.get("token", "").strip()

    # 2. 如果 Query 没有，再尝试从 Header 提取
    if not supplied_token:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            supplied_token = auth_header[7:].strip()
        else:
            supplied_token = auth_header

    # 3. 关键修复：去除两端的引号
    supplied_token = supplied_token.strip("'").strip('"')

    # 4. 记录日志
    logger.info(f"鉴权排查 -> 收到 Token: '{supplied_token}' | 期望: '{TOKEN}'")

    # 5. 特殊处理：如果配置的 token 为 none，则完全不鉴权
    if TOKEN.lower() == "none":
        return True

    # 6. 比对
    return supplied_token == TOKEN

async def handle_index(request):
    """返回远程控制前端页面"""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    return web.Response(text="<h1>index.html 未找到</h1>", content_type="text/html", status=404)

async def handle_status(request):
    """查询当前状态和配置限额"""
    return web.json_response({
        "connected_modules": len(modules),
        "limits": {
            "max_strength": MAX_STRENGTH,
            "max_duration": MAX_DURATION,
            "cooldown": COOLDOWN
        }
    })

async def handle_control(request):
    """HTTP API 方式发送控制指令"""
    global last_command_time
    if not verify_auth(request):
        raise web.HTTPUnauthorized()

    if not modules:
        return web.json_response({"ok": False, "error": "没有在线的设备客户端 (remote_module 未连接)"}, status=503)

    # 检查冷却时间
    now = time.time()
    if now - last_command_time < COOLDOWN:
        remaining = round(COOLDOWN - (now - last_command_time), 1)
        return web.json_response({"ok": False, "error": f"指令过于频繁，请等待冷却 ({remaining}s)"}, status=429)

    try:
        data = await request.json()
        action = data.get("action")
        strength = int(data.get("strength", 0))

        command = {"action": action}
        if action == "stop":
            pass
        elif action == "adjust":
            direction = data.get("direction", "add")
            if not (1 <= strength <= MAX_STRENGTH):
                return web.json_response({"ok": False, "error": f"强度超出范围 (1-{MAX_STRENGTH})"}, status=400)
            command["strength"] = strength
            command["direction"] = direction
        elif action == "pulse":
            duration = float(data.get("duration", 0))
            if not (1 <= strength <= MAX_STRENGTH):
                return web.json_response({"ok": False, "error": f"强度超出范围 (1-{MAX_STRENGTH})"}, status=400)
            if not (0 < duration <= MAX_DURATION):
                return web.json_response({"ok": False, "error": f"时长超出范围 (0-{MAX_DURATION}s)"}, status=400)
            command["strength"] = strength
            command["duration"] = duration
        else:
            return web.json_response({"ok": False, "error": "不支持的 action"}, status=400)

        last_command_time = now
        # 广播给所有绑定的被控端
        msg = json.dumps({"type": "command", "command": command})
        for ws in list(modules):
            await ws.send_str(msg)

        logger.info(f"已转发远程控制指令: {command}")
        return web.json_response({"ok": True, "command": command})
    except Exception as e:
        logger.error(f"处理远程指令异常: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=400)

async def handle_ws_module(request):
    """供被控机 remote_module.py 连接的 WebSocket 入口"""
    if not verify_auth(request):
        raise web.HTTPUnauthorized()

    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    modules.add(ws)
    logger.info(f"客户端 (remote_module) 已接入, 当前在线: {len(modules)}")

    try:
        async for msg in ws:
            pass
    finally:
        modules.discard(ws)
        logger.info(f"客户端断开, 当前在线: {len(modules)}")

    return ws

def make_app():
    app = web.Application()
    # 静态文件
    html_dir = os.path.dirname(__file__)
    if os.path.exists(os.path.join(html_dir, "static")):
        app.router.add_static("/static", os.path.join(html_dir, "static"))

    # 路由
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/status", handle_status)
    app.router.add_post("/api/control", handle_control)
    app.router.add_get("/ws/module", handle_ws_module)
    return app

if __name__ == "__main__":
    app = make_app()
    logger.info(f"DG-Lab 远程控制服务端启动中: http://{HOST}:{PORT}")
    logger.info(f"当前服务端鉴权 Token: '{TOKEN}'")
    web.run_app(app, host=HOST, port=PORT)
