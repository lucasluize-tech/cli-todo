"""Check PyPI for updates and upgrade via pipx."""

from __future__ import annotations

import json
import shutil
import subprocess
from urllib.request import urlopen

PYPI_URL = "https://pypi.org/pypi/todo-cli-tool/json"


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple of ints."""
    return tuple(int(part) for part in version.split("."))


def check_latest_version() -> str | None:
    """Fetch the latest version from PyPI. Returns None on failure."""
    try:
        with urlopen(PYPI_URL, timeout=5) as response:
            data = json.loads(response.read())
            return str(data["info"]["version"])
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def run_pipx_upgrade(*, force: bool) -> tuple[bool, str]:
    """Run pipx upgrade. Returns (success, message)."""
    if shutil.which("pipx") is None:
        return False, "pipx not found -- install manually with: pipx install todo-cli-tool"

    cmd = ["pipx", "upgrade"]
    if force:
        cmd.append("--force")
    cmd.append("todo-cli-tool")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        return False, "Upgrade failed. Run 'pipx upgrade todo-cli-tool' manually."
    return True, "Upgrade complete!"
