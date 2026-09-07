import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture
def servers():
    return {
        "local": {"type": "stdio", "command": "node", "args": ["path with spaces/server.js"],
                  "env": {"TEST_OPTION": "literal ${VALUE}"}},
        'remote.quoted"name': {"type": "http", "url": "https://fixture.test/mcp",
                               "headers": {"X-Test": "line one\nстрока два"}},
    }


@pytest.fixture
def bundle(tmp_path, servers):
    from aisettings import export

    export(tmp_path / "stage", ["codex"], servers)
    return tmp_path / "stage/codex"
