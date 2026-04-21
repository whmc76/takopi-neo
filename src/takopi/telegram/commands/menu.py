from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...commands import get_command
from ...config import ConfigError
from ...ids import RESERVED_COMMAND_IDS, is_valid_id
from ...logging import get_logger
from ...plugins import COMMAND_GROUP, list_entrypoints
from ...transport_runtime import TransportRuntime

if TYPE_CHECKING:
    from ..bridge import TelegramBridgeConfig

logger = get_logger(__name__)

_MAX_BOT_COMMANDS = 100


@dataclass(frozen=True, slots=True)
class TelegramCommandInfo:
    command: str
    description: str
    usage: str
    details: str


_BUILTIN_COMMANDS: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="help",
        description="show command help",
        usage="/help",
        details="Show this command guide.",
    ),
    TelegramCommandInfo(
        command="new",
        description="start a new thread",
        usage="/new",
        details="Clear stored sessions for this chat or topic without changing context.",
    ),
    TelegramCommandInfo(
        command="ctx",
        description="show or update context",
        usage="/ctx | /ctx set <project> [@branch] | /ctx clear",
        details="Show, bind, or clear the project and branch for this chat or topic.",
    ),
    TelegramCommandInfo(
        command="agent",
        description="set default engine",
        usage="/agent | /agent set <engine> | /agent clear",
        details="Show or change the default engine for this chat or topic.",
    ),
    TelegramCommandInfo(
        command="model",
        description="set model override",
        usage="/model | /model set [engine] <model> | /model clear [engine]",
        details="Show or change the model override for an engine.",
    ),
    TelegramCommandInfo(
        command="reasoning",
        description="set reasoning override",
        usage="/reasoning | /reasoning set [engine] <level> | /reasoning clear [engine]",
        details="Show or change the reasoning level override for an engine.",
    ),
    TelegramCommandInfo(
        command="trigger",
        description="set trigger mode",
        usage="/trigger | /trigger all | /trigger mentions | /trigger clear",
        details="Choose whether the bot responds to all messages or only mentions.",
    ),
)

_TOPIC_COMMANDS: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="topic",
        description="create or bind a topic",
        usage="/topic <project> @branch",
        details="Create a forum topic and bind it to a project branch.",
    ),
)

_FILE_COMMANDS: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="file",
        description="upload or fetch files",
        usage="/file put <path> | /file get <path>",
        details="Upload Telegram documents into a repo or fetch repo files back.",
    ),
)

_CANCEL_COMMANDS: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="cancel",
        description="cancel run",
        usage="/cancel",
        details="Reply to a running progress message to stop that run.",
    ),
)


def _builtin_command_infos(
    *,
    include_file: bool,
    include_topics: bool,
) -> tuple[TelegramCommandInfo, ...]:
    commands = [*_BUILTIN_COMMANDS]
    if include_topics:
        commands.extend(_TOPIC_COMMANDS)
    if include_file:
        commands.extend(_FILE_COMMANDS)
    commands.extend(_CANCEL_COMMANDS)
    return tuple(commands)


def _plugin_command_infos(runtime: TransportRuntime) -> list[TelegramCommandInfo]:
    commands: list[TelegramCommandInfo] = []
    allowlist = runtime.allowlist
    for ep in list_entrypoints(
        COMMAND_GROUP,
        allowlist=allowlist,
        reserved_ids=RESERVED_COMMAND_IDS,
    ):
        try:
            backend = get_command(ep.name, allowlist=allowlist)
        except ConfigError as exc:
            logger.info(
                "startup.command_menu.skip_command",
                command=ep.name,
                error=str(exc),
            )
            continue
        cmd = backend.id.lower()
        if not is_valid_id(cmd):
            logger.debug(
                "startup.command_menu.skip_command_id",
                command=cmd,
            )
            continue
        description = backend.description or f"command: {cmd}"
        commands.append(
            TelegramCommandInfo(
                command=cmd,
                description=description,
                usage=f"/{cmd}",
                details=description,
            )
        )
    return commands


def build_bot_commands(
    runtime: TransportRuntime,
    *,
    include_file: bool = True,
    include_topics: bool = False,
) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    seen: set[str] = set()
    for engine_id in runtime.available_engine_ids():
        cmd = engine_id.lower()
        if cmd in seen:
            continue
        commands.append({"command": cmd, "description": f"use engine: {cmd}"})
        seen.add(cmd)
    for alias in runtime.project_aliases():
        cmd = alias.lower()
        if cmd in seen:
            continue
        if not is_valid_id(cmd):
            logger.debug(
                "startup.command_menu.skip_project",
                alias=alias,
            )
            continue
        commands.append({"command": cmd, "description": f"work on: {cmd}"})
        seen.add(cmd)
    for info in _plugin_command_infos(runtime):
        cmd = info.command
        if cmd in seen:
            continue
        commands.append({"command": cmd, "description": info.description})
        seen.add(cmd)
    for info in _builtin_command_infos(
        include_file=include_file,
        include_topics=include_topics,
    ):
        cmd = info.command
        if cmd in seen:
            continue
        commands.append({"command": cmd, "description": info.description})
        seen.add(cmd)
    if len(commands) > _MAX_BOT_COMMANDS:
        logger.warning(
            "startup.command_menu.too_many",
            count=len(commands),
            limit=_MAX_BOT_COMMANDS,
        )
        commands = commands[:_MAX_BOT_COMMANDS]
        required = (
            {"command": "help", "description": "show command help"},
            {"command": "cancel", "description": "cancel run"},
        )
        for offset, required_cmd in enumerate(reversed(required)):
            if any(cmd["command"] == required_cmd["command"] for cmd in commands):
                continue
            commands[-1 - offset] = required_cmd
    return commands


def build_help_text(
    runtime: TransportRuntime,
    *,
    include_file: bool = True,
    include_topics: bool = False,
) -> str:
    lines = [
        "Takopi command help",
        "",
        "Directives (put these at the start of a message):",
    ]
    engine_ids = list(runtime.available_engine_ids())
    if engine_ids:
        lines.append(f"`/<engine>` choose engine: {', '.join(engine_ids)}")
    aliases = [
        alias for alias in runtime.project_aliases() if is_valid_id(alias.lower())
    ]
    if aliases:
        lines.append(f"`/<project>` choose project: {', '.join(aliases)}")
    lines.extend(
        [
            "`@branch` choose or create a branch worktree.",
            "Example: `/codex /myproj @fix-login update the tests`",
            "",
            "Built-in commands:",
        ]
    )
    lines.extend(
        f"`{info.usage}` - {info.details}"
        for info in _builtin_command_infos(
            include_file=include_file,
            include_topics=include_topics,
        )
    )
    plugin_infos = _plugin_command_infos(runtime)
    if plugin_infos:
        lines.extend(["", "Plugin commands:"])
        lines.extend(f"`{info.usage}` - {info.details}" for info in plugin_infos)
    lines.extend(
        [
            "",
            "Notes:",
            "`/agent`, `/model`, `/reasoning`, and `/trigger` affect the current chat or topic.",
            "In groups, changing defaults is restricted to admins.",
            "`/new` clears conversation sessions only; it does not clear `/ctx` bindings.",
        ]
    )
    if not include_topics:
        lines.append("Topic commands are hidden because topics are not enabled.")
    if not include_file:
        lines.append("File commands are hidden because file transfer is not enabled.")
    return "\n\n".join(lines)


def _reserved_commands(runtime: TransportRuntime) -> set[str]:
    return {
        *{engine.lower() for engine in runtime.engine_ids},
        *{alias.lower() for alias in runtime.project_aliases()},
        *RESERVED_COMMAND_IDS,
    }


async def _set_command_menu(cfg: TelegramBridgeConfig) -> None:
    commands = build_bot_commands(
        cfg.runtime,
        include_file=cfg.files.enabled,
        include_topics=cfg.topics.enabled,
    )
    if not commands:
        return
    try:
        ok = await cfg.bot.set_my_commands(commands)
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "startup.command_menu.failed",
            error=str(exc),
            error_type=exc.__class__.__name__,
        )
        return
    if not ok:
        logger.info("startup.command_menu.rejected")
        return
    logger.info(
        "startup.command_menu.updated",
        commands=[cmd["command"] for cmd in commands],
    )
