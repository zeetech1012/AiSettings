"""Render the tracked baseline into native, user-scoped client files."""

import hashlib
import json
import re
import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLIENTS = json.loads((ROOT / "config/clients.json").read_text())
COMPONENTS = ("rules", "skills", "mcp", "agents", "commands")
COMPATIBILITY = """

## Переносимость процедур AiSettings

- Читай scripts/, references/ и assets/ относительно каталога вызванного skill.
- Упоминания Claude tool names в исходных процедурах сопоставляй с доступными
  инструментами по назначению. Сначала проверяй реальные MCP schemas.
- Название skill можно передать обычным текстом. Slash-команды и $skill зависят
  от клиента. $ARGUMENTS означает запрос, сопровождающий вызов процедуры.
- context: fork, модели sub-agents, hooks и permissions не универсальны.
  Если нужного механизма нет, явно обозначь ограничение; не выдумывай tool calls.
- Проектный AGENTS.md и существующий CLAUDE.md читай оба, если они есть.
"""


def digest(content):
    return hashlib.sha256(content).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def toml_bytes(value):
    """Only the string/list/map subset needed for MCP; preserve quoted keys."""
    lines = []

    def table(data, prefix=()):
        if prefix:
            lines.append("[" + ".".join(json.dumps(p) for p in prefix) + "]")
        for key, item in data.items():
            if not isinstance(item, dict):
                lines.append(f"{json.dumps(key)} = {json.dumps(item, ensure_ascii=False)}")
        for key, item in data.items():
            if isinstance(item, dict):
                lines.append("")
                table(item, (*prefix, key))

    table(value)
    result = "\n".join(lines).strip() + "\n"
    if tomllib.loads(result) != value:
        raise ValueError("MCP TOML round trip failed")
    return result.encode()


def read_servers(path, selected=None):
    source = json.loads(path.read_text())
    if set(source) != {"mcpServers"} or not isinstance(source["mcpServers"], dict):
        raise ValueError("MCP source must contain only an mcpServers object")
    servers = source["mcpServers"]
    if selected is not None:
        unknown = set(selected) - servers.keys()
        if unknown:
            raise ValueError("Unknown MCP servers: " + ", ".join(sorted(unknown)))
        servers = {name: servers[name] for name in selected}
    for name, server in servers.items():
        if not isinstance(server, dict):
            raise ValueError(f"MCP {name}: expected an object")
        transport = server.get("type")
        fields = {"type", "command", "args", "env", "cwd"} if transport == "stdio" else {
            "type", "url", "headers"
        }
        if transport not in {"stdio", "http"} or set(server) - fields:
            raise ValueError(f"MCP {name}: unsupported transport or fields")
        required = "command" if transport == "stdio" else "url"
        if not isinstance(server.get(required), str) or not server[required].strip():
            raise ValueError(f"MCP {name}: missing {required}")
        if "args" in server and (not isinstance(server["args"], list) or
                                not all(isinstance(x, str) for x in server["args"])):
            raise ValueError(f"MCP {name}: args must be strings")
        for key in ("env", "headers"):
            values = server.get(key, {})
            if not isinstance(values, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in values.items()
            ):
                raise ValueError(f"MCP {name}: {key} must map strings to strings")
        if "cwd" in server and not isinstance(server["cwd"], str):
            raise ValueError(f"MCP {name}: cwd must be a string")
    return servers


def render_mcp(flavor, servers):
    converted = {}
    for name, source in servers.items():
        server = {k: v for k, v in source.items() if k != "type"}
        if flavor == "claude":
            server = dict(source)
        elif flavor == "codex":
            if "headers" in server:
                server["http_headers"] = server.pop("headers")
        elif flavor in {"qwen", "agy"}:
            if "url" in server:
                server["httpUrl" if flavor == "qwen" else "serverUrl"] = server.pop("url")
        elif flavor == "opencode":
            if source["type"] == "stdio":
                server["command"] = [server["command"], *server.pop("args", [])]
                server["type"] = "local"
                if "env" in server:
                    server["environment"] = server.pop("env")
            else:
                server["type"] = "remote"
        else:
            raise ValueError(f"Unknown MCP adapter: {flavor}")
        converted[name] = server
    if flavor == "codex":
        return toml_bytes({"mcp_servers": converted})
    if flavor == "opencode":
        return json_bytes({"$schema": "https://opencode.ai/config.json", "mcp": converted})
    return json_bytes({"mcpServers": converted})


def render_bundle(client, servers):
    profile = CLIENTS[client]
    files = {}
    limitations = [
        "Runtime settings, hooks, permissions and third-party plugins are not exported; Claude agent metadata is retained.",
        "Skill discovery is portable; tool names, context: fork and workflow behavior need client validation.",
        "Clients may also discover skills from other installed clients; avoid duplicate installations.",
        "Default user paths only; custom CODEX_HOME/XDG_CONFIG_HOME require manual path adaptation."
    ]

    def add(path, content, component, executable=False):
        if path in files:
            raise ValueError(f"Duplicate destination: {path}")
        files[path] = (content, {"component": component, "sha256": digest(content),
                                "mode": 0o700 if executable else 0o600})

    baseline = (ROOT / "AGENTS.md").read_text() + COMPATIBILITY
    if client == "claude":
        baseline += "\n" + (ROOT / "claude/CLAUDE.md").read_text().removeprefix("@AGENTS.md\n")
    if len(baseline) > profile.get("rules_limit", float("inf")):
        add(profile["baseline"], baseline.encode(), "rules")
        baseline = ("# AiSettings\n\nПеред началом каждой задачи прочитай полностью файл\n"
                    f"`~/{profile['baseline']}` и следуй общим правилам из него.\n"
                    "Это полный командный baseline; здесь оставлена ссылка из-за лимита\n"
                    "размера глобальных правил клиента. Личные инструкции добавляются отдельно.\n")
        limitations.append("Rules bootstrap requires the agent to read the full baseline file (12,000-character global-rule limit).")
    add(profile["rules"], baseline.encode(), "rules")

    skill_count = 0
    for directory in sorted((ROOT / "plugins").glob("*/skills/*")):
        skill = directory / "SKILL.md"
        if not skill.is_file() or directory.name in profile["excluded_skills"]:
            continue
        metadata = yaml.safe_load(skill.read_text().split("---", 2)[1])
        if metadata.get("name") != directory.name or not metadata.get("description"):
            raise ValueError(f"Invalid skill metadata: {directory.name}")
        skill_count += 1
        for source in sorted(directory.rglob("*")):
            if source.is_symlink():
                raise ValueError(f"Symlink in skill source: {source.relative_to(ROOT)}")
            if not source.is_file() or "__pycache__" in source.parts or ".bak" in source.name or source.suffix == ".pyc":
                continue
            content = source.read_bytes()
            if source.suffix in {".md", ".py", ".json", ".yaml", ".sh"}:
                content = content.replace(b"~/.claude/skills", f"~/{profile['skills']}".encode())
            destination = str(Path(profile["skills"]) / directory.name / source.relative_to(directory))
            add(destination, content, "skills", bool(source.stat().st_mode & 0o111))

    counts = {"rules": "bootstrap" if "baseline" in profile and profile["baseline"] in files else "inline",
              "skills": skill_count, "mcp": len(servers), "agents": 0, "commands": 0}
    for component in ("agents", "commands"):
        if component not in profile:
            limitations.append(f"Native {component} are not exported for {client}; invoke skills directly.")
            continue
        for source in sorted((ROOT / "plugins").glob(f"*/{component}/*.md")):
            add(str(Path(profile[component]) / source.name), source.read_bytes(), component)
            counts[component] += 1
    add(profile["mcp"], render_mcp(profile["mcp_format"], servers), "mcp")
    unconfigured = [name for name, server in servers.items()
                    if re.search(r"<[^>]+>|\bexample\.com\b", json.dumps(server))]
    manifest = {"version": 1, "client": client, "capabilities": counts,
                "excluded_skills": profile["excluded_skills"], "limitations": limitations,
                "unconfigured_mcp": unconfigured,
                "files": {path: info for path, (_, info) in files.items()}}
    return files, manifest
