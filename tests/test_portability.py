import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from support import isolated_environment
from audit_paths import PERSONAL, audit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("portable_installer", ROOT / "packages/codex/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PortabilityTests(unittest.TestCase):
    def test_manifest_rejects_windows_escape_and_ambiguous_paths(self):
        for name in (
            ".agents/skills/dev-quick-fix/../other", ".agents//skills/dev-quick-fix/SKILL.md",
            ".agents/skills/dev-quick-fix/SKILL.md:stream",
            ".agents/skills/dev-quick-fix/C:/other",
            ".agents/skills/dev-quick-fix/NUL.txt",
            ".agents/skills/dev-quick-fix/CON", ".agents/skills/dev-quick-fix/COM1.txt",
            ".agents/skills/dev-quick-fix/SKILL.md.", ".agents/skills/dev-quick-fix/SKILL.md ",
            r".agents\skills\dev-quick-fix\SKILL.md", r"C:\Users\other\SKILL.md",
            r"\\server\share\SKILL.md",
        ):
            with self.subTest(name=name):
                self.assertFalse(installer.safe_relative(name))
        self.assertTrue(installer.safe_relative(".agents/skills/dev-quick-fix/SKILL.md"))
        self.assertTrue(installer.safe_relative(".codex/agents/dev-developer.toml"))

    def test_windows_reparse_tag_is_rejected_on_python311(self):
        path = Path("fixture")
        with mock.patch.object(type(path), "is_symlink", return_value=False), \
                mock.patch.object(type(path), "lstat",
                                  return_value=SimpleNamespace(st_reparse_tag=0xA0000003)):
            with self.assertRaises(ValueError):
                installer.check_path(path)

    def test_child_environment_isolated_on_both_home_conventions(self):
        with tempfile.TemporaryDirectory(prefix="expert-env-") as folder:
            user = Path(folder).resolve() / "测试 用户"
            source = {
                "PATH": os.environ["PATH"], "SystemRoot": "system sentinel",
                "USERPROFILE": "real profile", "HOME": "real home",
                "APPDATA": "real appdata", "CODEX_HOME": "real codex",
                "ANTHROPIC_API_KEY": "do-not-copy", "OPENAI_API_KEY": "do-not-copy",
                "HTTP_PROXY": "do-not-copy",
            }
            env = isolated_environment(user, source)
            self.assertEqual(env["SystemRoot"], "system sentinel")
            self.assertEqual(env["HOME"], str(user))
            self.assertEqual(env["USERPROFILE"], str(user))
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("ANTHROPIC_API_KEY", env)
            self.assertNotIn("HTTP_PROXY", env)
            for key in ("CODEX_HOME", "CLAUDE_CONFIG_DIR", "APPDATA", "LOCALAPPDATA",
                        "TMP", "TEMP", "XDG_CACHE_HOME"):
                self.assertTrue(Path(env[key]).is_relative_to(user), key)
            # Use actual OS launch prerequisites, not the synthetic sentinel.
            actual_env = isolated_environment(user)
            result = subprocess.run(
                [sys.executable, "-c",
                 "import json; from pathlib import Path; print(json.dumps(str(Path.home())))"],
                env=actual_env, capture_output=True, encoding="utf-8", check=True)
            self.assertEqual(Path(json.loads(result.stdout)), user)

    def test_path_audit_distinguishes_author_path_from_portable_reference(self):
        for name in ("/Users/alice/.codex/agents", "/home/alice/.agents/skills",
                     r"C:\Users\alice\.codex", "/mnt/c/Users/alice/.claude"):
            self.assertRegex(name, PERSONAL)
        for name in ("~/.agents/skills", "${CLAUDE_PLUGIN_ROOT}/skills",
                     "$env:USERPROFILE\\.codex", "%USERPROFILE%\\.claude",
                     "C:/Users/<user>/.codex", "../dev-shared/expert-model-policy.md"):
            self.assertIsNone(PERSONAL.search(name))
        self.assertFalse(any(r["personal_path_references"] for r in audit()))


if __name__ == "__main__":
    unittest.main()
