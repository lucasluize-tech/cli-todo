"""Unit tests for the updater module."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from todo.updater import check_latest_version, parse_version, run_pipx_upgrade


class TestParseVersion:
    def test_simple_version(self):
        assert parse_version("0.2.0") == (0, 2, 0)

    def test_major_version(self):
        assert parse_version("1.0.0") == (1, 0, 0)

    def test_double_digits(self):
        assert parse_version("1.12.3") == (1, 12, 3)


class TestCheckLatestVersion:
    @patch("todo.updater.urlopen")
    def test_returns_latest_version(self, mock_urlopen: MagicMock):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"info": {"version": "0.4.0"}}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        assert check_latest_version() == "0.4.0"

    @patch("todo.updater.urlopen")
    def test_network_error_returns_none(self, mock_urlopen: MagicMock):
        mock_urlopen.side_effect = OSError("No internet")

        assert check_latest_version() is None

    @patch("todo.updater.urlopen")
    def test_invalid_json_returns_none(self, mock_urlopen: MagicMock):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        assert check_latest_version() is None


class TestRunPipxUpgrade:
    @patch("todo.updater.shutil.which", return_value="/usr/bin/pipx")
    @patch("todo.updater.subprocess.run")
    def test_upgrade_success(self, mock_run: MagicMock, mock_which: MagicMock):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        success, _msg = run_pipx_upgrade(force=False)
        assert success is True
        mock_run.assert_called_once_with(["pipx", "upgrade", "todo-cli-tool"], check=False)

    @patch("todo.updater.shutil.which", return_value="/usr/bin/pipx")
    @patch("todo.updater.subprocess.run")
    def test_upgrade_force(self, mock_run: MagicMock, mock_which: MagicMock):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        success, _msg = run_pipx_upgrade(force=True)
        assert success is True
        mock_run.assert_called_once_with(
            ["pipx", "upgrade", "--force", "todo-cli-tool"], check=False
        )

    @patch("todo.updater.shutil.which", return_value=None)
    def test_pipx_not_found(self, mock_which: MagicMock):
        success, msg = run_pipx_upgrade(force=False)
        assert success is False
        assert "pipx not found" in msg

    @patch("todo.updater.shutil.which", return_value="/usr/bin/pipx")
    @patch("todo.updater.subprocess.run")
    def test_upgrade_failure(self, mock_run: MagicMock, mock_which: MagicMock):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stderr="error")

        success, _msg = run_pipx_upgrade(force=False)
        assert success is False
