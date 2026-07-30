from __future__ import annotations

import os
import sys
from typing import Generator
from unittest.mock import MagicMock

import pytest

# Offscreen mode for Qt in CI/CD and headless environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.vault_engine import VaultEngine


@pytest.fixture
def engine() -> Generator[VaultEngine, None, None]:
    """Fixture dat een schone VaultEngine instantie geeft met geresette actieve mounts."""
    VaultEngine._active_mounts.clear()
    eng = VaultEngine()
    yield eng
    VaultEngine._active_mounts.clear()


@pytest.fixture
def mock_popen(mocker: pytest.FixtureRequest) -> MagicMock:
    """Fixture dat subprocess.Popen mockt en een succesvolle default afhandeling biedt."""
    mock_process = MagicMock()
    mock_process.poll.return_value = 0
    mock_process.returncode = 0
    mock_process.communicate.return_value = ("created volume", "")

    # Access pytest-mock mocker fixture via pytest_mock
    mocker_fixture = sys.modules["pytest_mock"].MockerFixture if "pytest_mock" in sys.modules else None
    
    # We patch subprocess.Popen directly
    import subprocess
    patcher = mocker_fixture.patch("subprocess.Popen") if mocker_fixture else None
    if patcher:
        patched = patcher.start()
        patched.return_value = mock_process
        yield patched
        patcher.stop()
    else:
        from unittest.mock import patch
        with patch("subprocess.Popen", return_value=mock_process) as p:
            yield p


@pytest.fixture
def mock_run() -> Generator[MagicMock, None, None]:
    """Fixture dat subprocess.run mockt met succesvolle returncode 0."""
    from unittest.mock import patch
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "OK"
    mock_res.stderr = ""
    with patch("subprocess.run", return_value=mock_res) as p:
        yield p


@pytest.fixture
def sample_dir(tmp_path: pytest.TempPathFactory) -> str:
    """Maakt een representatieve bronmappenstructuur aan voor testdoeleinden."""
    source_dir = tmp_path / "source_folder"
    source_dir.mkdir()

    sub_dir = source_dir / "sub_folder"
    sub_dir.mkdir()

    file1 = source_dir / "document.txt"
    file1.write_text("Confidential data content", encoding="utf-8")

    file2 = sub_dir / "image.png"
    file2.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)

    return str(source_dir)
