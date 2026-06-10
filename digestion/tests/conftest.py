import os
from pathlib import Path

import pytest

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())


def pytest_addoption(parser):
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="Overwrite snapshot files with the current extractor output.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: requires GITHUB_ACCESS_TOKEN and a git-initialised Lean repo (slow)",
    )


def pytest_collection_modifyitems(config, items):
    skip = pytest.mark.skip(
        reason="Set GITHUB_ACCESS_TOKEN and run 'git init' in the test repo first"
    )
    for item in items:
        if "integration" in item.keywords and not os.getenv("GITHUB_ACCESS_TOKEN"):
            item.add_marker(skip)
