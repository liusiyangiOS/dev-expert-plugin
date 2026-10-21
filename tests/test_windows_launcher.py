"""Windows entry point regression tests; POSIX installation is unchanged."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from support import isolated_environment

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "packages/codex/install.ps1"


@unittest.skipUnless(os.name == "nt", "Windows PowerShell entry point")
class WindowsLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="expert-windows-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "用户 空格"
        self.env = isolated_environment(self.home)
        self.env["EXPERT_PYTHON"] = sys.executable
        self.shell = shutil.which("powershell.exe")
        self.assertIsNotNone(self.shell)

    def run_launcher(self, *args, launcher=LAUNCHER, ok=True):
        result = subprocess.run(
            [self.shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(launcher), *args], cwd=self.base, env=self.env,
            capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_standalone_unicode_path_lifecycle_without_py_or_path(self):
        package = self.base / "独立 包"
        shutil.copytree(ROOT / "packages/codex", package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.env["PATH"] = str(self.base / "empty-path")
        launcher = package / "install.ps1"
        self.run_launcher("install", "--dry-run", launcher=launcher)
        self.assertFalse((self.home / ".codex/expert-team/install-manifest.json").exists())
        for command in ("install", "check", "install", "uninstall"):
            self.run_launcher(command, "--home", str(self.home), launcher=launcher)
        self.assertFalse((self.home / ".codex/agents/dev.toml").exists())

    def test_installer_error_exit_code_and_replace_are_forwarded(self):
        target = self.home / ".codex/agents/dev.toml"
        target.parent.mkdir(parents=True)
        target.write_text("original", encoding="utf-8")
        self.run_launcher("install", ok=False)
        self.assertEqual(target.read_text(encoding="utf-8"), "original")
        self.run_launcher("install", "--replace")
        self.run_launcher("check")
        backups = list((self.home / ".codex/expert-team/backups").rglob("dev.toml"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "original")

    def test_invalid_explicit_python_has_actionable_error_and_no_writes(self):
        self.env["EXPERT_PYTHON"] = str(self.base / "missing.exe")
        result = self.run_launcher("install", ok=False)
        self.assertIn("Python 3.11+", result.stderr)
        self.assertIn("https://www.python.org/downloads/windows/", result.stderr)
        self.assertFalse((self.home / ".agents").exists())

    def test_discovery_skips_failed_candidate_and_restores_environment(self):
        # Simulate a broken/too-old launcher before a working Python, without
        # changing the machine's PATH, registry, or installed interpreters.
        harness = self.base / "probe.ps1"
        harness.write_text("\n".join([
            ". $env:EXPERT_TEST_LAUNCHER",
            "function Get-ExpertPythonCandidates {",
            "  [pscustomobject]@{Path = $env:EXPERT_TEST_BAD; Prefix = @()}",
            "  [pscustomobject]@{Path = $env:EXPERT_PYTHON; Prefix = @()}",
            "}",
            "$env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'original'",
            "$env:PYLAUNCHER_ALLOW_INSTALL = 'original'",
            "$found = Find-ExpertPython",
            "if ($found -ne $env:EXPERT_PYTHON) { exit 2 }",
            "if ($env:PYTHON_MANAGER_AUTOMATIC_INSTALL -ne 'original') { exit 3 }",
            "if ($env:PYLAUNCHER_ALLOW_INSTALL -ne 'original') { exit 4 }",
        ]), encoding="ascii")
        bad = self.base / "old-python.ps1"
        bad.write_text("$global:LASTEXITCODE = 1\nWrite-Output $env:EXPERT_PYTHON\n",
                       encoding="ascii")
        self.env["EXPERT_TEST_BAD"] = str(bad)
        self.env["EXPERT_TEST_LAUNCHER"] = str(LAUNCHER)
        self.run_launcher(launcher=harness)

    def test_python_on_path_without_py(self):
        self.env.pop("EXPERT_PYTHON")
        self.env["PATH"] = str(Path(sys.executable).parent)
        result = self.run_launcher("install", "--dry-run")
        self.assertIn(sys.executable, result.stdout)


if __name__ == "__main__":
    unittest.main()
