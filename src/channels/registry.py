"""渠道注册表：按名称返回渠道实例，调用方无需关心平台差异。"""
from src.channels.base import BaseChannel, ChannelResult

# name -> 无参工厂（各渠道类用 create() 按全局配置构造默认实例）
_FACTORIES: dict[str, type[BaseChannel]] = {}


def _register(cls):
    _FACTORIES[cls.name] = cls
    return cls


def get_channel(name: str | None = None) -> BaseChannel:
    """按渠道名实例化渠道；未指定时使用全局配置 CHANNEL（默认 mock）。"""
    from src import config

    key = (name or config.CHANNEL or "mock").strip().lower()
    factory = _FACTORIES.get(key)
    if factory is None:
        raise ValueError(
            f"未知渠道：{key}，可选：{', '.join(sorted(_FACTORIES))}"
        )
    return factory.create()


def available_channels() -> list[str]:
    return sorted(_FACTORIES)


# 注册内置渠道（延迟导入避免循环依赖：registry 只被 __init__ 与测试引用）
from src.channels.api_channel import ApiChannel  # noqa: E402
from src.channels.mock_channel import MockChannel  # noqa: E402

_register(MockChannel)
_register(ApiChannel)