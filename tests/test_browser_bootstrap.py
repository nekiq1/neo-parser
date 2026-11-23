"""Unit tests for the on-demand Chromium installer (no network/browser needed)."""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import yandex


class _PlaywrightContext:
    def __init__(self, executable):
        self.chromium = SimpleNamespace(executable_path=str(executable))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_chromium_installer_skips_download_when_browser_exists():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        browser = root / "chrome.exe"
        browser.write_bytes(b"already-installed")
        with patch.object(yandex, "_browsers_path", return_value=root), \
             patch("playwright.sync_api.sync_playwright", return_value=_PlaywrightContext(browser)), \
             patch("subprocess.run") as run:
            result = yandex.ensure_chromium_installed()
        assert result == browser
        run.assert_not_called()


def test_chromium_installer_downloads_only_full_browser():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        browser = root / "chrome.exe"
        node, cli = root / "node.exe", root / "cli.js"
        node.write_bytes(b"node")
        cli.write_text("// test cli", encoding="utf-8")
        contexts = [_PlaywrightContext(browser), _PlaywrightContext(browser)]

        def install(*_args, **_kwargs):
            browser.write_bytes(b"installed")
            return SimpleNamespace(returncode=0, stdout="installed", stderr="")

        with patch.object(yandex, "_browsers_path", return_value=root), \
             patch("playwright.sync_api.sync_playwright", side_effect=contexts), \
             patch("playwright._impl._driver.compute_driver_executable", return_value=(str(node), str(cli))), \
             patch("subprocess.run", side_effect=install) as run:
            result = yandex.ensure_chromium_installed()

        assert result == browser
        args, kwargs = run.call_args
        assert args[0][-3:] == ["install", "chromium", "--no-shell"]
        assert kwargs["env"]["PLAYWRIGHT_BROWSERS_PATH"] == str(root)
        assert kwargs["timeout"] == 900
