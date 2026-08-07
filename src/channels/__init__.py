"""渠道适配器包：统一发布契约（BaseChannel）+ 渠道实现（Mock / Api / RPA 基类）。

- get_channel(name) 按配置返回渠道实例
- ChannelResult 是发布/下架的结构化结果
"""
from src.channels.base import BaseChannel, ChannelResult
from src.channels.registry import available_channels, get_channel

__all__ = [
    "BaseChannel",
    "ChannelResult",
    "available_channels",
    "get_channel",
]