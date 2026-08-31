from __future__ import annotations

import os
import subprocess
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from src.ui import KluisApp, VaultBrowserTab, VaultScanWorker
from src.vault_engine import VaultEngine


@pytest.fixture
def mock_msgbox(monkeypatch: pytest.MonkeyPatch) -> Generator[MagicMock, None, None]:
    """Mock alle blocking QMessageBox dialogen."""
    mock_box = MagicMock()
    mock_box.exec.return_value = 0
    mock_box.clickedButton.return_value = None
    mock_box.addButton.return_value = MagicMock()
    monkeypatch.setattr(QMessageBox, "information", MagicMock(return_value=None))
    monkeypatch.setattr(QMessageBox, "warning", MagicMock(return_value=None))
    monkeypatch.setattr(QMessageBox, "critical", MagicMock(return_value=None))
    monkeypatch.setattr(QMessageBox, "question", MagicMock(return_value=QMessageBox.StandardButton.Yes))
    monkeypatch.setattr("src.ui.QMessageBox", MagicMock(return_value=mock_box))
    yield mock_box


class TestVaultEngineScanning:
    """Tests voor VaultEngine scan- en Keychain functies."""

    def test_get_all_keychain_vaults_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sample_dump = """
keychain: "/Users/test/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    "acct"<blob>="/Users/test/SecretVault.dmg"
    "svce"<blob>="SecureVault"
keychain: "/Users/test/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    "acct"<blob>="/Users/test/Documents/Work.sparsebundle"
    "svce"<blob>="SecureVault"
"""
        def mock_run(cmd, capture_output, text, timeout, check):
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=sample_dump, stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        vaults = VaultEngine.get_all_keychain_vaults()
        assert len(vaults) == 2
        assert "/Users/test/SecretVault.dmg" in vaults
        assert "/Users/test/Documents/Work.sparsebundle" in vaults

    def test_get_all_keychain_vaults_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def mock_run(cmd, capture_output, text, timeout, check):
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="error")

        monkeypatch.setattr(subprocess, "run", mock_run)
        vaults = VaultEngine.get_all_keychain_vaults()
        assert vaults == []

    def test_is_vault_encrypted_true_and_false(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        v_file = tmp_path / "test.dmg"
        v_file.write_text("dummy")

        def mock_run_success(cmd, capture_output, text, timeout, check):
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="encrypted: 1", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run_success)
        assert VaultEngine.is_vault_encrypted(str(v_file)) is True

        def mock_run_fail(cmd, capture_output, text, timeout, check):
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="not encrypted")

        monkeypatch.setattr(subprocess, "run", mock_run_fail)
        assert VaultEngine.is_vault_encrypted(str(v_file)) is False
        assert VaultEngine.is_vault_encrypted("/nonexistent/file.dmg") is False

    def test_scan_vaults_on_system_with_spotlight(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        v1 = tmp_path / "Kluis1.dmg"
        v1.write_text("content")
        v2 = tmp_path / "Kluis2.sparsebundle"
        v2.mkdir()

        engine = VaultEngine()

        def mock_run(cmd, capture_output, text, timeout, check):
            if cmd[0] == "security":
                return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
            if cmd[0] == "mdfind":
                out = f"{v1}\n{v2}\n"
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=out, stderr="")
            if cmd[0] == "hdiutil" and cmd[1] == "isencrypted":
                return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        progress_msgs: list[str] = []
        results = engine.scan_vaults_on_system(
            search_roots=[str(tmp_path)],
            filter_securevault_only=True,
            progress_callback=lambda m: progress_msgs.append(m),
        )

        assert len(results) == 2
        names = [r["name"] for r in results]
        assert "Kluis1.dmg" in names
        assert "Kluis2.sparsebundle" in names
        assert any("Spotlight" in msg for msg in progress_msgs)

    def test_scan_vaults_on_system_fallback_os_walk(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        sub = tmp_path / "SubFolder"
        sub.mkdir()
        v = sub / "Archive.dmg"
        v.write_text("content")

        engine = VaultEngine()

        def mock_run(cmd, capture_output, text, timeout, check):
            if cmd[0] == "security":
                return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
            if cmd[0] == "mdfind":
                return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")
            if cmd[0] == "hdiutil" and cmd[1] == "isencrypted":
                return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        results = engine.scan_vaults_on_system(
            search_roots=[str(tmp_path)],
            filter_securevault_only=True,
        )

        assert len(results) == 1
        assert results[0]["name"] == "Archive.dmg"
        assert results[0]["ext"] == ".dmg"


class TestVaultBrowserUI:
    """Tests voor VaultBrowserTab en VaultScanWorker."""

    def test_worker_execution(self, qtbot) -> None:
        worker = VaultScanWorker(search_roots=["/nonexistent"])
        with patch.object(VaultEngine, "scan_vaults_on_system", return_value=[{"name": "V1.dmg", "path": "/V1.dmg"}]):
            with qtbot.waitSignal(worker.finish_signal, timeout=2000) as blocker:
                worker.start()
            assert len(blocker.args[0]) == 1
            assert blocker.args[0][0]["name"] == "V1.dmg"

    def test_worker_error(self, qtbot) -> None:
        worker = VaultScanWorker(search_roots=["/test"])
        with patch.object(VaultEngine, "scan_vaults_on_system", side_effect=RuntimeError("Scan error")):
            with qtbot.waitSignal(worker.error_signal, timeout=2000) as blocker:
                worker.start()
            assert "Scan error" in blocker.args[0]

    def test_browser_tab_initial_state(self, qtbot) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        tab = app.tab_browser

        assert tab.chk_home.isChecked() is True
        assert tab.btn_scan.isEnabled() is True
        assert tab.btn_cancel_scan.isVisible() is False
        assert tab.btn_unlock.isEnabled() is False
        assert tab.btn_lock.isEnabled() is False
        assert tab.table.columnCount() == 6

    def test_browser_tab_populate_and_filter(self, qtbot) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        tab = app.tab_browser

        vaults = [
            {
                "path": "/Users/test/Work.dmg",
                "name": "Work.dmg",
                "ext": ".dmg",
                "size": "50 MB",
                "keychain": True,
                "mounted": False,
                "mount_point": "",
            },
            {
                "path": "/Users/test/Personal.sparsebundle",
                "name": "Personal.sparsebundle",
                "ext": ".sparsebundle",
                "size": "120 MB",
                "keychain": False,
                "mounted": True,
                "mount_point": "/Volumes/Personal",
            },
        ]

        tab.on_scan_finished(vaults)
        assert tab.table.rowCount() == 2
        assert "2 kluis(en) gevonden" in tab.lbl_count.text()

        # Test filter
        tab.inp_filter.setText("Work")
        assert tab.table.rowCount() == 1
        assert tab.table.item(0, 0).text() == "Work.dmg"

        tab.inp_filter.setText("")
        assert tab.table.rowCount() == 2

    def test_browser_tab_selection_and_keychain_autofill(self, qtbot, monkeypatch: pytest.MonkeyPatch) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        tab = app.tab_browser

        vaults = [
            {
                "path": "/Users/test/Work.dmg",
                "name": "Work.dmg",
                "ext": ".dmg",
                "size": "50 MB",
                "keychain": True,
                "mounted": False,
                "mount_point": "",
            }
        ]
        tab.on_scan_finished(vaults)

        monkeypatch.setattr(VaultEngine, "get_keychain_password", lambda p: "Secret123!" if p == "/Users/test/Work.dmg" else None)

        tab.table.selectRow(0)
        assert tab.btn_unlock.isEnabled() is True
        assert tab.btn_lock.isEnabled() is False
        assert tab.inp_pass.text() == "Secret123!"
        assert tab.chk_keychain.isChecked() is True

    def test_browser_tab_unlock_flow(self, qtbot, mock_msgbox, monkeypatch: pytest.MonkeyPatch) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        tab = app.tab_browser

        vaults = [
            {
                "path": "/Users/test/Work.dmg",
                "name": "Work.dmg",
                "ext": ".dmg",
                "size": "50 MB",
                "keychain": False,
                "mounted": False,
                "mount_point": "",
            }
        ]
        tab.on_scan_finished(vaults)
        tab.table.selectRow(0)
        tab.inp_pass.setText("CorrectPassword123")

        def mock_mount(self, p, pw):
            return True, "Success", "/Volumes/Work"

        monkeypatch.setattr(VaultEngine, "mount_vault", mock_mount)
        monkeypatch.setattr(VaultEngine, "get_active_mounts", lambda self: {"/Volumes/Work": "/Users/test/Work.dmg"})
        monkeypatch.setattr(subprocess, "run", MagicMock())

        tab.unlock_selected()

        # Check status update
        status_item = tab.table.item(0, 5)
        assert status_item is not None
        assert "Geopend" in status_item.text()

    def test_browser_tab_lock_flow(self, qtbot, mock_msgbox, monkeypatch: pytest.MonkeyPatch) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        tab = app.tab_browser

        vaults = [
            {
                "path": "/Users/test/OpenVault.dmg",
                "name": "OpenVault.dmg",
                "ext": ".dmg",
                "size": "50 MB",
                "keychain": False,
                "mounted": True,
                "mount_point": "/Volumes/OpenVault",
            }
        ]
        tab.on_scan_finished(vaults)
        tab.table.selectRow(0)

        def mock_unmount(self, mnt, force=False):
            return True, "Vault unmounted"

        monkeypatch.setattr(VaultEngine, "unmount_vault", mock_unmount)
        monkeypatch.setattr(VaultEngine, "get_active_mounts", lambda self: {})

        tab.lock_selected()
        status_item = tab.table.item(0, 5)
        assert status_item is not None
        assert "Vergrendeld" in status_item.text()

    def test_custom_folder_browse(self, qtbot, monkeypatch: pytest.MonkeyPatch) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        tab = app.tab_browser

        monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *a, **k: "/Users/test/CustomVaults")
        tab.browse_custom_folder()

        assert tab.custom_folder_path == "/Users/test/CustomVaults"
        assert not tab.lbl_custom_folder.isHidden()
