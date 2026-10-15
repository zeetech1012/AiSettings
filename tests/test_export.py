import json
import subprocess
import sys

import allure
import pytest

from aisettings import export, install
from settings_bundle import CLIENTS, ROOT, read_servers, render_bundle


@allure.epic("AiSettings")
@allure.feature("Reproducible client bundles")
@allure.severity(allure.severity_level.NORMAL)
class TestExport:
    @allure.title("{client}: export the full baseline, compatible skills and portable paths")
    @allure.story("Client support")
    @pytest.mark.parametrize("client,count", [("claude", 25), ("codex", 24), ("agy", 23),
                                             ("qwen", 24), ("opencode", 23)])
    def test_client_bundles(self, servers, client, count):
        with allure.step("Given: the tracked baseline and source skill catalog"):
            baseline = (ROOT / "AGENTS.md").read_text()
            profile = CLIENTS[client]
        with allure.step("When: render the same client twice"):
            first = render_bundle(client, servers)
            second = render_bundle(client, servers)
            files, manifest = first
            allure.attach(json.dumps(manifest["capabilities"]), "Capabilities", allure.attachment_type.JSON)
        with allure.step("Then: the bundle is deterministic and respects client limitations"):
            assert first == second
            assert manifest["capabilities"]["skills"] == count
            rules = files[profile.get("baseline", profile["rules"])][0].decode()
            assert baseline in rules
            if client == "agy":
                assert len(files[profile["rules"]][0].decode()) <= 12000
                assert profile["baseline"] in files[profile["rules"]][0].decode()
            if client != "claude":
                assert all("git-guardrails-claude-code" not in path for path in files)
                assert all(b"~/.claude/skills" not in data for data, _ in files.values())
            harness = json.loads(files[profile["skills"] + "/agent-harness/assets/harnesses/project-management.json"][0])
            assert all(item["path"].startswith("~/" + profile["skills"] + "/") for item in harness["skills"])

    @allure.title("Unconfigured MCP templates cannot be installed")
    @allure.story("Private configuration")
    def test_placeholders_block_mcp(self, tmp_path):
        with allure.step("Given: an export of the complete public MCP template"):
            stage = tmp_path / "stage"
            export(stage, ["codex"], read_servers(ROOT / "mcp/mcp.json"))
        with allure.step("When: attempt to install MCP with unresolved placeholders"):
            report = install(stage / "codex", tmp_path / "home", ["mcp"], True)
        with allure.step("Then: installation refuses and names the unconfigured servers"):
            assert not report["applied"]
            assert "jira" in report["conflicts"][0]["reason"]
            assert not (tmp_path / "home").exists()

    @allure.title("CLI exports all five clients; reusing a nonempty output fails safely")
    @allure.story("Command line workflow")
    def test_cli(self, tmp_path):
        with allure.step("Given: a fresh output directory and an explicit public MCP selection"):
            stage = tmp_path / "stage"
            command = [sys.executable, str(ROOT / "scripts/aisettings.py"), "export",
                       "--client", "all", "--output", str(stage), "--servers", "context7"]
        with allure.step("When: export and then attempt to reuse that directory"):
            first = subprocess.run(command, capture_output=True, text=True, timeout=30)
            repeated = subprocess.run(command, capture_output=True, text=True, timeout=30)
        with allure.step("Then: all five bundles are present and the second export is refused"):
            assert first.returncode == 0, first.stderr
            assert set(json.loads(first.stdout)) == {"claude", "codex", "agy", "qwen", "opencode"}
            assert repeated.returncode == 2
            assert "absent or empty" in repeated.stderr
