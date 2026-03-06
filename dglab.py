# -*- coding: utf-8 -*-
import asyncio
import http.cookies
import logging
import os
import re
from typing import Optional

import aiohttp
import yaml

import blivedm
import blivedm.models.web as web_models

# ── 配置加载 ──────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

ROOM_ID: int           = cfg["bilibili"]["room_id"]
SESSDATA: str          = cfg["bilibili"]["sessdata"]
CONTROLLER_URL: str    = cfg["dglab"]["controller_url"].rstrip("/")
CONTROLLER_ID: str     = cfg["dglab"]["controller_id"]

DANMAKU_CFG: dict      = cfg["danmaku"]
GUARD_BONUS_ENABLED    = DANMAKU_CFG.get("guard_bonus", {}).get("enabled", False)
GUARD_BONUS_CFG: dict  = {int(k): v for k, v in DANMAKU_CFG.get("guard_bonus", {}).items() if isinstance(k, int)}
INTERACT_CFG: dict     = cfg.get("interact", {})
GIFT_TIERS: list       = sorted(cfg["gift"]["tiers"], key=lambda t: t["min_price"], reverse=True)
SC_TIERS: list         = sorted(cfg["super_chat"]["tiers"], key=lambda t: t["min_price"], reverse=True)
GUARD_LEVELS: dict     = {int(k): v for k, v in cfg["guard"]["levels"].items()}

# ── 日志 ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, cfg["log"]["level"].upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
logging.getLogger("blivedm").setLevel(logging.CRITICAL)

# ── 时间解析 ──────────────────────────────────────────────────────────────────
def parse_duration(value) -> float:
    """支持 "30s" / "2m" / "1m30s" / 纯数字（秒）"""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    m_min = re.search(r'(\d+(?:\.\d+)?)\s*m', s)
    m_sec = re.search(r'(\d+(?:\.\d+)?)\s*s', s)
    total = (float(m_min.group(1)) if m_min else 0.0) * 60 + (float(m_sec.group(1)) if m_sec else 0.0)
    if total <= 0:
        raise ValueError(f"无法解析时间：{value!r}，支持格式如 '30s' '2m' '1m30s'")
    return total

def fmt_duration(value) -> str:
    secs = parse_duration(value)
    m, s = divmod(int(secs), 60)
    if m and s:
        return f"{m}m{s}s"
    return f"{m}m" if m else f"{s}s"

# ── 弹幕限流（滑动窗口） ──────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self, per: float, max_triggers: int):
        self._per = per
        self._max = max_triggers
        self._records: dict[int, list[float]] = {}

    def allow(self, uid: int) -> bool:
        now = asyncio.get_event_loop().time()
        ts = [t for t in self._records.get(uid, []) if now - t < self._per]
        if len(ts) >= self._max:
            self._records[uid] = ts
            return False
        ts.append(now)
        self._records[uid] = ts
        return True

_rl_cfg = DANMAKU_CFG.get("rate_limit", {})
_rate_limiter = RateLimiter(
    per=parse_duration(_rl_cfg.get("per", "1m")),
    max_triggers=int(_rl_cfg.get("max_triggers", 5)),
)

# ── DG-Lab 强度控制 ───────────────────────────────────────────────────────────
session: Optional[aiohttp.ClientSession] = None

async def _strength(*, add: int = 0, sub: int = 0):
    url = f"{CONTROLLER_URL}/api/v2/game/{CONTROLLER_ID}/strength"
    payload = {"strength": {"add": add} if add else {"sub": sub}}
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            data = await resp.json()
            if data.get("status") != 1:
                logger.warning(f"[DGLab] 接口异常: {data}")
    except Exception as e:
        logger.error(f"[DGLab] 请求失败: {e}")

async def strength_pulse(add: int, duration):
    """加强度 → 等待 → 减回来"""
    await _strength(add=add)
    await asyncio.sleep(parse_duration(duration))
    await _strength(sub=add)

def fire(add: int, duration):
    asyncio.create_task(strength_pulse(add, duration))

def match_tier(tiers: list, price: float) -> Optional[dict]:
    return next((t for t in tiers if price >= t["min_price"]), None)

# ── 事件处理器 ────────────────────────────────────────────────────────────────
GUARD_NAME = {1: "总督", 2: "提督", 3: "舰长"}

class MyHandler(blivedm.BaseHandler):

    def handle(self, client, command: dict):
        """重写 handle，过滤掉不需要的 cmd，不产生任何 WARNING"""
        if command.get("cmd", "") in self._CMD_CALLBACK_DICT:
            super().handle(client, command)

    def _on_danmaku(self, client, message: web_models.DanmakuMessage):
        if not DANMAKU_CFG.get("enabled", True):
            return
        if not _rate_limiter.allow(message.uid):
            logger.debug(f"[限流] {message.uname} 弹幕过于频繁，忽略")
            return

        add      = DANMAKU_CFG["strength_add"]
        duration = DANMAKU_CFG["duration"]
        logger.info(f"[弹幕] {message.uname}：{message.msg} → +{add} / {fmt_duration(duration)}")
        fire(add, duration)

        # 舰长额外加成
        if GUARD_BONUS_ENABLED and message.privilege_type in GUARD_BONUS_CFG:
            bonus = GUARD_BONUS_CFG[message.privilege_type]
            name  = GUARD_NAME.get(message.privilege_type, "")
            logger.info(f"[弹幕·{name}加成] {message.uname} → +{bonus['strength_add']} / {fmt_duration(bonus['duration'])}")
            fire(bonus["strength_add"], bonus["duration"])

    def _on_gift(self, client, message: web_models.GiftMessage):
        if not cfg["gift"].get("enabled", True) or message.coin_type != "gold":
            return
        price = message.total_coin / 1000.0
        tier  = match_tier(GIFT_TIERS, price)
        if tier is None:
            logger.info(f"[礼物] {message.uname} {message.gift_name} x{message.num}（¥{price:.2f}）→ 未达最低档位")
            return
        logger.info(f"[礼物] {message.uname} {message.gift_name} x{message.num}（¥{price:.2f}）→ +{tier['strength_add']} / {fmt_duration(tier['duration'])}")
        fire(tier["strength_add"], tier["duration"])

    def _on_super_chat(self, client, message: web_models.SuperChatMessage):
        if not cfg["super_chat"].get("enabled", True):
            return
        tier = match_tier(SC_TIERS, float(message.price))
        if tier is None:
            logger.info(f"[SC ¥{message.price}] {message.uname}：{message.message} → 未达最低档位")
            return
        logger.info(f"[SC ¥{message.price}] {message.uname}：{message.message} → +{tier['strength_add']} / {fmt_duration(tier['duration'])}")
        fire(tier["strength_add"], tier["duration"])

    def _on_interact_word_v2(self, client, message: web_models.InteractWordV2Message):
        key_map  = {1: "enter", 2: "follow", 3: "share", 4: "special_follow"}
        name_map = {1: "进入房间", 2: "关注", 3: "分享", 4: "特别关注"}
        key      = key_map.get(message.msg_type)
        if not key:
            return
        ecfg = INTERACT_CFG.get(key, {})
        if not ecfg.get("enabled", False):
            return
        logger.info(f"[{name_map[message.msg_type]}] {message.username} → +{ecfg['strength_add']} / {fmt_duration(ecfg['duration'])}")
        fire(ecfg["strength_add"], ecfg["duration"])

    def _on_user_toast_v2(self, client, message: web_models.UserToastV2Message):
        if not cfg["guard"].get("enabled", True) or message.source == 2:
            return
        lcfg = GUARD_LEVELS.get(message.guard_level)
        if lcfg is None:
            return
        name = GUARD_NAME.get(message.guard_level, "舰长")
        logger.info(f"[上舰] {message.username} 开通{name} → +{lcfg['strength_add']} / {fmt_duration(lcfg['duration'])}")
        fire(lcfg["strength_add"], lcfg["duration"])

# ── 主程序 ────────────────────────────────────────────────────────────────────
async def main():
    cookies = http.cookies.SimpleCookie()
    cookies["SESSDATA"] = SESSDATA
    cookies["SESSDATA"]["domain"] = "bilibili.com"

    global session
    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)

    client = blivedm.BLiveClient(ROOM_ID, session=session)
    client.set_handler(MyHandler())
    client.start()
    logger.info(f"已连接到直播间 {ROOM_ID}，按 Ctrl+C 退出")

    try:
        await client.join()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await client.stop_and_close()
        await session.close()
        logger.info("已退出")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass