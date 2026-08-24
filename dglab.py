# -*- coding: utf-8 -*-
"""DG-Lab 郊狼控制器模块"""
import asyncio
import logging

import aiohttp

from utils import parse_duration

logger = logging.getLogger(__name__)

class DGLabController:
    """DG-Lab 郊狼控制器"""
    
    def __init__(self, controller_url: str, controller_id: str, session: aiohttp.ClientSession, enabled: bool = True):
        self.controller_url = controller_url.rstrip("/")
        self.controller_id = controller_id
        self.session = session
        self.enabled = enabled

    async def strength(self, *, add: int = 0, sub: int = 0):
        """调整强度"""
        if not self.enabled:
            logger.debug(f"[DGLab] 已禁用，跳过强度调整")
            return
            
        url = f"{self.controller_url}/api/v2/game/{self.controller_id}/strength"
        payload = {"strength": {"add": add} if add else {"sub": sub}}
        try:
            async with self.session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                if data.get("status") != 1:
                    logger.warning(f"[DGLab] 接口异常: {data}")
        except Exception as e:
            logger.error(f"[DGLab] 请求失败: {e}")

    async def pulse(self, add: int, duration):
        """脉冲：增加强度，持续一段时间后减少"""
        if not self.enabled:
            logger.debug(f"[DGLab] 已禁用，跳过脉冲")
            return
            
        await self.strength(add=add)
        await asyncio.sleep(parse_duration(duration))
        await self.strength(sub=add)