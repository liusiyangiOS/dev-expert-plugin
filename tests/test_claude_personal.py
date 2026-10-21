"""Claude 插件到个人安装的适配、生命周期与独立性。"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from support import isolated_environment

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / 'packages/claude/install.py'
spec = importlib.util.spec_from_file_location('claude_installer', INSTALL)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ClaudePersonalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='expert-claude-personal-')
        self.home = Path(self.temp.name) / '使用者 空格'
        self.env = isolated_environment(self.home)

    def tearDown(self):
        self.temp.cleanup()

    def run_install(self, command='install', *options, ok=True, source=INSTALL):
        result = subprocess.run([sys.executable, str(source), command, *options],
                                env=self.env, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_render_changes_only_layout_and_preserves_contracts(self):
        files = installer.payload()
        self.assertEqual(len(files), 20)
        for rel, data in files.items():
            self.assertNotIn(b'CLAUDE_PLUGIN_ROOT', data, rel)
            self.assertNotIn(b'dev-expert-plugin:', data, rel)
            self.assertNotIn(b'.agents/', data, rel)
            self.assertNotIn(b'.codex/', data, rel)
            if rel == '.claude/expert-team/README.md':
                self.assertEqual(data, (installer.PACKAGE / 'personal-install.md').read_bytes())
                continue
            source = (installer.PACKAGE / rel.removeprefix('.claude/')).read_text(encoding='utf-8')
            if not rel.endswith(('expert-platform.md', 'expert-team-runtime.md')):
                self.assertEqual(data.decode(), source.replace('${CLAUDE_PLUGIN_ROOT}', '~/.claude'))
            elif rel.endswith('expert-team-runtime.md'):
                # All routing, budget, known-failure and evidence rules survive verbatim.
                for section in ('## 快修自动路由', '## 证据、状态与缺失依赖'):
                    original = source.split(section, 1)[1].split('\n## ', 1)[0]
                    self.assertIn(original, data.decode())

    def test_lifecycle_and_unrelated_files(self):
        sentinel = self.home / '.claude/cache/expert-team/expert-model-cache.json'
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text('private cache', encoding='utf-8')
        self.run_install('install', '--dry-run')
        self.assertFalse((self.home / '.claude/agents').exists())
        self.run_install()
        self.run_install('check')
        self.run_install()
        for rel, data in installer.payload().items():
            dest = self.home / rel
            self.assertEqual(dest.read_bytes(), data)
            self.assertFalse(dest.is_symlink())
            self.assertEqual(dest.stat().st_nlink, 1)
        self.run_install('uninstall')
        self.assertEqual(sentinel.read_text(), 'private cache')
        self.assertFalse((self.home / '.claude/agents/dev.md').exists())
        self.assertEqual(list((self.home / '.codex').iterdir()), [])
        self.assertFalse((self.home / '.agents').exists())

    def test_local_edits_block_updates_and_are_backed_up(self):
        self.run_install()
        dest = self.home / '.claude/skills/quick-fix/SKILL.md'
        dest.write_text('personal change', encoding='utf-8')
        self.run_install('check', ok=False)
        self.run_install(ok=False)
        self.run_install('uninstall', ok=False)
        self.run_install('install', '--replace')
        saved = list((self.home / '.claude/expert-team/backups').rglob('SKILL.md'))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(), 'personal change')
        self.run_install('check')

    def test_standalone_package_updates_without_codex(self):
        package = Path(self.temp.name) / '独立包'
        shutil.copytree(INSTALL.parent, package, ignore=shutil.ignore_patterns('__pycache__'))
        local = package / 'install.py'
        self.run_install(source=local)
        src = package / 'agents/dev.md'
        src.write_text(src.read_text(encoding='utf-8') + '\n更新测试\n', encoding='utf-8')
        self.run_install(source=local)
        self.run_install('check', source=local)
        self.assertIn('更新测试', (self.home / '.claude/agents/dev.md').read_text(encoding='utf-8'))

    def test_write_failure_rolls_back(self):
        args = installer.argparse.Namespace(home=self.home, explicit_home=True,
                                            command='install', replace=False, dry_run=False)
        original = installer.atomic_write
        count = 0
        def fail_once(path, data):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError('disk fixture')
            original(path, data)
        installer.atomic_write = fail_once
        try:
            with self.assertRaises(OSError):
                installer.run(args)
        finally:
            installer.atomic_write = original
        self.assertFalse(any(p.is_file() for p in self.home.rglob('*')))

    def test_manifest_and_link_boundaries(self):
        for rel in ('../escape', '.codex/agents/dev.md', '.claude/agents/dev.toml',
                    '.claude/skills/quick-fix/CON', '.claude/skills/quick-fix/a:b'):
            self.assertFalse(installer.safe_relative(rel))
        self.run_install()
        dest = self.home / '.claude/agents/dev.md'
        outside = self.home / 'linked-original'
        outside.write_text('untouched')
        dest.unlink()
        os.link(outside, dest)
        self.run_install('install', '--replace', ok=False)
        self.assertEqual(outside.read_text(), 'untouched')
        dest.unlink()
        self.run_install('install', '--replace')
        manifest = self.home / '.claude/expert-team/install-manifest.json'
        manifest.write_text(json.dumps({'files': {'../../escape': 'hash'}}))
        self.run_install('uninstall', '--replace', ok=False)
        self.assertTrue(dest.exists())

    def test_future_layout_rules_cannot_be_silently_dropped(self):
        relative = 'skills/_shared/expert-team-runtime.md'
        original = (installer.PACKAGE / relative).read_bytes()
        with self.assertRaises(ValueError):
            installer.render_personal(relative, original + '\n新增的必要验收规则\n'.encode())
        relative = 'skills/_shared/expert-platform.md'
        original = (installer.PACKAGE / relative).read_text(encoding='utf-8')
        changed = original.replace('不猜测作者或宿主缓存目录。', '不猜测作者或宿主缓存目录。新增约束。')
        with self.assertRaises(ValueError):
            installer.render_personal(relative, changed.encode())

    def test_nondefault_config_is_rejected(self):
        self.env['CLAUDE_CONFIG_DIR'] = str(self.home / 'different-config')
        self.run_install(ok=False)


if __name__ == '__main__':
    unittest.main()
