"""发行命名空间的跨端运行时契约。

迁移兼容清单和 ``docs/source-manifest.json`` 必然保留旧发行名；本测试
只检查安装器实际会交付的 payload，避免将兼容读取误判为运行时引用。
"""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROLES = frozenset({
    "dev-planner", "dev-developer", "dev-qa", "dev-debugger",
    "dev-researcher", "dev-code-reviewer", "dev-security-auditor",
    "dev-team-lead",
})
SKILLS = frozenset({
    "dev-expert-team-review", "dev-bugfix-pipeline",
    "dev-post-coding-pipeline", "dev-quick-fix",
})
LEGACY_IDENTIFIERS = (
    "planner", "dev", "qa", "debugger", "researcher", "code-reviewer",
    "security-auditor", "team-lead", "expert-team-review", "bugfix-pipeline",
    "post-coding-pipeline", "quick-fix", "_shared",
)
LEGACY_ROLE_NAMES = {
    "dev-planner": "planner", "dev-developer": "dev", "dev-qa": "qa",
    "dev-debugger": "debugger", "dev-researcher": "researcher",
    "dev-code-reviewer": "code-reviewer",
    "dev-security-auditor": "security-auditor", "dev-team-lead": "team-lead",
}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NamespaceContractTests(unittest.TestCase):
    def test_role_metadata_matches_the_eight_new_filenames(self):
        for platform, suffix in (("codex", ".toml"), ("claude", ".md")):
            agents = ROOT / "packages" / platform / "agents"
            self.assertEqual({path.stem for path in agents.glob(f"*{suffix}")}, ROLES)
            for path in agents.glob(f"*{suffix}"):
                with self.subTest(platform=platform, role=path.stem):
                    if suffix == ".toml":
                        self.assertEqual(tomllib.loads(path.read_text(encoding="utf-8"))["name"],
                                         path.stem)
                    else:
                        front_matter = path.read_text(encoding="utf-8").split("---", 2)[1]
                        self.assertIn(f"name: {path.stem}", front_matter)

    def test_skills_and_codex_ui_use_the_same_new_namespace(self):
        for platform in ("codex", "claude"):
            skills_root = ROOT / "packages" / platform / "skills"
            self.assertEqual(
                {path.name for path in skills_root.iterdir() if (path / "SKILL.md").is_file()},
                SKILLS,
            )
            self.assertFalse((skills_root / "dev-shared" / "SKILL.md").exists())
            for skill in SKILLS:
                text = (skills_root / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(f"name: {skill}", text.split("---", 2)[1])

        for skill in SKILLS:
            ui = ROOT / "packages/codex/skills" / skill / "agents/openai.yaml"
            text = ui.read_text(encoding="utf-8")
            prompt = re.search(r"^\s*default_prompt:\s*[\"']?(.*?)[\"']?\s*$", text,
                               re.MULTILINE)
            self.assertIsNotNone(prompt, ui)
            self.assertIn(f"${skill}", prompt.group(1), ui)

    def test_model_resolution_exposes_exactly_the_new_role_keys(self):
        policy = load_module(
            ROOT / "packages/codex/skills/dev-shared/expert_models.py",
            "namespace_contract_expert_models",
        )
        now = policy.utcnow()
        catalog = {
            "fetched_at": now.isoformat(),
            "models": [{
                "slug": "gpt-6-sol",
                "supported_reasoning_levels": [{"effort": "high"}],
            }],
        }
        result = policy.resolve(None, "默认", model="gpt-6-sol", effort="high",
                                catalog=catalog, now=now)
        self.assertEqual(set(policy.ROLES), ROLES)
        self.assertEqual(set(result["agents"]), ROLES)

    def test_actual_install_payloads_have_no_legacy_runtime_reference(self):
        # The installer has deliberate migration support.  payload() is the public
        # release boundary: it also covers rendered Claude personal-install files.
        forbidden = re.compile(
            r"(?<![A-Za-z0-9_-])(?:" + "|".join(map(re.escape, LEGACY_IDENTIFIERS))
            + r")(?![A-Za-z0-9_-])"
        )
        for platform in ("codex", "claude"):
            installer = load_module(ROOT / f"packages/{platform}/install.py",
                                    f"namespace_contract_{platform}_installer")
            for destination, data in installer.payload().items():
                with self.subTest(platform=platform, destination=destination):
                    text = data.decode("utf-8")
                    self.assertIsNone(forbidden.search(text),
                                      f"legacy active reference in {destination}")

    def test_source_manifest_preserves_legacy_source_but_hashes_current_payload(self):
        entries = json.loads((ROOT / "docs/source-manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(entries)
        for entry in entries:
            with self.subTest(destination=entry["destination"]):
                # source is provenance from before the rename, so it must not be
                # normalized to the current filename and cannot be checked on disk.
                current = Path(entry["destination"]).relative_to(
                    Path("packages") / entry["platform"]
                )
                if current.parts[0] == "agents":
                    legacy = Path("agents", LEGACY_ROLE_NAMES[current.stem] + current.suffix)
                    source_root = ".claude" if entry["platform"] == "claude" else ".codex"
                else:
                    skill = current.parts[1]
                    legacy_skill = "_shared" if skill == "dev-shared" else skill.removeprefix("dev-")
                    legacy = Path("skills", legacy_skill, *current.parts[2:])
                    source_root = ".claude" if entry["platform"] == "claude" else ".agents"
                self.assertEqual(entry["source"], f"{source_root}/{legacy.as_posix()}")
                destination = ROOT / entry["destination"]
                self.assertTrue(destination.is_file(), destination)
                self.assertEqual(
                    hashlib.sha256(destination.read_bytes()).hexdigest(),
                    entry["packaged_sha256"],
                )
                self.assertEqual(entry["packaged_version"], "3.1.0")


if __name__ == "__main__":
    unittest.main()
