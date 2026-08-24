"""部署在运行主程序电脑上的远程模块。

它主动连接远程服务端，不要求主程序开放公网端口。
"""
import asyncio
import json
import logging
import os

import aiohttp

LOG = logging.getLogger("remote-module")


async def forward(session, command, local_url, local_token):
    headers = {"Authorization": f"Bearer {local_token}"}
    async with session.post(f"{local_url}/api/remote-command", json=command, headers=headers) as response:
        if response.status >= 300:
            LOG.warning("local command rejected: %s", await response.text())


async def run(config=None):
    remote = (config or {}).get("remote", {})
    show_log = remote.get("show_log", True)
    server_url = remote.get("server_ws") or os.environ.get("REMOTE_SERVER_WS")
    token = remote.get("server_token") or os.environ.get("REMOTE_TOKEN")
    local_url = remote.get("local_url", "http://127.0.0.1:8080")
    local_token = remote.get("local_token") or os.environ.get("LOCAL_CONTROL_TOKEN")
    if not server_url or not token or not local_token:
        if show_log:
            LOG.warning("远程服务端未连接：请检查 remote.server_ws、server_token 和 local_token 配置")
        return
    headers = {"Authorization": f"Bearer {token}"}
    timeout = aiohttp.ClientTimeout(total=10)
    announced_failure = False
    while True:
        try:
            if not announced_failure and show_log:
                LOG.info("正在连接远程服务端: %s", server_url)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as session:
                # 强制使用 ssl=False 且不进行证书验证
                async with session.ws_connect(server_url, headers=headers, heartbeat=30, ssl=False) as ws:
                    LOG.info("【远程控制】已成功连接到远程服务端")  # 修改点
                    announced_failure = False
                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            payload = json.loads(message.data)
                            if payload.get("type") == "command":
                                await forward(session, payload["command"], local_url, local_token)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError) as exc:
            if not announced_failure and show_log:
                LOG.warning("【远程控制】未连接到远程服务端：%s；后台每 5 秒重试", exc)
                announced_failure = True
            await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
