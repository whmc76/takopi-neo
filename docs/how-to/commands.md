# Use Telegram commands and directives

This guide is the practical command sheet for using Takopi from Telegram. Use
`/help` in the bot any time you want the same command set inside the chat.

## Mental model

Takopi has two kinds of instructions:

| Kind | Where it goes | What it does |
|------|---------------|--------------|
| Directive | Start of a normal message | Chooses engine, project, or branch for that task. |
| Command | Whole message starting with `/` | Changes Takopi state or performs a utility action. |

Directives are for one task. Commands are for managing the chat, topic, engine
defaults, files, and sessions.

## Start a task

Send a normal message:

```text
fix the failing tests
```

Choose an engine for one message:

```text
/codex fix the failing tests
```

Choose a project:

```text
/myproject update the changelog
```

Choose a branch worktree:

```text
@fix-login reproduce the login failure
```

Combine them:

```text
/codex /myproject @fix-login reproduce the login failure
```

Rules:

- Put directives at the start of the first non-empty line.
- Use one engine directive, one project directive, and optionally one `@branch`.
- Takopi stops parsing directives at the first normal word.
- Replying to a message with a `ctx:` footer reuses that context.

## Built-in commands

| Command | Use when |
|---------|----------|
| `/help` | You want the command list in Telegram. |
| `/new` | You want a clean conversation thread in the current chat or topic. |
| `/ctx` | You want to see the current project/branch binding. |
| `/ctx set <project> [@branch]` | You want this chat or topic to default to a project/branch. |
| `/ctx clear` | You want to remove the chat or topic binding. |
| `/agent` | You want to see the active engine and defaults. |
| `/agent set <engine>` | You want this chat or topic to default to an engine. |
| `/agent clear` | You want to remove that engine default. |
| `/model` | You want to see the active model override. |
| `/model set [engine] <model>` | You want to pin a model for an engine. |
| `/model clear [engine]` | You want to remove a model override. |
| `/reasoning` | You want to see the active reasoning override. |
| `/reasoning set [engine] <level>` | You want to pin a reasoning level for an engine. |
| `/reasoning clear [engine]` | You want to remove a reasoning override. |
| `/trigger` | You want to see when the bot responds in this chat or topic. |
| `/trigger all` | You want Takopi to respond to every message. |
| `/trigger mentions` | You want Takopi to respond only when mentioned or addressed. |
| `/trigger clear` | You want to reset trigger mode to the chat default. |
| `/file put <path>` | You want to upload a Telegram document into the repo. |
| `/file get <path>` | You want Takopi to send a repo file or directory back to Telegram. |
| `/topic <project> @branch` | You want to create or bind a forum topic for a project branch. |
| `/cancel` | You want to stop a running task; reply to the progress message. |

Project aliases are also commands. If you registered a project named `web`, then
`/web fix routing` means “run this task in the `web` project.”

Engine ids are also commands. If `codex`, `claude`, `opencode`, and `pi` are
configured, then `/codex`, `/claude`, `/opencode`, and `/pi` select that engine
for one message.

Plugins can add more commands. They appear in `/help` and in Telegram’s command
menu when the plugin is enabled.

## Common workflows

Bind a chat to a repo once, then send short tasks:

```text
/ctx set myproject
```

```text
fix the failing tests
```

Start fresh without losing the bound repo:

```text
/new
```

Run one task on a branch worktree:

```text
@feature/search implement search filters
```

Change defaults for a topic:

```text
/agent set codex
/model set gpt-5.1-codex-max
/reasoning set high
```

Upload a file into the current project:

```text
/file put docs/spec.md
```

Then attach the document to that Telegram message.

Fetch a directory:

```text
/file get docs
```

## Scope and permissions

- In private chats, command settings apply to that chat.
- In forum topics, command settings apply to that topic.
- In groups, changing `/agent`, `/model`, `/reasoning`, `/trigger`, and file
  transfer settings is restricted to admins.
- `/new` clears stored sessions only. It does not clear `/ctx`, `/agent`,
  `/model`, `/reasoning`, or `/trigger` settings.
