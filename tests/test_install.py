import json

import allure
import pytest

from aisettings import install
from settings_bundle import digest, json_bytes


def change_bundle(bundle, relative, text):
    target = bundle / "home" / relative
    target.write_text(text)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][relative]["sha256"] = digest(text.encode())
    manifest_path.write_bytes(json_bytes(manifest))


def snapshot(directory):
    return {str(p.relative_to(directory)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in directory.rglob("*") if p.is_file()}


@allure.epic("AiSettings")
@allure.feature("Managed installation")
@allure.severity(allure.severity_level.CRITICAL)
class TestInstall:
    @allure.title("Preview does not create the target home; repeat apply is a no-op")
    @allure.story("Installation lifecycle")
    def test_preview_and_idempotency(self, bundle, tmp_path):
        with allure.step("Given: a fresh installation target"):
            target = tmp_path / "home"
        with allure.step("When: preview installation"):
            report = install(bundle, target, ["rules", "skills", "mcp"])
        with allure.step("Then: the preview lists changes without writing files"):
            assert not report["conflicts"]
            assert not report["applied"]
            assert not target.exists()
        with allure.step("When: apply the same bundle twice"):
            assert install(bundle, target, ["rules", "skills", "mcp"], True)["applied"]
            before = snapshot(target)
            repeated = install(bundle, target, ["rules", "skills", "mcp"], True)
        with allure.step("Then: no content or modification time changes on the second apply"):
            assert repeated["applied"]
            assert all(item["action"] == "unchanged" for item in repeated["actions"])
            assert snapshot(target) == before

    @allure.title("A personal MCP config blocks all selected writes")
    @allure.story("Preserve personal settings")
    def test_personal_config_conflict(self, bundle, tmp_path):
        with allure.step("Given: an existing personal config"):
            target = tmp_path / "home"
            config = target / ".codex/config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('model = "personal-model"\n')
            before = snapshot(target)
        with allure.step("When: apply rules, skills and MCP together"):
            report = install(bundle, target, ["rules", "skills", "mcp"], True)
            allure.attach(json.dumps(report), "Preflight", allure.attachment_type.JSON)
        with allure.step("Then: no selected file is written"):
            assert not report["applied"]
            assert any(x["path"] == ".codex/config.toml" for x in report["conflicts"])
            assert snapshot(target) == before

    @allure.title("Managed baseline updates; subsequent local edits remain protected")
    @allure.story("Installation lifecycle")
    def test_managed_update_and_local_edit(self, bundle, tmp_path):
        with allure.step("Given: an installed baseline and a new bundle revision"):
            target = tmp_path / "home"
            relative = ".codex/AGENTS.md"
            assert install(bundle, target, ["rules"], True)["applied"]
            change_bundle(bundle, relative, "Updated baseline\n")
        with allure.step("When: update the managed baseline"):
            assert install(bundle, target, ["rules"], True)["applied"]
        with allure.step("Then: the new baseline is present"):
            assert (target / relative).read_text() == "Updated baseline\n"
        with allure.step("Given: the user edits that baseline locally"):
            (target / relative).write_text("Personal edits\n")
            before = snapshot(target)
        with allure.step("When: reapply the bundle"):
            report = install(bundle, target, ["rules"], True)
        with allure.step("Then: the local edits and installation state remain intact"):
            assert report["conflicts"]
            assert snapshot(target) == before

    @allure.title("Reject bundle tampering and destination symlinks before writing")
    @allure.story("Installation boundaries")
    @pytest.mark.parametrize("problem", ["tampering", "symlink", "traversal", "parent-file"])
    def test_boundaries(self, bundle, tmp_path, problem):
        with allure.step("Given: an unsafe bundle or target path"):
            target = tmp_path / "home"
            target.mkdir()
            outside = tmp_path / "outside"
            outside.mkdir()
            if problem == "tampering":
                (bundle / "home/.codex/AGENTS.md").write_text("Tampered\n")
            elif problem == "symlink":
                (target / ".codex").symlink_to(outside, target_is_directory=True)
            elif problem == "parent-file":
                (target / ".codex").write_text("Personal file\n")
            else:
                path = bundle / "manifest.json"
                manifest = json.loads(path.read_text())
                manifest["files"]["../outside/escaped"] = manifest["files"].pop(".codex/AGENTS.md")
                path.write_bytes(json_bytes(manifest))
            before = snapshot(target)
        with allure.step("When: attempt installation"):
            report = install(bundle, target, ["rules", "skills"], True)
        with allure.step("Then: no files are written inside or outside the target"):
            assert report["conflicts"]
            assert snapshot(target) == before
            assert not list(outside.iterdir())

    @allure.title("Remove obsolete managed files while retaining unselected components")
    @allure.story("Installation lifecycle")
    def test_prune_selected_components(self, bundle, tmp_path):
        with allure.step("Given: rules and skills installed from a previous bundle"):
            target = tmp_path / "home"
            assert install(bundle, target, ["rules", "skills"], True)["applied"]
            manifest_path = bundle / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            obsolete = ".agents/skills/occams-razor/SKILL.md"
            manifest["files"].pop(obsolete)
            manifest_path.write_bytes(json_bytes(manifest))
        with allure.step("When: update only skills"):
            report = install(bundle, target, ["skills"], True)
        with allure.step("Then: the obsolete managed skill is removed and rules remain"):
            assert report["applied"]
            assert not (target / obsolete).exists()
            assert (target / ".codex/AGENTS.md").exists()
