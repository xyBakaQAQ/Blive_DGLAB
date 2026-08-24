# -*- coding: utf-8 -*-
"""哔哩哔哩直播间监听模块"""
import asyncio
import logging
import time
from typing import Optional

import blivedm
import blivedm.models.web as web_models

from utils import parse_duration, fmt_duration

logger = logging.getLogger(__name__)

# ── 限流器 ────────────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self, time_window: float, max_count: int, enabled: bool = True):
        self._time_window = time_window
        self._max_count = max_count
        self._enabled = enabled
        self._user_records: dict[int, list[float]] = {}

    def allow(self, uid: int) -> bool:
        """检查用户是否允许触发"""
        if not self._enabled:
            return True
        
        now = asyncio.get_event_loop().time()
        timestamps = [t for t in self._user_records.get(uid, []) if now - t < self._time_window]
        
        if len(timestamps) >= self._max_count:
            self._user_records[uid] = timestamps
            return False
        
        timestamps.append(now)
        self._user_records[uid] = timestamps
        return True

# ── 事件处理器 ────────────────────────────────────────────────────────────────
GUARD_NAME = {1: "总督", 2: "提督", 3: "舰长"}

class BilibiliHandler(blivedm.BaseHandler):
    def __init__(self, config: dict, dglab_controller, webui=None):
        super().__init__()
        self.config = config
        self.dglab = dglab_controller
        self.webui = webui
        self._gift_seen = {}
        self._gift_seen_ttl = 15
        
        # 初始化限流器
        rl_cfg = config["danmaku"].get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            time_window=parse_duration(rl_cfg.get("time_window", "1m")),
            max_count=int(rl_cfg.get("max_count", 5)),
            enabled=bool(rl_cfg.get("enabled", True)),
        )

    def handle(self, client, command: dict):
        if command.get("cmd", "") in self._CMD_CALLBACK_DICT:
            super().handle(client, command)

    def _on_danmaku(self, client, message: web_models.DanmakuMessage):
        cfg = self.config["danmaku"]
        viewer_rule = self._match_viewer_rule(message)
        if not cfg.get("enabled", True):
            return
        
        if not self.rate_limiter.allow(message.uid):
            logger.info(f"[弹幕] {message.uname}：{message.msg} (已达限流上限)")
            return

        add = int(viewer_rule.get("strength", cfg["strength_add"])) if viewer_rule else cfg["strength_add"]
        duration = viewer_rule.get("duration", cfg["duration"]) if viewer_rule else cfg["duration"]
        logger.info(f"[弹幕] {message.uname}：{message.msg} → +{add} / {fmt_duration(duration)}")
        if viewer_rule and viewer_rule.get("action", "add") == "subtract":
            asyncio.create_task(self.dglab.strength(sub=add))
        else:
            asyncio.create_task(self.dglab.pulse(add, duration))
        
        # 发送到 OBS
        if self.webui:
            asyncio.create_task(self.webui.broadcast_to_obs('danmaku', {
                'username': message.uname,
                'face': message.face,
                'message': message.msg,
                'guard_level': message.privilege_type if message.privilege_type in [1, 2, 3] else None,
                'dglab': {
                    'strength': add,
                    'duration': fmt_duration(duration)
                } if self.dglab.enabled else None
            }))

        # 舰长额外加成
        guard_bonus_cfg = cfg.get("guard_bonus", {})
        if guard_bonus_cfg.get("enabled", False) and message.privilege_type in guard_bonus_cfg:
            bonus = guard_bonus_cfg[message.privilege_type]
            badd = bonus["strength_add"]
            name = GUARD_NAME.get(message.privilege_type, "")
            logger.info(f"[弹幕·{name}加成] {message.uname} → +{badd} / {fmt_duration(bonus['duration'])}")
            asyncio.create_task(self.dglab.pulse(badd, bonus["duration"]))

    def _on_gift(self, client, message: web_models.GiftMessage):
        cfg = self.config["gift"]
        if not cfg.get("enabled", True) or message.coin_type != "gold":
            return
        
        event_id = message.tid or message.rnd
        if event_id:
            now = time.monotonic()
            self._gift_seen = {
                key: timestamp for key, timestamp in self._gift_seen.items()
                if now - timestamp < self._gift_seen_ttl
            }
            if event_id in self._gift_seen:
                return
            self._gift_seen[event_id] = now

        price = message.total_coin / 1000.0
        unit_price = message.price / 1000.0
        tier = self._match_gift_rule(cfg.get("rules", []), message.gift_name, price, unit_price)
        if tier is None and not cfg.get("rules"):
            tier = self._match_tier(cfg.get("tiers", []), price)
        if tier is None:
            logger.info(f"[礼物] {message.uname} {message.gift_name} x{message.num}（¥{price:.2f}）→ 未达最低档位")
            return
        
        add = tier["strength_add"]
        logger.info(f"[礼物] {message.uname} {message.gift_name} x{message.num}（¥{price:.2f}）→ +{add} / {fmt_duration(tier['duration'])}")
        asyncio.create_task(self.dglab.pulse(add, tier["duration"]))
        
        # 发送到 OBS
        if self.webui:
            asyncio.create_task(self.webui.broadcast_to_obs('gift', {
                'username': message.uname,
                'face': message.face,
                'gift_name': message.gift_name,
                'count': message.num,
                'price': f"{price:.2f}",
                'rule': tier.get('gift_name') or f"金额≥{tier.get('min_price', 0)}",
                'dglab': {
                    'strength': add,
                    'duration': fmt_duration(tier['duration'])
                } if self.dglab.enabled else None
            }))

    def _on_super_chat(self, client, message: web_models.SuperChatMessage):
        cfg = self.config["super_chat"]
        if not cfg.get("enabled", True):
            return
        
        tier = self._match_tier(cfg["tiers"], float(message.price))
        if tier is None:
            logger.info(f"[SC ¥{message.price}] {message.uname}：{message.message} → 未达最低档位")
            return
        
        add = tier["strength_add"]
        logger.info(f"[SC ¥{message.price}] {message.uname}：{message.message} → +{add} / {fmt_duration(tier['duration'])}")
        asyncio.create_task(self.dglab.pulse(add, tier["duration"]))
        
        # 发送到 OBS
        if self.webui:
            asyncio.create_task(self.webui.broadcast_to_obs('sc', {
                'username': message.uname,
                'face': message.face,
                'message': message.message,
                'price': message.price,
                'dglab': {
                    'strength': add,
                    'duration': fmt_duration(tier['duration'])
                } if self.dglab.enabled else None
            }))

    def _on_interact_word_v2(self, client, message: web_models.InteractWordV2Message):
        key_map = {1: "enter", 2: "follow", 3: "share", 4: "special_follow"}
        name_map = {1: "进入房间", 2: "关注", 3: "分享", 4: "特别关注"}
        
        key = key_map.get(message.msg_type)
        if not key:
            return
        
        ecfg = self.config.get("interact", {}).get(key, {})
        if not ecfg.get("enabled", False):
            return
        
        add = ecfg["strength_add"]
        logger.info(f"[{name_map[message.msg_type]}] {message.username} → +{add} / {fmt_duration(ecfg['duration'])}")
        asyncio.create_task(self.dglab.pulse(add, ecfg["duration"]))

    def _on_user_toast_v2(self, client, message: web_models.UserToastV2Message):
        cfg = self.config["guard"]
        if not cfg.get("enabled", True) or message.source == 2:
            return
        
        lcfg = cfg["levels"].get(message.guard_level)
        if lcfg is None:
            return
        
        add = lcfg["strength_add"]
        name = GUARD_NAME.get(message.guard_level, "舰长")
        logger.info(f"[上舰] {message.username} 开通{name} → +{add} / {fmt_duration(lcfg['duration'])}")
        asyncio.create_task(self.dglab.pulse(add, lcfg["duration"]))
        
        # 发送到 OBS
        if self.webui:
            asyncio.create_task(self.webui.broadcast_to_obs('guard', {
                'username': message.username,
                'guard_level': message.guard_level,
                'dglab': {
                    'strength': add,
                    'duration': fmt_duration(lcfg['duration'])
                } if self.dglab.enabled else None
            }))

    @staticmethod
    def _match_tier(tiers: list, price: float) -> Optional[dict]:
        sorted_tiers = sorted(tiers, key=lambda t: t["min_price"], reverse=True)
        return next((t for t in sorted_tiers if price >= t["min_price"]), None)

    @staticmethod
    def _match_gift_rule(rules: list, gift_name: str, total_price: float, unit_price: float = None) -> Optional[dict]:
        unit_price = total_price if unit_price is None else unit_price
        for rule in rules:
            if rule.get("enabled", True) is False:
                continue
            rule_name = str(rule.get("gift_name", "")).strip()
            match_type = rule.get("match_type", "exact")
            if rule_name and ((match_type == "contains" and rule_name in gift_name) or
                              (match_type != "contains" and rule_name == gift_name)):
                return rule
        amount_rules = []
        for rule in rules:
            if rule.get("enabled", True) is False or rule.get("gift_name"):
                continue
            if rule.get("min_price") is None and rule.get("max_price") is None:
                continue
            amount = unit_price if rule.get("price_mode", "total") == "unit" else total_price
            minimum = float(rule.get("min_price", 0))
            maximum = rule.get("max_price")
            if amount >= minimum and (maximum in (None, "") or amount <= float(maximum)):
                amount_rules.append(rule)
        return max(amount_rules, key=lambda r: float(r.get("min_price", 0)), default=None)

    def _match_viewer_rule(self, message) -> Optional[dict]:
        cfg = self.config.get("viewer_rules", {})
        if not cfg.get("enabled", False):
            return None
        for rule in cfg.get("special_users", []):
            if rule.get("enabled", True) and str(rule.get("uid", "")) == str(message.uid):
                return rule
        for rule in cfg.get("keywords", []):
            if rule.get("enabled", True) and rule.get("keyword") in message.msg:
                return rule
        return cfg.get("default") if cfg.get("default", {}).get("enabled", True) else None
