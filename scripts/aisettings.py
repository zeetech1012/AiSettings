#!/usr/bin/env python3
"""Export AiSettings or preview/apply an exported bundle to a user home."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from settings_bundle import (
    CLIENTS, COMPONENTS, ROOT, digest, json_bytes, read_servers, render_bundle,
)


def safe_path(root, relative):
    if root.exists() and not root.is_dir():
        raise ValueError("Destination root is not a directory")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts or "\\" in relative:
        raise ValueError(f"Invalid relative path: {relative}")
    destination = root / path
    for item in (destination, *destination.parents):
        if item == root:
            break
        if item.is_symlink():
            raise ValueError(f"Refusing symlink: {relative}")
        if item != destination and item.exists() and not item.is_dir():
            raise ValueError(f"Parent is not a directory: {relative}")
    return destination


def write_atomic(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def export(output, clients, servers):
    output = output.expanduser().resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Export outside the repository, for example to a fresh /tmp directory")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Export destination must be absent or empty; use a fresh directory")
    bundles = {client: render_bundle(client, servers) for client in clients}
    for client, (files, manifest) in bundles.items():
        bundle = output / client
        for relative, (content, info) in files.items():
            write_atomic(safe_path(bundle / "home", relative), content, info["mode"])
        write_atomic(bundle / "manifest.json", json_bytes(manifest))
    return {client: {"bundle": str(output / client), "capabilities": manifest["capabilities"],
                     "excluded_skills": manifest["excluded_skills"],
                     "unconfigured_mcp": manifest["unconfigured_mcp"],
                     "limitations": manifest["limitations"]}
            for client, (_, manifest) in bundles.items()}


def install(bundle, target_home, components, apply=False):
    bundle = bundle.expanduser().resolve()
    target_home = target_home.expanduser().resolve()
    if target_home == ROOT or ROOT in target_home.parents:
        raise ValueError("The installation target must be a user home outside this repository")
    manifest = json.loads((bundle / "manifest.json").read_text())
    client = manifest["client"]
    if manifest["version"] != 1 or client not in CLIENTS:
        raise ValueError("Unsupported bundle manifest")
    state_relative = f".local/share/aisettings/{client}.json"
    state_path = safe_path(target_home, state_relative)
    previous = json.loads(state_path.read_text()) if state_path.exists() else {}
    next_state = dict(previous)
    desired = {path: info for path, info in manifest["files"].items()
               if info["component"] in components}
    actions, conflicts, changes = [], [], []
    if "mcp" in components and manifest["unconfigured_mcp"]:
        conflicts.append({"path": CLIENTS[client]["mcp"],
                          "reason": "Configure MCP servers or export with --servers: " +
                                    ", ".join(manifest["unconfigured_mcp"])})
    for relative in sorted(desired.keys() | {
        path for path, info in previous.items() if info["component"] in components
    }):
        if relative == state_relative:
            raise ValueError("Bundle cannot overwrite its installation state")
        try:
            target = safe_path(target_home, relative)
            if target.exists() and not target.is_file():
                raise ValueError("Destination is not a regular file")
            current = digest(target.read_bytes()) if target.exists() else None
            info = desired.get(relative)
            old = previous.get(relative)
            content = None
            if info:
                source = safe_path(bundle / "home", relative)
                content = source.read_bytes()
                if digest(content) != info["sha256"] or info["mode"] not in {0o600, 0o700}:
                    raise ValueError("Bundle integrity check failed; export it again")
            if info and current == info["sha256"]:
                action = "unchanged"
                if old:
                    next_state[relative] = info
            elif current is not None and (not old or current != old["sha256"]):
                raise ValueError("Existing personal or locally modified file; merge manually")
            elif info:
                action = "update" if current is not None else "create"
                changes.append((relative, content, info["mode"], current))
                next_state[relative] = info
            else:
                action = "delete" if current is not None else "unchanged"
                if current is not None:
                    changes.append((relative, None, None, current))
                next_state.pop(relative, None)
            actions.append({"path": relative, "action": action})
        except (ValueError, OSError) as error:
            conflicts.append({"path": relative, "reason": str(error)})
    report = {"client": client, "applied": False, "actions": actions, "conflicts": conflicts}
    if conflicts or not apply:
        return report
    for relative, content, mode, expected in changes:
        path = safe_path(target_home, relative)
        current = digest(path.read_bytes()) if path.exists() else None
        if current != expected:
            raise ValueError(f"Destination changed during installation: {relative}")
        if content is None:
            path.unlink()
        else:
            write_atomic(path, content, mode)
    if next_state != previous:
        write_atomic(state_path, json_bytes(next_state))
    report["applied"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("clients", help="List native paths and supported clients")
    render = commands.add_parser("export", help="Build native files in a fresh staging directory")
    render.add_argument("--client", choices=[*CLIENTS, "all"], default="all")
    render.add_argument("--output", required=True, type=Path)
    render.add_argument("--mcp-source", type=Path, default=ROOT / "mcp/mcp.json")
    render.add_argument("--servers", nargs="+", help="Export only these MCP servers")
    deploy = commands.add_parser("install", help="Preview by default; --apply writes managed files")
    deploy.add_argument("--bundle", type=Path, required=True)
    deploy.add_argument("--home", type=Path, default=Path.home())
    deploy.add_argument("--components", nargs="+", choices=COMPONENTS, default=["rules", "skills"])
    deploy.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "clients":
            result = CLIENTS
        elif args.command == "export":
            clients = list(CLIENTS) if args.client == "all" else [args.client]
            result = export(args.output, clients, read_servers(args.mcp_source, args.servers))
        else:
            result = install(args.bundle, args.home, args.components, args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("conflicts") else 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
