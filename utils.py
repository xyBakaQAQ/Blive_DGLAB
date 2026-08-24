# -*- coding: utf-8 -*-
"""工具函数模块"""
import re


def parse_duration(value) -> float:
    """
    解析时间字符串为秒数
    支持格式: "30s" / "2m" / "1m30s" / 纯数字（秒）
    """
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
    """
    格式化时间为可读字符串
    例如: 90 -> "1m30s", 60 -> "1m", 30 -> "30s"
    """
    m, s = divmod(int(parse_duration(value)), 60)
    if m and s:
        return f"{m}m{s}s"
    return f"{m}m" if m else f"{s}s"
