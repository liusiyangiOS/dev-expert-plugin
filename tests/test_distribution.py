"""离线结构检查与真实文件安装生命周期测试，不使用个人配置。"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from support import isolated_environment

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {"dev-expert-team-review", "dev-bugfix-pipeline", "dev-post-coding-pipeline", "dev-quick-fix"}
ROLES = {"dev-planner", "dev-developer", "dev-qa", "dev-debugger", "dev-researcher",
         "dev-code-reviewer", "dev-security-auditor", "dev-team-lead"}
INSTALL = ROOT / "packages/codex/install.py"


class PackageTests(unittest.TestCase):
    def test_independent_payloads(self):
        identities = set()
        for platform in ("claude", "codex"):
            root = ROOT / "packages" / platform
            for folder in ("agents", "skills"):
                for p in (root / folder).rglob("*"):
                    self.assertFalse(p.is_symlink(), p)
                    if not p.is_file():
                        continue
                    stat = p.stat()
                    self.assertEqual(stat.st_nlink, 1, p)
                    self.assertNotIn((stat.st_dev, stat.st_ino), identities, p)
                    identities.add((stat.st_dev, stat.st_ino))
                    if p.suffix not in (".md", ".toml", ".py", ".yaml", ".js"):
                        continue
                    text = p.read_text(encoding="utf-8")
                    self.assertNotIn("/Users/", text, p)
                    self.assertNotIn("/home/", text, p)
                    forbidden = (r"~?/\.agents/|~?/\.codex/" if platform == "claude"
                                 else r"~?/\.claude/|expert-claude-adapter|expert-claude-model-policy")
                    self.assertIsNone(re.search(forbidden, text), p)
            self.assertEqual({p.name for p in (root / "skills").iterdir()
                              if (p / "SKILL.md").exists()}, SKILLS)
            self.assertEqual({p.stem for p in (root / "agents").iterdir()}, ROLES)

    def test_metadata_and_resources(self):
        for platform in ("claude", "codex"):
            root = ROOT / "packages" / platform
            for p in (root / "agents").iterdir():
                if p.suffix == ".toml":
                    data = tomllib.loads(p.read_text(encoding="utf-8"))
                    self.assertEqual(data["name"], p.stem)
                    self.assertTrue(data["developer_instructions"])
                    self.assertNotIn("model", data)
                else:
                    text = p.read_text(encoding="utf-8")
                    self.assertTrue(text.startswith("---\n"))
                    self.assertIn(f"name: {p.stem}", text.split("---", 2)[1])
                    self.assertIn("effort:", text.split("---", 2)[1])
            for name in SKILLS:
                text = (root / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
                front = text.split("---", 2)[1]
                self.assertIn(f"name: {name}", front)
                self.assertIn("description:", front)
            for folder in ("agents", "skills"):
                for p in (root / folder).rglob("*"):
                    if p.suffix not in (".md", ".toml"):
                        continue
                    text = p.read_text(encoding="utf-8")
                    for link in re.findall(r"\]\(([^)\s]+)\)", text):
                        if ":" in link or link.startswith("#"):
                            continue
                        self.assertTrue((p.parent / link.split("#")[0]).exists(), (p, link))
                    for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", text):
                        # Template role filenames are covered by the eight roles above.
                        self.assertTrue((root / rel).exists(), (p, rel))
                    for rel in re.findall(r"~/.agents/skills/([\w./-]+)", text):
                        self.assertTrue((root / "skills" / rel).exists(), (p, rel))

    def test_marketplace_routes_to_claude_only(self):
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        entry, = market["plugins"]
        self.assertEqual(entry["source"], "./packages/claude")
        plugin = json.loads((ROOT / entry["source"] / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(entry["name"], plugin["name"])
        self.assertFalse((ROOT / "workflows").exists())
        self.assertFalse((ROOT / "agents").exists())


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="expert-install-test-")
        self.home = Path(self.temp.name).resolve()
        self.env = isolated_environment(self.home)

    def tearDown(self):
        self.temp.cleanup()

    def run_install(self, command="install", *options, ok=True):
        p = subprocess.run([sys.executable, str(INSTALL), command, "--home", str(self.home),
                            *options], env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode == 0, ok, p.stdout + p.stderr)
        return p

    def test_lifecycle_preserves_unrelated_data(self):
        for name in (".codex/config.toml", ".claude/settings.json",
                     ".agents/skills/dev-shared/unrelated.md",
                     ".cache/codex-expert-workflows/expert-model-cache.json"):
            p = self.home / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("sentinel", encoding="utf-8")
        self.run_install("install", "--dry-run")
        self.assertFalse((self.home / ".codex/agents").exists())
        self.run_install()
        self.run_install("check")
        self.run_install()  # Idempotent update.
        self.run_install("uninstall")
        for p in self.home.rglob("*"):
            if p.is_file() and p.name in ("config.toml", "settings.json", "unrelated.md",
                                         "expert-model-cache.json"):
                self.assertEqual(p.read_text(encoding="utf-8"), "sentinel")
        self.assertFalse((self.home / ".codex/agents/dev-developer.toml").exists())

    def test_conflict_is_preflighted_and_backed_up(self):
        p = self.home / ".agents/skills/dev-quick-fix/SKILL.md"
        p.parent.mkdir(parents=True)
        p.write_text("original customization", encoding="utf-8")
        self.run_install(ok=False)
        self.assertFalse((self.home / ".codex/agents/dev-developer.toml").exists())
        self.run_install("install", "--replace")
        saved = list((self.home / ".codex/expert-team/backups").rglob("SKILL.md"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(encoding="utf-8"), "original customization")
        p.write_text("new customization", encoding="utf-8")
        self.run_install("check", ok=False)
        self.run_install(ok=False)
        self.run_install("uninstall", ok=False)
        self.assertEqual(p.read_text(encoding="utf-8"), "new customization")
        self.run_install("uninstall", "--replace")

    def test_symlinks_are_never_followed(self):
        outside = self.home / "outside"
        outside.mkdir()
        try:
            (self.home / ".agents").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows 未授予符号链接权限；目录联接和硬链接另行测试")
            raise
        self.run_install(ok=False)
        self.assertEqual(list(outside.iterdir()), [])
        (self.home / ".agents").unlink()

    def test_hardlinks_are_never_overwritten(self):
        outside = self.home / "outside"
        outside.mkdir()
        p = self.home / ".codex/agents/dev-developer.toml"
        p.parent.mkdir(parents=True, exist_ok=True)
        original = outside / "original"
        original.write_text("untouched", encoding="utf-8")
        os.link(original, p)
        self.run_install("install", "--replace", ok=False)
        self.assertEqual(original.read_text(encoding="utf-8"), "untouched")

    @unittest.skipUnless(os.name == "nt", "仅 Windows 有目录联接")
    def test_windows_junction_is_rejected(self):
        outside = self.home / "outside"
        outside.mkdir()
        link = self.home / ".agents"
        result = subprocess.run(
            [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "mklink", "/J",
             str(link), str(outside)], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            self.run_install("install", "--replace", ok=False)
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            os.rmdir(link)

    def test_corrupt_manifest_cannot_delete_outside_payload(self):
        self.run_install()
        manifest = self.home / ".codex/expert-team/install-manifest.json"
        manifest.write_text(json.dumps({"files": {"../../outside": "hash"}}), encoding="utf-8")
        self.run_install("uninstall", "--replace", ok=False)
        self.assertTrue((self.home / ".codex/agents/dev-developer.toml").exists())

    def test_write_failure_rolls_back_payload_and_state(self):
        spec = importlib.util.spec_from_file_location("installer", INSTALL)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        args = module.argparse.Namespace(home=self.home, explicit_home=True,
                                         command="install", replace=False, dry_run=False)
        real = module.atomic_write
        count = 0

        def fail_once(path, data):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError("simulated disk failure")
            real(path, data)

        module.atomic_write = fail_once
        with self.assertRaises(OSError):
            module.run(args)
        self.assertFalse(any(p.is_file() for p in self.home.rglob("*")))

    def test_standalone_package_can_update_without_other_platform(self):
        package = self.home / "standalone-source"
        shutil.copytree(ROOT / "packages/codex", package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        installer = package / "install.py"
        target = self.home / "isolated-user"

        def apply(command):
            result = subprocess.run(
                [sys.executable, str(installer), command, "--home", str(target)],
                env=self.env, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)

        apply("install")
        src = package / "agents/dev-developer.toml"
        original = src.read_bytes()
        src.write_bytes(original + b"\n# package update fixture\n")
        apply("install")
        apply("check")
        self.assertEqual((target / ".codex/agents/dev-developer.toml").read_bytes(), src.read_bytes())
        backups = list((target / ".codex/expert-team/backups").rglob("dev-developer.toml"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertFalse((target / ".claude").exists())
        apply("uninstall")

    def test_unicode_home_and_source_paths(self):
        package = self.home / "源码 空格"
        shutil.copytree(ROOT / "packages/codex", package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        target = self.home / "使用者 空格"
        env = isolated_environment(target)
        env["PYTHONIOENCODING"] = "cp1252"  # CLI must still emit UTF-8.
        for command in ("install", "check", "uninstall"):
            result = subprocess.run(
                [sys.executable, str(package / "install.py"), command],
                env=env, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("\ufffd", result.stdout)
        self.assertFalse((target / ".codex/agents/dev-developer.toml").exists())

    def test_unicode_manifest_is_read_as_utf8(self):
        self.run_install()
        path = self.home / ".codex/expert-team/install-manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["note"] = "安装备注"
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        self.run_install("check")
        self.run_install("uninstall")


if __name__ == "__main__":
    unittest.main()
