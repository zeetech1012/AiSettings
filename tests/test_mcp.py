import json
import tomllib

import allure
import pytest

from settings_bundle import read_servers, render_mcp


@allure.epic("AiSettings")
@allure.feature("Native MCP configuration")
@allure.severity(allure.severity_level.CRITICAL)
class TestMcp:
    @allure.title("{client}: preserve stdio arguments and remote HTTP headers")
    @allure.story("Transport compatibility")
    @pytest.mark.parametrize("client,root,url_key", [
        ("claude", "mcpServers", "url"), ("codex", "mcp_servers", "url"),
        ("qwen", "mcpServers", "httpUrl"), ("agy", "mcpServers", "serverUrl"),
        ("opencode", "mcp", "url"),
    ])
    def test_transports(self, servers, client, root, url_key):
        with allure.step("Given: stdio arguments with spaces and HTTP headers with Unicode"):
            remote = servers['remote.quoted"name']
        with allure.step("When: render and parse native configuration"):
            raw = render_mcp(client, servers).decode()
            data = (tomllib.loads(raw) if client == "codex" else json.loads(raw))[root]
            allure.attach(raw, "Native MCP configuration", allure.attachment_type.TEXT)
        with allure.step("Then: transports, arguments and headers retain their meaning"):
            local = data["local"]
            http = data['remote.quoted"name']
            assert http[url_key] == remote["url"]
            assert http["http_headers" if client == "codex" else "headers"] == remote["headers"]
            if client == "opencode":
                assert local == {"type": "local", "command": ["node", "path with spaces/server.js"],
                                 "environment": servers["local"]["env"]}
                assert http["type"] == "remote"
            else:
                assert local["command"] == "node"
                assert local["args"] == ["path with spaces/server.js"]
                assert local["env"] == servers["local"]["env"]
                assert ("type" in local) == (client == "claude")

    @allure.title("Reject MCP input that cannot be converted without data loss")
    @allure.story("Input validation")
    @pytest.mark.parametrize("server", [
        {"type": "sse", "url": "https://fixture.test/events"},
        {"type": "stdio", "command": "node", "trust": True},
        {"type": "http", "url": ""},
        {"type": "stdio", "command": "node", "args": "--option"},
        {"type": "stdio", "command": "node", "env": {"OPTION": 1}},
        {"type": "http", "url": "https://fixture.test/mcp", "command": "node"},
    ])
    def test_invalid_sources(self, tmp_path, server):
        with allure.step("Given: an unsupported or invalid MCP entry"):
            source = tmp_path / "mcp.json"
            source.write_text(json.dumps({"mcpServers": {"invalid": server}}))
        with allure.step("When: validate the source before export"):
            with pytest.raises(ValueError, match="MCP invalid"):
                read_servers(source)
        with allure.step("Then: only the supplied fixture exists"):
            assert list(tmp_path.iterdir()) == [source]
