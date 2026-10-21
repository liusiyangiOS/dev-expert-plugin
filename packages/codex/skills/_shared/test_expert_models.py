"""离线验证模型选择、覆盖、过期与失败不改缓存。"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import expert_models as policy


def catalog(now, *slugs):
    return {"fetched_at": now.isoformat(), "models": [
        {"slug": slug, "visibility": "list", "supported_reasoning_levels": [
            {"effort": effort} for effort in ("low", "medium", "high", "max")
        ]} for slug in slugs
    ]}


class ModelPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = policy.utcnow()
        self.catalog = catalog(self.now, "gpt-6-sol", "gpt-6.1-sol",
                               "gpt-5.6-terra", "gpt-6-astra")
        self.cache = policy.make_cache(self.catalog, "gpt-6-astra",
                                       ["https://learn.chatgpt.com/docs/models"], self.now)

    def test_default_mode_preserves_role_split(self):
        agents = policy.resolve(self.cache, "默认", now=self.now)["agents"]
        self.assertEqual(agents["dev"], {"model": "gpt-6.1-sol", "reasoning_effort": "high"})
        self.assertEqual(agents["qa"], {"model": "gpt-5.6-terra", "reasoning_effort": "high"})
        self.assertEqual(agents["researcher"]["reasoning_effort"], "medium")
        self.assertEqual(agents["team-lead"], agents["dev"])

    def test_crazy_mode_uses_flagship_but_keeps_terra(self):
        agents = policy.resolve(self.cache, "疯狂", now=self.now)["agents"]
        self.assertEqual(agents["planner"]["model"], "gpt-6-astra")
        self.assertEqual(agents["qa"]["model"], "gpt-5.6-terra")

    def test_explicit_pair_overrides_every_role_without_mode_cache(self):
        agents = policy.resolve(None, "疯狂", "gpt-6-sol", "max",
                                self.catalog, self.now)["agents"]
        self.assertEqual(len(agents), 8)
        self.assertTrue(all(entry == {"model": "gpt-6-sol", "reasoning_effort": "max"}
                            for entry in agents.values()))

    def test_only_model_override_preserves_role_effort(self):
        agents = policy.resolve(None, "默认", "gpt-6-astra", catalog=self.catalog,
                                now=self.now)["agents"]
        self.assertTrue(all(entry["model"] == "gpt-6-astra" for entry in agents.values()))
        self.assertEqual(agents["researcher"]["reasoning_effort"], "medium")

    def test_only_effort_override_preserves_mode_models(self):
        agents = policy.resolve(self.cache, "疯狂", effort="low", now=self.now)["agents"]
        self.assertTrue(all(entry["reasoning_effort"] == "low" for entry in agents.values()))
        self.assertEqual(agents["dev"]["model"], "gpt-6-astra")
        self.assertEqual(agents["qa"]["model"], "gpt-5.6-terra")

    def test_partial_override_rejects_unsupported_role_effort(self):
        self.catalog["models"][3]["supported_reasoning_levels"] = [{"effort": "high"}]
        with self.assertRaises(policy.PolicyError):
            policy.resolve(None, "默认", "gpt-6-astra", catalog=self.catalog, now=self.now)

    def test_version_order_is_numeric_and_selects_new_terra(self):
        models = policy.normalize_catalog(catalog(self.now, "gpt-6.9-sol",
                  "gpt-6.10-sol", "gpt-5.6-terra", "gpt-6.1-terra"))
        self.assertEqual(policy.latest_family(models, "sol"), "gpt-6.10-sol")
        self.assertEqual(policy.latest_family(models, "terra"), "gpt-6.1-terra")

    def test_hidden_latest_model_is_not_selected(self):
        self.catalog["models"][1]["visibility"] = "hide"
        self.assertEqual(policy.latest_family(policy.normalize_catalog(self.catalog), "sol"),
                         "gpt-6-sol")

    def test_72_hour_boundary_and_future_clock(self):
        self.assertTrue(policy.fresh(self.cache["checked_at"], self.now + timedelta(hours=71)))
        self.assertFalse(policy.fresh(self.cache["checked_at"], self.now + timedelta(hours=72)))
        self.assertFalse(policy.fresh(self.cache["checked_at"], self.now - timedelta(seconds=1)))

    def test_original_catalog_age_cannot_be_reset_by_new_check_time(self):
        self.cache["catalog_fetched_at"] = (self.now - timedelta(hours=72)).isoformat()
        with self.assertRaises(policy.PolicyError):
            policy.valid_cache(self.cache, self.now)

    def test_stale_cache_blocks_mode_but_not_verified_explicit_pair(self):
        self.cache["checked_at"] = (self.now - timedelta(hours=72)).isoformat()
        with self.assertRaises(policy.PolicyError):
            policy.resolve(self.cache, "默认", now=self.now)
        agents = policy.resolve(self.cache, "默认", "gpt-6-sol", "high",
                                self.catalog, self.now)["agents"]
        self.assertEqual(agents["qa"]["model"], "gpt-6-sol")

    def test_missing_terra_is_not_silently_substituted(self):
        self.catalog["models"] = [m for m in self.catalog["models"] if "terra" not in m["slug"]]
        with self.assertRaises(policy.PolicyError):
            policy.make_cache(self.catalog, "gpt-6-astra",
                              ["https://learn.chatgpt.com/docs/models"], self.now)
        # 全员明确使用 Sol 时，Terra 缺失不能阻挡用户的选择。
        self.assertEqual(policy.resolve(None, "默认", "gpt-6-sol", "high",
                                        self.catalog, self.now)["agents"]["qa"]["model"],
                         "gpt-6-sol")

    def test_removed_model_is_rejected_by_current_catalog(self):
        self.catalog["models"] = [m for m in self.catalog["models"] if m["slug"] != "gpt-6.1-sol"]
        with self.assertRaises(policy.PolicyError):
            policy.resolve(self.cache, "默认", catalog=self.catalog, now=self.now)

    def test_unknown_or_unsupported_explicit_choice_is_not_changed(self):
        for model, effort in (("gpt-99-sol", "high"), ("gpt-6-astra", "none")):
            with self.subTest(model=model, effort=effort), self.assertRaises(policy.PolicyError):
                policy.resolve(None, "默认", model, effort, self.catalog, self.now)

    def test_future_flagship_name_is_supported(self):
        document = copy.deepcopy(self.catalog)
        document["models"] += catalog(self.now, "gpt-7-newflagship")["models"]
        cache = policy.make_cache(document, "gpt-7-newflagship",
                                  ["https://learn.chatgpt.com/docs/models"], self.now)
        self.assertEqual(policy.resolve(cache, "疯狂", now=self.now)["agents"]["dev"]["model"],
                         "gpt-7-newflagship")

    def test_camel_case_model_list_format(self):
        document = {"fetched_at": self.now.isoformat(), "data": [
            {"model": "gpt-6.1-sol", "hidden": False,
             "supportedReasoningEfforts": [{"reasoningEffort": "high"}]}
        ]}
        self.assertEqual(policy.normalize_catalog(document)["gpt-6.1-sol"]["efforts"], ["high"])

    def test_refresh_rejects_stale_catalog_or_nonofficial_source(self):
        for document, sources in (
            (catalog(self.now - timedelta(hours=72), "gpt-6.1-sol"),
             ["https://learn.chatgpt.com/docs/models"]),
            (self.catalog, ["https://example.org/models"]),
        ):
            with self.assertRaises(policy.PolicyError):
                policy.make_cache(document, "gpt-6-astra", sources, self.now)

    def test_failed_cli_refresh_does_not_overwrite_existing_cache(self):
        with tempfile.TemporaryDirectory(prefix="expert-model-test-") as directory:
            cache_path = Path(directory) / "cache.json"
            catalog_path = Path(directory) / "catalog.json"
            policy.atomic_save(cache_path, self.cache)
            policy.atomic_save(catalog_path, self.catalog)
            before = cache_path.read_bytes()
            result = subprocess.run([
                sys.executable, str(Path(policy.__file__)), "refresh",
                "--cache", str(cache_path), "--catalog", str(catalog_path),
                "--flagship", "unavailable-model",
                "--source", "https://learn.chatgpt.com/docs/models",
            ], capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "blocked")
            self.assertEqual(cache_path.read_bytes(), before)

    def test_cli_unicode_paths_and_output_are_utf8(self):
        with tempfile.TemporaryDirectory(prefix="expert-unicode-") as directory:
            root = Path(directory) / "模型 测试"
            root.mkdir()
            cache_path, catalog_path = root / "缓存.json", root / "目录.json"
            policy.atomic_save(cache_path, self.cache)
            policy.atomic_save(catalog_path, self.catalog)
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "cp1252"
            result = subprocess.run([
                sys.executable, str(Path(policy.__file__)), "resolve", "--mode", "疯狂",
                "--cache", str(cache_path), "--catalog", str(catalog_path),
            ], env=env, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["mode"], "疯狂")
            self.assertEqual(data["agents"]["qa"]["model"], "gpt-5.6-terra")


if __name__ == "__main__":
    unittest.main()
