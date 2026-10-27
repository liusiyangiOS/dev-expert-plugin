"""3.1 共享资源的完整分发与受管更新边界；不以文案匹配代替行为评估。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from support import isolated_environment

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = frozenset({
    "expert-performance.md", "expert-performance-record.md", "expert-ui-verification.md",
})


class PerformanceDistributionTests(unittest.TestCase):
    @contextlib.contextmanager
    def package(self, host):
        with tempfile.TemporaryDirectory(prefix="expert-performance-") as folder:
            base = Path(folder).resolve()
            source = base / "源码 空格" / host
            shutil.copytree(ROOT / "packages" / host, source,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            spec = importlib.util.spec_from_file_location("performance_installer_" + host,
                                                         source / "install.py")
            installer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(installer)
            home = base / "使用者 空格"
            home.mkdir()
            with mock.patch.dict("os.environ", isolated_environment(home), clear=True):
                yield installer, home, source

    def apply(self, installer, home, command="install", **kwargs):
        args = SimpleNamespace(home=home, explicit_home=True, command=command,
                               replace=False, dry_run=False)
        for key, value in kwargs.items():
            setattr(args, key, value)
        with contextlib.redirect_stdout(io.StringIO()):
            installer.run(args)

    def state(self, home, host):
        return home / (".codex" if host == "codex" else ".claude") / "expert-team/install-manifest.json"

    def snapshot(self, home):
        return {p.relative_to(home).as_posix(): p.read_bytes()
                for p in home.rglob("*") if p.is_file()}

    def seed_managed_3_0(self, installer, home, host):
        # A constructed managed-3.0 fixture exercises update semantics without
        # depending on Git or pretending to be a frozen historical release.
        previous = {name: data for name, data in installer.payload().items()
                    if Path(name).name not in RESOURCES}
        role = next(name for name in previous if "/agents/dev-developer." in name)
        previous[role] = b"previous managed role fixture\n"
        for name, data in previous.items():
            target = home / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest = {"schema_version": 1, "package": installer.PACKAGE_NAME,
                    "version": "3.0.0",
                    "files": {name: installer.digest(data) for name, data in previous.items()}}
        state = self.state(home, host)
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return previous, manifest, role

    def test_complete_standalone_payload_installs_resources(self):
        for host in ("codex", "claude"):
            with self.subTest(host=host), self.package(host) as (installer, home, source):
                self.assertEqual(set(installer.REQUIRED_SHARED), RESOURCES)
                self.assertEqual(installer.VERSION, "3.1.0")
                self.apply(installer, home)
                self.apply(installer, home, "check")
                prefix = ".agents" if host == "codex" else ".claude"
                for name in RESOURCES:
                    relative = "skills/dev-shared/" + name
                    data = (source / relative).read_bytes()
                    if host == "claude":
                        data = installer.render_personal(relative, data)
                    self.assertEqual((home / prefix / relative).read_bytes(), data)
                other = home / (".claude" if host == "codex" else ".codex")
                self.assertFalse(any(p.is_file() for p in other.rglob("*")))
                self.apply(installer, home, "uninstall")
                self.assertFalse(self.state(home, host).exists())
                self.assertTrue(all(not (home / prefix / "skills/dev-shared" / name).exists()
                                    for name in RESOURCES))

    def test_each_missing_required_resource_blocks_before_write(self):
        for host in ("codex", "claude"):
            for name in RESOURCES:
                with self.subTest(host=host, missing=name), self.package(host) as (installer, home, source):
                    (source / "skills/dev-shared" / name).unlink()
                    with self.assertRaises(ValueError):
                        self.apply(installer, home)
                    self.assertEqual(self.snapshot(home), {})

    def test_managed_3_0_update_preserves_backup_and_unrelated_data(self):
        for host in ("codex", "claude"):
            with self.subTest(host=host), self.package(host) as (installer, home, source):
                previous, manifest, role = self.seed_managed_3_0(installer, home, host)
                sentinel = home / "未受管 空格.txt"
                sentinel.write_text("保留", encoding="utf-8")
                self.apply(installer, home)
                self.apply(installer, home, "check")
                state = json.loads(self.state(home, host).read_text(encoding="utf-8"))
                self.assertEqual(state["version"], installer.VERSION)
                self.assertEqual(state["files"], {n: installer.digest(b)
                                                  for n, b in installer.payload().items()})
                backups = list(self.state(home, host).parent.glob("backups/*"))
                self.assertEqual(len(backups), 1)
                saved = json.loads((backups[0] / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["previous_install_manifest"], manifest)
                self.assertEqual((backups[0] / "files" / role).read_bytes(), previous[role])
                self.apply(installer, home)
                self.apply(installer, home, "check")
                self.assertEqual(json.loads(self.state(home, host).read_text(encoding="utf-8")), state)
                self.apply(installer, home, "uninstall")
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "保留")

    def test_update_keeps_user_modifications_and_new_resource_conflicts(self):
        for host in ("codex", "claude"):
            for conflict in ("existing", "new"):
                with self.subTest(host=host, conflict=conflict), self.package(host) as (installer, home, source):
                    _, _, role = self.seed_managed_3_0(installer, home, host)
                    prefix = ".agents" if host == "codex" else ".claude"
                    target = home / (role if conflict == "existing" else
                                     prefix + "/skills/dev-shared/expert-performance.md")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("用户定制", encoding="utf-8")
                    before = self.snapshot(home)
                    with self.assertRaises(ValueError):
                        self.apply(installer, home)
                    self.assertEqual(self.snapshot(home), before)
                    self.apply(installer, home, replace=True)
                    self.apply(installer, home, "check")
                    backups = self.state(home, host).parent.glob("backups/*/files/" + target.relative_to(home).as_posix())
                    self.assertEqual([p.read_text(encoding="utf-8") for p in backups], ["用户定制"])

    def test_failed_update_restores_previous_payload_and_manifest(self):
        for host in ("codex", "claude"):
            with self.subTest(host=host), self.package(host) as (installer, home, source):
                self.seed_managed_3_0(installer, home, host)
                before = self.snapshot(home)
                real_write = installer.atomic_write
                count = 0

                def fail_once(path, data):
                    nonlocal count
                    if "backups" not in path.relative_to(home).parts:
                        count += 1
                    if count == 2:
                        count += 1
                        raise OSError("simulated update failure")
                    real_write(path, data)

                with mock.patch.object(installer, "atomic_write", side_effect=fail_once):
                    with self.assertRaises(OSError):
                        self.apply(installer, home)
                after = {n: b for n, b in self.snapshot(home).items()
                         if "backups" not in Path(n).parts}
                self.assertEqual(after, before)
                self.assertTrue(list(self.state(home, host).parent.glob("backups/*/manifest.json")))


if __name__ == "__main__":
    unittest.main()
