from __future__ import annotations

import os
from typing import Generator
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QMimeData, QUrl, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QFileDialog, QMessageBox

from src.ui import KluisApp, ModernInput


@pytest.fixture(autouse=True)
def mock_qmessagebox(mocker: pytest.FixtureRequest) -> Generator[MagicMock, None, None]:
    """
    Autouse fixture dat alle synchrone QMessageBox methodes mockt
    om te voorkomen dat de GUI testsuite blijft hangen op geopende modals.
    """
    mock_box = MagicMock()
    mock_box.exec.return_value = QMessageBox.StandardButton.Ok
    mock_box.clickedButton.return_value = None

    mocker.patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok)
    mocker.patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok)
    mocker.patch.object(QMessageBox, "critical", return_value=QMessageBox.StandardButton.Ok)
    mocker.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes)
    mocker.patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Ok)
    yield mock_box


class TestKluisAppUI:
    """GUI testsuite voor KluisApp en diens tabbladen via pytest-qt (qtbot)."""

    def test_app_initialization(self, qtbot: pytest.FixtureRequest) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        assert app.windowTitle().startswith("SecureVault")
        assert app.tabs.count() == 2
        assert app.tabs.tabText(0) == "➕ Nieuwe Kluis"
        assert app.tabs.tabText(1) == "🔓 Kluis Beheren"

    def test_modern_input_components(self, qtbot: pytest.FixtureRequest) -> None:
        inp = ModernInput("TEST INPUT", is_password=True, tooltip="Tooltip text")
        qtbot.addWidget(inp)

        assert inp.lbl.text() == "TEST INPUT"
        assert inp.input.toolTip() == "Tooltip text"

        # Toggle password visibility
        inp.toggle_password_visibility()
        assert inp.btn_toggle.text() == "🙈"
        inp.toggle_password_visibility()
        assert inp.btn_toggle.text() == "👁"

        # Border status styling
        inp.set_border_status("valid")
        inp.set_border_status("invalid")
        inp.set_border_status(None)

    def test_browsing_dialogs(self, qtbot: pytest.FixtureRequest, mocker: pytest.FixtureRequest, tmp_path: pytest.TempPathFactory) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        tab_create = app.tab_create
        tab_manage = app.tab_manage

        fake_folder = str(tmp_path / "picked_folder")
        fake_vault = str(tmp_path / "picked_vault.dmg")

        mocker.patch.object(QFileDialog, "getExistingDirectory", return_value=fake_folder)
        tab_create.browse_source()
        assert tab_create.inp_source.text() == fake_folder

        tab_create.browse_dest()
        assert tab_create.inp_dest.text() == fake_folder

        mocker.patch.object(QFileDialog, "getOpenFileName", return_value=(fake_vault, ""))
        tab_manage.browse_vault_file()
        assert tab_manage.inp_vault_file.text() == fake_vault

    def test_show_help_dialog(self, qtbot: pytest.FixtureRequest, mocker: pytest.FixtureRequest) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        mock_exec = mocker.patch.object(QMessageBox, "exec")
        app.show_help()
        assert mock_exec.called

    def test_password_strength_and_matching(self, qtbot: pytest.FixtureRequest) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        tab = app.tab_create

        # Type te kort wachtwoord
        qtbot.keyClicks(tab.inp_pass.input, "short")
        assert tab.strength_bar.value() < 50
        assert "minimaal 8 tekens" in tab.lbl_strength.text()

        # Wis en type sterk wachtwoord
        tab.inp_pass.input.clear()
        qtbot.keyClicks(tab.inp_pass.input, "StrongP@ss2026!")
        assert tab.strength_bar.value() >= 75
        assert "Sterk" in tab.lbl_strength.text()

        # Bevestig wachtwoord mismatch
        qtbot.keyClicks(tab.inp_pass_confirm.input, "WrongMatch!")
        assert "niet overeen" in tab.lbl_match.text()

        # Bevestig wachtwoord match
        tab.inp_pass_confirm.input.clear()
        qtbot.keyClicks(tab.inp_pass_confirm.input, "StrongP@ss2026!")
        assert "komen overeen" in tab.lbl_match.text()

    def test_start_process_validation_triggers_warning(self, qtbot: pytest.FixtureRequest, mocker: pytest.FixtureRequest) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        tab = app.tab_create
        mock_warn = mocker.patch.object(QMessageBox, "warning")

        # Velden leeg -> start klik
        qtbot.mouseClick(tab.btn_start, Qt.MouseButton.LeftButton)
        mock_warn.assert_called_once()
        assert "Invoer incompleet" in mock_warn.call_args[0][1]

    def test_async_worker_execution_flow(self, qtbot: pytest.FixtureRequest, mocker: pytest.FixtureRequest, tmp_path: pytest.TempPathFactory) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        dest.mkdir()

        tab = app.tab_create
        tab.inp_source.setText(str(src))
        tab.inp_dest.setText(str(dest))
        tab.inp_name.setText("TestVault")
        tab.inp_pass.setText("StrongP@ss2026!")
        tab.inp_pass_confirm.setText("StrongP@ss2026!")

        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("created", "")
        mocker.patch("subprocess.Popen", return_value=mock_proc)

        # Klik start
        qtbot.mouseClick(tab.btn_start, Qt.MouseButton.LeftButton)

        # UI state tijdens run
        assert not tab.btn_start.isEnabled()
        assert not tab.btn_cancel.isHidden()

        # Wacht op worker finish via qtbot
        with qtbot.waitSignal(tab.worker.finish_signal, timeout=5000):
            pass

        # UI herstel na finish
        assert tab.btn_start.isEnabled()
        assert tab.btn_cancel.isHidden()

    def test_cancel_button_flow(self, qtbot: pytest.FixtureRequest, mocker: pytest.FixtureRequest, tmp_path: pytest.TempPathFactory) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        dest.mkdir()

        tab = app.tab_create
        tab.inp_source.setText(str(src))
        tab.inp_dest.setText(str(dest))
        tab.inp_name.setText("CancelVault")
        tab.inp_pass.setText("StrongP@ss2026!")
        tab.inp_pass_confirm.setText("StrongP@ss2026!")

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.communicate.return_value = ("", "")
        mocker.patch("subprocess.Popen", return_value=mock_proc)

        qtbot.mouseClick(tab.btn_start, Qt.MouseButton.LeftButton)
        assert not tab.btn_cancel.isHidden()

        # Klik annuleren
        qtbot.mouseClick(tab.btn_cancel, Qt.MouseButton.LeftButton)
        assert "Bezig met opruimen" in tab.btn_cancel.text()

        with qtbot.waitSignal(tab.worker.finish_signal, timeout=5000):
            pass

        assert tab.worker.cancel_event.is_set()

    def test_drag_and_drop_handling(self, qtbot: pytest.FixtureRequest, tmp_path: pytest.TempPathFactory, mocker: pytest.FixtureRequest) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()

        # 1. Drop gewone map -> naar Tab 0 (Nieuwe Kluis)
        folder = tmp_path / "drag_folder"
        folder.mkdir()

        mime1 = QMimeData()
        mime1.setUrls([QUrl.fromLocalFile(str(folder))])
        drop_evt1 = QDropEvent(app.rect().center(), Qt.DropAction.CopyAction, mime1, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)

        app.dropEvent(drop_evt1)
        assert app.tabs.currentIndex() == 0
        assert app.tab_create.inp_source.text() == str(folder)

        # 2. Drop .dmg kluisbestand -> naar Tab 1 (Kluis Beheren)
        dmg_file = tmp_path / "my_vault.dmg"
        dmg_file.write_text("dummy")

        mime2 = QMimeData()
        mime2.setUrls([QUrl.fromLocalFile(str(dmg_file))])
        drop_evt2 = QDropEvent(app.rect().center(), Qt.DropAction.CopyAction, mime2, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)

        app.dropEvent(drop_evt2)
        assert app.tabs.currentIndex() == 1
        assert app.tab_manage.inp_vault_file.text() == str(dmg_file)

        # 3. Drop .sparsebundle pakket (map) -> naar Tab 1 (Kluis Beheren)
        bundle_dir = tmp_path / "my_vault.sparsebundle"
        bundle_dir.mkdir()

        mime3 = QMimeData()
        mime3.setUrls([QUrl.fromLocalFile(str(bundle_dir))])
        drop_evt3 = QDropEvent(app.rect().center(), Qt.DropAction.CopyAction, mime3, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)

        app.dropEvent(drop_evt3)
        assert app.tabs.currentIndex() == 1
        assert app.tab_manage.inp_vault_file.text() == str(bundle_dir)

        # 4. Drop los bestand (geen kluis/geen map) -> waarschuwing
        file_path = tmp_path / "regular.txt"
        file_path.write_text("hello")
        mime4 = QMimeData()
        mime4.setUrls([QUrl.fromLocalFile(str(file_path))])
        drop_evt4 = QDropEvent(app.rect().center(), Qt.DropAction.CopyAction, mime4, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)

        mock_warn = mocker.patch.object(QMessageBox, "warning")
        app.dropEvent(drop_evt4)
        mock_warn.assert_called_once()

    def test_manage_tab_unlock_and_lock_flow(self, qtbot: pytest.FixtureRequest, mocker: pytest.FixtureRequest, tmp_path: pytest.TempPathFactory) -> None:
        app = KluisApp()
        qtbot.addWidget(app)
        app.show()
        app.tabs.setCurrentIndex(1)

        tab = app.tab_manage
        dmg = tmp_path / "test.dmg"
        dmg.write_text("vault content")

        tab.inp_vault_file.setText(str(dmg))
        tab.inp_vault_pass.setText("Secret123!")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("/dev/disk2", "")
        mocker.patch("subprocess.Popen", return_value=mock_proc)
        mocker.patch("subprocess.run")
        mocker.patch("os.path.exists", return_value=True)

        # Klik ontgrendelen
        qtbot.mouseClick(tab.btn_unlock, Qt.MouseButton.LeftButton)

        # Verifieer dat mount in lijst staat
        assert tab.mounts_list.count() == 1
        item = tab.mounts_list.item(0)
        assert "test.dmg" in item.text()

        # Selecteer item en klik vergrendelen
        tab.mounts_list.setCurrentItem(item)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value.returncode = 0

        qtbot.mouseClick(tab.btn_lock_selected, Qt.MouseButton.LeftButton)
        assert mock_run.called
