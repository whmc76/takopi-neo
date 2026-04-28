from __future__ import annotations

from typing import TYPE_CHECKING

from .menu import build_help_text
from .reply import make_reply

if TYPE_CHECKING:
    from ..bridge import TelegramBridgeConfig
    from ..types import TelegramIncomingMessage


async def _handle_help_command(
    cfg: TelegramBridgeConfig,
    msg: TelegramIncomingMessage,
) -> None:
    reply = make_reply(cfg, msg)
    await reply(
        text=build_help_text(
            cfg.runtime,
            include_file=cfg.files.enabled,
            include_topics=cfg.topics.enabled,
            language=cfg.language,
        )
    )
