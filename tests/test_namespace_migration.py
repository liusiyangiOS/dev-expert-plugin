"""真实 2.0.1 个人安装到当前 dev 命名空间的独立迁移回归。"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from support import isolated_environment

ROOT = Path(__file__).resolve().parents[1]
# Frozen complete payloads, including Claude's historical personal rendering.
# Tests need neither Git history nor the other host's distributed package.
LEGACY = json.loads((ROOT / 'tests/fixtures/legacy-2.0.1.json').read_text(
    encoding='utf-8'))['packages']


def load_installer(host, package=None):
    package = package or ROOT / 'packages' / host
    spec = importlib.util.spec_from_file_location('namespace_installer_' + host,
                                                 package / 'install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NamespaceMigrationTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, host):
        with tempfile.TemporaryDirectory(prefix='expert-namespace-') as folder:
            home = Path(folder).resolve() / '使用者 空格'
            home.mkdir()
            installer = load_installer(host)
            yield installer, home

    def state(self, home, host):
        return home / ('.codex' if host == 'codex' else '.claude') / 'expert-team/install-manifest.json'

    def seed_legacy(self, installer, home, host):
        files = {name: data.encode('utf-8') for name, data in LEGACY[host].items()}
        self.assertEqual(len(files), 28 if host == 'codex' else 20)
        for name, data in files.items():
            target = home / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest = {
            'schema_version': 1, 'package': installer.PACKAGE_NAME,
            'version': '2.0.1',
            'files': {name: installer.digest(data) for name, data in files.items()},
        }
        state = self.state(home, host)
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        return files, manifest

    def run_installer(self, installer, home, command='install', replace=False, dry_run=False):
        args = SimpleNamespace(home=home, explicit_home=True, command=command,
                               replace=replace, dry_run=dry_run)
        with contextlib.redirect_stdout(io.StringIO()):
            installer.run(args)

    def snapshot(self, home, backups=True):
        return {p.relative_to(home).as_posix(): p.read_bytes()
                for p in home.rglob('*') if p.is_file()
                and (backups or 'backups' not in p.relative_to(home).parts)}

    def test_complete_legacy_upgrade_cleans_and_backs_up_only_managed_files(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host), self.fixture(host) as (installer, home):
                files, old = self.seed_legacy(installer, home, host)
                old_state = self.state(home, host).read_bytes()
                self.run_installer(installer, home)
                desired = installer.payload()
                state = json.loads(self.state(home, host).read_text(encoding='utf-8'))
                self.assertEqual(state['version'], installer.VERSION)
                self.assertEqual(state['files'], {n: installer.digest(b) for n, b in desired.items()})
                self.assertTrue(all(installer.safe_relative(n) for n in state['files']))
                for name in set(files) - set(desired):
                    self.assertFalse((home / name).exists(), name)
                backups = list(self.state(home, host).parent.glob('backups/*'))
                self.assertEqual(len(backups), 1)
                backup = backups[0]
                info = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
                self.assertEqual(info['previous_install_manifest'], old)
                self.assertEqual(old_state, json.dumps(old, ensure_ascii=False, indent=2).encode())
                for name, before in files.items():
                    if desired.get(name) != before:
                        self.assertEqual((backup / 'files' / name).read_bytes(), before)
                self.run_installer(installer, home, 'check')
                self.run_installer(installer, home, 'uninstall')
                self.assertFalse(self.state(home, host).exists())
                self.assertTrue(all(not (home / name).exists() for name in desired))

    def test_new_name_conflict_blocks_before_cleanup_or_partial_writes(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host), self.fixture(host) as (installer, home):
                self.seed_legacy(installer, home, host)
                name = next(n for n in installer.payload() if '/dev-quick-fix/' in n)
                target = home / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('既有同名自定义技能', encoding='utf-8')
                before = self.snapshot(home)
                with self.assertRaisesRegex(ValueError, '保留已有或被修改'):
                    self.run_installer(installer, home)
                self.assertEqual(self.snapshot(home), before)
                self.run_installer(installer, home, replace=True)
                self.run_installer(installer, home, 'check')
                saved = list(self.state(home, host).parent.glob('backups/*/files/' + name))
                self.assertEqual(len(saved), 1)
                self.assertEqual(saved[0].read_text(encoding='utf-8'), '既有同名自定义技能')

    def test_unmanaged_old_names_are_preserved_during_fresh_install_and_upgrade(self):
        for host in ('codex', 'claude'):
            for upgrade in (False, True):
                with self.subTest(host=host, upgrade=upgrade), self.fixture(host) as (installer, home):
                    name = next(n for n in LEGACY[host] if '/agents/dev.' in n)
                    if upgrade:
                        _, old = self.seed_legacy(installer, home, host)
                        del old['files'][name]
                        self.state(home, host).write_text(json.dumps(old), encoding='utf-8')
                    target = home / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('属于用户的旧同名角色', encoding='utf-8')
                    self.run_installer(installer, home, replace=True)
                    self.assertEqual(target.read_text(encoding='utf-8'), '属于用户的旧同名角色')
                    self.run_installer(installer, home, 'uninstall', replace=True)
                    self.assertEqual(target.read_text(encoding='utf-8'), '属于用户的旧同名角色')

    def test_modified_legacy_file_blocks_until_replace_then_is_backed_up(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host), self.fixture(host) as (installer, home):
                files, _ = self.seed_legacy(installer, home, host)
                name = next(n for n in files if '/_shared/' in n)
                (home / name).write_text('用户修改的共用规则', encoding='utf-8')
                before = self.snapshot(home)
                for command in ('install', 'uninstall'):
                    with self.assertRaisesRegex(ValueError, '保留已有或被修改'):
                        self.run_installer(installer, home, command)
                    self.assertEqual(self.snapshot(home), before)
                self.run_installer(installer, home, replace=True)
                self.assertFalse((home / name).exists())
                saved = list(self.state(home, host).parent.glob('backups/*/files/' + name))
                self.assertEqual(len(saved), 1)
                self.assertEqual(saved[0].read_text(encoding='utf-8'), '用户修改的共用规则')

    def test_write_or_manifest_failure_restores_old_installation(self):
        for host in ('codex', 'claude'):
            for fail_manifest in (False, True):
                with self.subTest(host=host, manifest=fail_manifest), self.fixture(host) as (installer, home):
                    self.seed_legacy(installer, home, host)
                    before = self.snapshot(home)
                    original = installer.atomic_write
                    calls = 0
                    failed = False

                    def fail_once(path, data):
                        nonlocal calls, failed
                        if 'backups' not in path.relative_to(home).parts:
                            calls += 1
                            should_fail = path == self.state(home, host) if fail_manifest else calls == 2
                            if should_fail and not failed:
                                failed = True
                                raise OSError('迁移磁盘失败 fixture')
                        return original(path, data)

                    with mock.patch.object(installer, 'atomic_write', side_effect=fail_once):
                        with self.assertRaisesRegex(OSError, '迁移磁盘失败'):
                            self.run_installer(installer, home)
                    self.assertTrue(failed)
                    self.assertEqual(self.snapshot(home, backups=False), before)
                    self.assertTrue(list(self.state(home, host).parent.glob('backups/*/manifest.json')))
                    self.run_installer(installer, home)
                    self.run_installer(installer, home, 'check')

    def test_legacy_paths_require_exact_inventory_and_historical_manifest_identity(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host), self.fixture(host) as (installer, home):
                files, old = self.seed_legacy(installer, home, host)
                skill_root = '.agents' if host == 'codex' else '.claude'
                malicious = (
                    f'{skill_root}/skills/_shared/private.md',
                    f'{skill_root}/skills/_shared/SKILL.md',
                    f'{skill_root}/skills/quick-fix/private.md',
                    f'{skill_root}/skills/_shared/../private.md',
                    f'{skill_root}/skills/_shared/CON',
                    f'{skill_root}/skills/_shared/expert-platform.md:stream',
                    f'{skill_root}/skills/_shared/expert-platform.md.',
                    '../escape', r'C:\Users\other\file',
                )
                for name in malicious:
                    with self.subTest(path=name):
                        bad = dict(old, files={**old['files'], name: '0' * 64})
                        self.state(home, host).write_text(json.dumps(bad), encoding='utf-8')
                        before = self.snapshot(home)
                        with self.assertRaisesRegex(ValueError, '越界路径'):
                            self.run_installer(installer, home, replace=True)
                        self.assertEqual(self.snapshot(home), before)
                for field, value in (('version', '3.0.0'), ('version', '2.0.0'),
                                     ('package', 'other-package'), ('schema_version', 2)):
                    bad = dict(old, **{field: value})
                    self.state(home, host).write_text(json.dumps(bad), encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, '越界路径'):
                        self.run_installer(installer, home, replace=True)
                name = next(iter(files))
                for value in (None, 12, 'hash', 'g' * 64):
                    bad = dict(old, files={name: value})
                    self.state(home, host).write_text(json.dumps(bad), encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, '越界路径'):
                        self.run_installer(installer, home, replace=True)

    def test_legacy_payload_is_rejected_by_standalone_new_package(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host), self.fixture(host) as (installer, home):
                package = home.parent / '独立发行包'
                shutil.copytree(installer.PACKAGE, package, ignore=shutil.ignore_patterns('__pycache__'))
                local = load_installer(host, package)
                old_agent = next(n for n in LEGACY[host] if '/agents/dev.' in n)
                injected = package / 'agents' / Path(old_agent).name
                injected.write_text(LEGACY[host][old_agent], encoding='utf-8')
                self.assertFalse(local.safe_relative(old_agent))
                with self.assertRaisesRegex(ValueError, '不允许的分发路径'):
                    self.run_installer(local, home)
                self.assertFalse(self.snapshot(home))

    def test_standalone_package_migrates_without_repository_or_other_host(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host), self.fixture(host) as (installer, home):
                self.seed_legacy(installer, home, host)
                package = home.parent / '仅含本端的独立发行包'
                shutil.copytree(installer.PACKAGE, package, ignore=shutil.ignore_patterns('__pycache__'))
                for command in ('install', 'check', 'uninstall'):
                    result = subprocess.run(
                        [sys.executable, str(package / 'install.py'), command, '--home', str(home)],
                        cwd=package, env=isolated_environment(home), capture_output=True, encoding='utf-8')
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dry_run_leaves_complete_legacy_installation_untouched(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host), self.fixture(host) as (installer, home):
                self.seed_legacy(installer, home, host)
                before = self.snapshot(home)
                self.run_installer(installer, home, dry_run=True)
                self.assertEqual(self.snapshot(home), before)

    def test_legacy_symlink_and_hardlink_cannot_be_followed_or_replaced(self):
        for host in ('codex', 'claude'):
            for link in ('symlink', 'hardlink'):
                with self.subTest(host=host, link=link), self.fixture(host) as (installer, home):
                    files, _ = self.seed_legacy(installer, home, host)
                    target = home / next(n for n in files if '/agents/dev.' in n)
                    outside = home.parent / '不属于安装的文件'
                    outside.write_text('不得修改', encoding='utf-8')
                    target.unlink()
                    try:
                        if link == 'symlink':
                            target.symlink_to(outside)
                        else:
                            os.link(outside, target)
                    except OSError as exc:
                        self.skipTest(f'本机无法建立 {link}: {exc}')
                    with self.assertRaises(ValueError):
                        self.run_installer(installer, home, replace=True)
                    self.assertEqual(outside.read_text(encoding='utf-8'), '不得修改')
                    self.assertEqual(json.loads(self.state(home, host).read_text())['version'], '2.0.1')


if __name__ == '__main__':
    unittest.main()
