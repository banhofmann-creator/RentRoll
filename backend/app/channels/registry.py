from __future__ import annotations

from app.channels.base import OutputChannel
from app.channels.local_filesystem import LocalFilesystemChannel

_CHANNELS: dict[str, type[OutputChannel]] = {}


def register_channel(name: str, cls: type[OutputChannel]) -> None:
    _CHANNELS[name] = cls


def get_channel(name: str) -> OutputChannel:
    channel_cls = _CHANNELS.get(name)
    if channel_cls is None:
        raise ValueError(f"Unknown channel: {name}")
    return channel_cls()


def list_channels() -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "description": channel_cls.description,
        }
        for name, channel_cls in sorted(_CHANNELS.items())
    ]


register_channel(LocalFilesystemChannel.name, LocalFilesystemChannel)
