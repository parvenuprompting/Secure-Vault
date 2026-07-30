from __future__ import annotations

import os
import threading
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from src.vault_engine import VaultEngine


class TestVaultEngineValidation:
    """Tests voor pad- en rechtenvalidatie van VaultEngine."""

    def test_validate_paths_success(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        dest.mkdir()

        engine.validate_paths(str(src), str(dest))

    def test_validate_paths_nonexistent_source(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        dest = tmp_path / "dest"
        dest.mkdir()
        with pytest.raises(ValueError, match="Bronmap bestaat niet"):
            engine.validate_paths(str(tmp_path / "nonexistent"), str(dest))

    def test_validate_paths_source_is_file(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        src_file = tmp_path / "file.txt"
        src_file.write_text("hello")
        dest = tmp_path / "dest"
        dest.mkdir()

        with pytest.raises(ValueError, match="Gekozen bron is geen map"):
            engine.validate_paths(str(src_file), str(dest))

    def test_validate_paths_nonexistent_dest(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        src = tmp_path / "src"
        src.mkdir()

        with pytest.raises(ValueError, match="Doelmap bestaat niet"):
            engine.validate_paths(str(src), str(tmp_path / "nonexistent_dest"))

    def test_validate_paths_dest_is_file(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        src = tmp_path / "src"
        src.mkdir()
        dest_file = tmp_path / "dest_file.txt"
        dest_file.write_text("hello")

        with pytest.raises(ValueError, match="Gekozen doel is geen map"):
            engine.validate_paths(str(src), str(dest_file))

    def test_validate_paths_unwritable_dest(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        dest.mkdir()

        monkeypatch.setattr(os, "access", lambda path, mode: False if mode == os.W_OK else True)

        with pytest.raises(PermissionError, match="Geen schrijfrechten"):
            engine.validate_paths(str(src), str(dest))


class TestVaultEngineSizeAndCleanup:
    """Tests voor grootteberekening en opschoning."""

    def test_calculate_size_mb_with_files(self, engine: VaultEngine, sample_dir: str) -> None:
        size = engine.calculate_size_mb(sample_dir)
        assert size >= 100

    def test_calculate_size_mb_ignores_symlinks_and_oserror(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "src_sym"
        src.mkdir()
        real_file = src / "real.txt"
        real_file.write_text("data")

        # Symlink
        symlink_file = src / "link.txt"
        try:
            os.symlink(str(real_file), str(symlink_file))
        except (AttributeError, OSError):
            pass

        orig_getsize = os.path.getsize

        def fake_getsize(path: str) -> int:
            if "real.txt" in path:
                raise OSError("Access denied simulation")
            return orig_getsize(path)

        monkeypatch.setattr(os.path, "getsize", fake_getsize)

        size = engine.calculate_size_mb(str(src))
        assert size == 100

    def test_cleanup_file_and_directory(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "remove_file.txt"
        f.write_text("to be deleted")
        d = tmp_path / "remove_dir"
        d.mkdir()

        engine.cleanup(str(f))
        assert not f.exists()

        engine.cleanup(str(d))
        assert not d.exists()

        # Non-existent cleanup should not raise
        engine.cleanup("/nonexistent/file/path")


class TestPasswordStrength:
    """Tests voor check_password_strength."""

    @pytest.mark.parametrize(
        "password,expected_valid,score_range",
        [
            ("", False, (0, 0)),
            ("short", False, (1, 35)),
            ("abcdefgh", True, (36, 49)),
            ("Abcdefg1", True, (75, 100)),
            ("P@ssw0rd2026!", True, (75, 100)),
        ],
    )
    def test_password_strength_boundaries(
        self, password: str, expected_valid: bool, score_range: tuple[int, int]
    ) -> None:
        valid, msg, score = VaultEngine.check_password_strength(password)
        assert valid == expected_valid
        assert score_range[0] <= score <= score_range[1]
        assert isinstance(msg, str)


class TestCreateVault:
    """Tests voor create_vault en subprocess interactie."""

    @pytest.mark.parametrize("format_type,expected_ext", [("UDZO", ".dmg"), ("UDRW", ".dmg"), ("UDSB", ".sparsebundle")])
    def test_create_vault_formats_success(
        self,
        engine: VaultEngine,
        sample_dir: str,
        tmp_path: pytest.TempPathFactory,
        format_type: str,
        expected_ext: str,
    ) -> None:
        dest = tmp_path / "out"
        dest.mkdir()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("success", "")

        logs: list[str] = []
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            success, dmg_path = engine.create_vault(
                sample_dir,
                str(dest),
                "MyTestVault",
                "StrongP@ss123!",
                format_type=format_type,
                progress_callback=logs.append,
            )

        assert success is True
        assert dmg_path.endswith(expected_ext)
        assert mock_popen.called
        cmd_args = mock_popen.call_args[0][0]
        assert "-format" in cmd_args
        assert format_type in cmd_args

    def test_create_vault_cancellation(self, engine: VaultEngine, sample_dir: str, tmp_path: pytest.TempPathFactory) -> None:
        dest = tmp_path / "out"
        dest.mkdir()

        cancel_event = threading.Event()
        cancel_event.set()

        success, msg = engine.create_vault(
            sample_dir,
            str(dest),
            "CancelVault",
            "StrongP@ss123!",
            cancel_event=cancel_event,
        )

        assert success is False
        assert "geannuleerd" in msg

    def test_create_vault_cancellation_during_execution(self, engine: VaultEngine, sample_dir: str, tmp_path: pytest.TempPathFactory) -> None:
        dest = tmp_path / "out"
        dest.mkdir()

        cancel_event = threading.Event()

        mock_proc = MagicMock()
        mock_proc.poll.side_effect = [None, None]
        mock_proc.communicate.return_value = ("", "")

        def set_cancel() -> None:
            cancel_event.set()

        timer = threading.Timer(0.1, set_cancel)
        timer.start()

        with patch("subprocess.Popen", return_value=mock_proc):
            success, msg = engine.create_vault(
                sample_dir,
                str(dest),
                "CancelMidVault",
                "StrongP@ss123!",
                cancel_event=cancel_event,
            )

        timer.cancel()
        assert success is False
        assert "geannuleerd" in msg
        assert mock_proc.terminate.called

    def test_create_vault_hdiutil_failure(self, engine: VaultEngine, sample_dir: str, tmp_path: pytest.TempPathFactory) -> None:
        dest = tmp_path / "out"
        dest.mkdir()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = ("", "hdiutil: create failed - invalid pass")

        with patch("subprocess.Popen", return_value=mock_proc):
            success, msg = engine.create_vault(
                sample_dir,
                str(dest),
                "FailVault",
                "StrongP@ss123!",
            )

        assert success is False
        assert "hdiutil fout" in msg

    def test_create_vault_trailing_slash_and_unicode(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        src = tmp_path / "unicode_mâp/"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("ok", "")

        with patch("subprocess.Popen", return_value=mock_proc):
            success, path = engine.create_vault(
                str(src),
                str(dest),
                "Unicodë Kluîs ✨",
                "StrongP@ss123!",
            )

        assert success is True
        assert "Unicodë Kluîs ✨" in path


class TestMountAndUnmount:
    """Tests voor mount_vault, unmount_vault en get_active_mounts."""

    def test_mount_vault_nonexistent(self, engine: VaultEngine) -> None:
        success, msg, mnt = engine.mount_vault("/nonexistent/vault.dmg", "pass")
        assert success is False
        assert "niet gevonden" in msg
        assert mnt == ""

    @patch("os.path.exists", return_value=True)
    def test_mount_vault_success(self, mock_exists: MagicMock, engine: VaultEngine) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("/dev/disk2", "")

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            success, msg, mnt = engine.mount_vault("/fake/vault.dmg", "Secret123!")

        assert success is True
        assert mnt.startswith("/Volumes/BeveiligdVolume-")
        assert mnt in engine.get_active_mounts()

    @patch("os.path.exists", return_value=True)
    def test_mount_vault_exception_handling(self, mock_exists: MagicMock, engine: VaultEngine) -> None:
        with patch("subprocess.Popen", side_effect=RuntimeError("Subprocess failed to launch")):
            success, msg, mnt = engine.mount_vault("/fake/vault.dmg", "Secret123!")

        assert success is False
        assert "Fout bij koppelen" in msg
        assert mnt == ""

    @patch("os.path.exists", return_value=True)
    def test_mount_vault_wrong_password(self, mock_exists: MagicMock, engine: VaultEngine) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = ("", "hdiutil: attach failed - checksum incorrect")

        with patch("subprocess.Popen", return_value=mock_proc):
            success, msg, mnt = engine.mount_vault("/fake/vault.dmg", "WrongPass")

        assert success is False
        assert "Kon kluis niet ontgrendelen" in msg
        assert mnt == ""

    def test_unmount_vault_nonexistent_mountpoint(self, engine: VaultEngine) -> None:
        success, msg = engine.unmount_vault("/Volumes/NonExistentVolume-1234")
        assert success is True
        assert "al ontkoppeld" in msg

    def test_unmount_vault_success(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        mnt = str(tmp_path / "mount_vol")
        os.makedirs(mnt)
        engine._active_mounts[mnt] = "/fake/vault.dmg"

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stderr = ""

        with patch("subprocess.run", return_value=mock_res) as mock_run:
            success, msg = engine.unmount_vault(mnt)

        assert success is True
        assert "veilig vergrendeld" in msg
        assert mnt not in engine.get_active_mounts()

    def test_unmount_vault_busy_and_forced(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        mnt = str(tmp_path / "mount_vol")
        os.makedirs(mnt)
        engine._active_mounts[mnt] = "/fake/vault.dmg"

        mock_res_busy = MagicMock()
        mock_res_busy.returncode = 1
        mock_res_busy.stderr = "Resource busy"

        with patch("subprocess.run", return_value=mock_res_busy):
            success, msg = engine.unmount_vault(mnt, force=False)

        assert success is False
        assert "Resource busy" in msg
        assert mnt in engine.get_active_mounts()

        mock_res_ok = MagicMock()
        mock_res_ok.returncode = 0
        mock_res_ok.stderr = ""

        with patch("subprocess.run", return_value=mock_res_ok):
            success_f, msg_f = engine.unmount_vault(mnt, force=True)

        assert success_f is True
        assert mnt not in engine.get_active_mounts()

    def test_get_active_mounts_cleans_stale_mounts(self, engine: VaultEngine, tmp_path: pytest.TempPathFactory) -> None:
        valid_mnt = str(tmp_path / "valid_mnt")
        os.makedirs(valid_mnt)
        stale_mnt = "/Volumes/BeveiligdVolume-stale123"

        engine._active_mounts[valid_mnt] = "/path/vault1.dmg"
        engine._active_mounts[stale_mnt] = "/path/vault2.dmg"

        active = engine.get_active_mounts()
        assert valid_mnt in active
        assert stale_mnt not in active
