from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

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

_BUILTIN_COMMANDS_ZH: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="help",
        description="显示命令帮助",
        usage="/help",
        details="显示这份命令指南。",
    ),
    TelegramCommandInfo(
        command="new",
        description="开始新线程",
        usage="/new",
        details="清除当前聊天或话题保存的会话，不改变上下文。",
    ),
    TelegramCommandInfo(
        command="ctx",
        description="查看或更新上下文",
        usage="/ctx | /ctx set <project> [@branch] | /ctx clear",
        details="查看、绑定或清除当前聊天或话题的项目和分支。",
    ),
    TelegramCommandInfo(
        command="agent",
        description="设置默认引擎",
        usage="/agent | /agent set <engine> | /agent clear",
        details="查看或修改当前聊天或话题的默认引擎。",
    ),
    TelegramCommandInfo(
        command="model",
        description="设置模型覆盖",
        usage="/model | /model set [engine] <model> | /model clear [engine]",
        details="查看或修改某个引擎的模型覆盖。",
    ),
    TelegramCommandInfo(
        command="reasoning",
        description="设置推理级别",
        usage="/reasoning | /reasoning set [engine] <level> | /reasoning clear [engine]",
        details="查看或修改某个引擎的推理级别覆盖。",
    ),
    TelegramCommandInfo(
        command="trigger",
        description="设置触发模式",
        usage="/trigger | /trigger all | /trigger mentions | /trigger clear",
        details="选择机器人响应所有消息，还是只响应明确提及。",
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

_TOPIC_COMMANDS_ZH: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="topic",
        description="创建或绑定话题",
        usage="/topic <project> @branch",
        details="创建论坛话题，并绑定到项目分支。",
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

_FILE_COMMANDS_ZH: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="file",
        description="上传或获取文件",
        usage="/file put <path> | /file get <path>",
        details="把 Telegram 文档上传到仓库，或把仓库文件取回 Telegram。",
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

_CANCEL_COMMANDS_ZH: tuple[TelegramCommandInfo, ...] = (
    TelegramCommandInfo(
        command="cancel",
        description="取消运行",
        usage="/cancel",
        details="回复正在运行的进度消息以停止该任务。",
    ),
)

TelegramLanguage = Literal["en", "zh"]


def _builtin_command_infos(
    *,
    include_file: bool,
    include_topics: bool,
    language: TelegramLanguage = "en",
) -> tuple[TelegramCommandInfo, ...]:
    builtins = _BUILTIN_COMMANDS_ZH if language == "zh" else _BUILTIN_COMMANDS
    topic_commands = _TOPIC_COMMANDS_ZH if language == "zh" else _TOPIC_COMMANDS
    file_commands = _FILE_COMMANDS_ZH if language == "zh" else _FILE_COMMANDS
    cancel_commands = _CANCEL_COMMANDS_ZH if language == "zh" else _CANCEL_COMMANDS

    commands = [*builtins]
    if include_topics:
        commands.extend(topic_commands)
    if include_file:
        commands.extend(file_commands)
    commands.extend(cancel_commands)
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
    language: TelegramLanguage = "en",
) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    seen: set[str] = set()
    for engine_id in runtime.available_engine_ids():
        cmd = engine_id.lower()
        if cmd in seen:
            continue
        description = f"使用引擎：{cmd}" if language == "zh" else f"use engine: {cmd}"
        commands.append({"command": cmd, "description": description})
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
        description = f"处理项目：{cmd}" if language == "zh" else f"work on: {cmd}"
        commands.append({"command": cmd, "description": description})
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
        language=language,
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
            {
                "command": "help",
                "description": "显示命令帮助"
                if language == "zh"
                else "show command help",
            },
            {
                "command": "cancel",
                "description": "取消运行" if language == "zh" else "cancel run",
            },
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
    language: TelegramLanguage = "en",
) -> str:
    if language == "zh":
        lines = [
            "Takopi 命令帮助",
            "",
            "指令（放在消息开头）：",
        ]
    else:
        lines = [
            "Takopi command help",
            "",
            "Directives (put these at the start of a message):",
        ]
    engine_ids = list(runtime.available_engine_ids())
    if engine_ids:
        if language == "zh":
            lines.append(f"`/<engine>` 选择引擎：{', '.join(engine_ids)}")
        else:
            lines.append(f"`/<engine>` choose engine: {', '.join(engine_ids)}")
    aliases = [
        alias for alias in runtime.project_aliases() if is_valid_id(alias.lower())
    ]
    if aliases:
        if language == "zh":
            lines.append(f"`/<project>` 选择项目：{', '.join(aliases)}")
        else:
            lines.append(f"`/<project>` choose project: {', '.join(aliases)}")
    if language == "zh":
        lines.extend(
            [
                "`@branch` 选择或创建分支 worktree。",
                "示例：`/codex /myproj @fix-login update the tests`",
                "",
                "内置命令：",
            ]
        )
    else:
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
            language=language,
        )
    )
    plugin_infos = _plugin_command_infos(runtime)
    if plugin_infos:
        section = "插件命令：" if language == "zh" else "Plugin commands:"
        lines.extend(["", section])
        lines.extend(f"`{info.usage}` - {info.details}" for info in plugin_infos)
    if language == "zh":
        lines.extend(
            [
                "",
                "说明：",
                "`/agent`、`/model`、`/reasoning` 和 `/trigger` 影响当前聊天或话题。",
                "在群组中，修改默认设置仅限管理员。",
                "`/new` 只清除会话，不清除 `/ctx` 绑定。",
            ]
        )
    else:
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
        if language == "zh":
            lines.append("话题命令已隐藏，因为未启用 topics。")
        else:
            lines.append("Topic commands are hidden because topics are not enabled.")
    if not include_file:
        if language == "zh":
            lines.append("文件命令已隐藏，因为未启用文件传输。")
        else:
            lines.append(
                "File commands are hidden because file transfer is not enabled."
            )
    return "\n\n".join(lines)


def _telegram_language_code(language: TelegramLanguage) -> str | None:
    if language == "zh":
        return "zh"
    return None


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
        language=cfg.language,
    )
    if not commands:
        return
    try:
        ok = await cfg.bot.set_my_commands(
            commands,
            language_code=_telegram_language_code(cfg.language),
        )
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
