# -*- coding: utf-8 -*-
"""主程序入口"""
import asyncio
import http.cookies
import logging
import os
import webbrowser

import aiohttp
import yaml

import blivedm
from bilibili import BilibiliHandler
from dglab import DGLabController
from web import WebUI

# ── 配置加载 ──────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# ── 日志配置 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config["log"]["level"].upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
logging.getLogger("blivedm").setLevel(logging.CRITICAL)

# ── 主程序 ────────────────────────────────────────────────────────────────────
async def main():
    # 设置 Bilibili cookies
    cookies = http.cookies.SimpleCookie()
    cookies["SESSDATA"] = config["bilibili"]["sessdata"]
    cookies["SESSDATA"]["domain"] = "bilibili.com"

    # 创建 session
    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)

    # 初始化 Bilibili 客户端（先初始化客户端）
    room_id = config["bilibili"]["room_id"]
    client = blivedm.BLiveClient(room_id, session=session)

    # 初始化 DG-Lab 控制器
    dglab = DGLabController(
        controller_url=config["dglab"]["controller_url"],
        controller_id=config["dglab"]["controller_id"],
        session=session,
        enabled=config["dglab"].get("enabled", True)
    )

    # 初始化 WebUI
    webui_config = config.get("webui", {})
    webui_host = webui_config.get("host", "0.0.0.0")
    webui_port = webui_config.get("port", 8080)
    webui = WebUI(
        config, 
        dglab, 
        host=webui_host,
        port=webui_port
    )
    await webui.start()
    
    # 自动打开浏览器
    browser_host = "localhost" if webui_host == "0.0.0.0" else webui_host
    webui_url = f"http://{browser_host}:{webui_port}"
    webbrowser.open(webui_url)

    # 设置处理器并启动客户端
    handler = BilibiliHandler(config, dglab, webui)
    client.set_handler(handler)
    client.start()
    
    logger.info(f"已连接到直播间 {room_id}")

    try:
        await client.join()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await client.stop_and_close()
        await webui.stop()
        await session.close()
        logger.info("已退出")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
