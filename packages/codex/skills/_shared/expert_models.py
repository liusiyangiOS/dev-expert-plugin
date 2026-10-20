"""四个专家技能共用的模型解析与 72 小时缓存（只用标准库）。"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

TTL = timedelta(hours=72)
ROLES = (
    "planner", "dev", "debugger", "code-reviewer", "security-auditor",
    "team-lead", "qa", "researcher",
)
CACHE = Path.home() / ".cache" / "codex-expert-workflows" / "expert-model-cache.json"
CATALOG = Path.home() / ".codex" / "models_cache.json"


class PolicyError(ValueError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def parse_time(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("缺少时区")
        return stamp.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError) as exc:
        raise PolicyError("检查时间必须为含时区的 ISO 8601 时间") from exc


def fresh(value, now):
    age = now - parse_time(value)
    return timedelta(0) <= age < TTL


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PolicyError(f"无法读取有效 JSON：{path}") from exc


def normalize_catalog(document):
    if not isinstance(document, dict):
        raise PolicyError("模型目录必须为 JSON 对象")
    entries = document.get("models", document.get("data"))
    if not isinstance(entries, list) or not entries:
        raise PolicyError("模型目录缺少非空 models/data 列表")
    models = {}
    for item in entries:
        if not isinstance(item, dict):
            raise PolicyError("模型条目必须为对象")
        slug = item.get("slug") or item.get("model") or item.get("id")
        if not isinstance(slug, str) or not slug:
            raise PolicyError("模型条目缺少 ID")
        hidden = item.get("hidden", item.get("visibility") == "hide")
        levels = item.get("supported_reasoning_levels",
                          item.get("supportedReasoningEfforts", []))
        if not isinstance(levels, list):
            raise PolicyError(f"{slug} 的推理强度列表无效")
        efforts = sorted({
            level.get("effort", level.get("reasoningEffort"))
            for level in levels if isinstance(level, dict)
            and isinstance(level.get("effort", level.get("reasoningEffort")), str)
        })
        if slug in models:
            raise PolicyError(f"目录含重复模型：{slug}")
        models[slug] = {"hidden": bool(hidden), "efforts": efforts}
    return models


def require_pair(models, slug, effort):
    if slug not in models:
        raise PolicyError(f"当前可用列表中没有模型 {slug}，禁止自动替换")
    if effort not in models[slug]["efforts"]:
        raise PolicyError(f"{slug} 不支持 {effort}，禁止自动调整强度")


def latest_family(models, family):
    candidates = []
    pattern = rf"gpt-(\d+(?:\.\d+)*)-{family}(?:-(\d{{4}}-\d{{2}}-\d{{2}}))?"
    for slug, info in models.items():
        match = re.fullmatch(pattern, slug)
        if match and not info["hidden"]:
            version = tuple(int(part) for part in match[1].split("."))
            candidates.append((version, match[2] or "", slug))
    if not candidates:
        raise PolicyError(f"没有可用的 {family} 家族模型；需核验官方继任关系，禁止换档")
    return max(candidates)[2]


def make_cache(document, flagship, sources, now):
    models = normalize_catalog(document)
    if not fresh(document.get("fetched_at"), now):
        raise PolicyError("模型目录已满 72 小时或来自未来；请先查询最新列表")
    if not sources or any(
        urlsplit(url).scheme != "https" or urlsplit(url).hostname not in
        {"learn.chatgpt.com", "developers.openai.com", "platform.openai.com"}
        for url in sources
    ):
        raise PolicyError("顶级模型必须附已实际查阅的官方 HTTPS 证据链接")
    sol = latest_family(models, "sol")
    terra = latest_family(models, "terra")
    if flagship not in models or models[flagship]["hidden"]:
        raise PolicyError("官方确认的顶级模型不在当前可见可用列表中")
    for slug, effort in ((sol, "high"), (terra, "high"),
                         (terra, "medium"), (flagship, "high")):
        require_pair(models, slug, effort)
    return {
        "schema_version": 1,
        "checked_at": now.isoformat(),
        "catalog_fetched_at": document["fetched_at"],
        "sources": sources,
        "tiers": {"sol": sol, "terra": terra, "flagship": flagship},
        "models": models,
    }


def valid_cache(cache, now):
    if not isinstance(cache, dict) or cache.get("schema_version") != 1:
        raise PolicyError("共享缓存格式无效")
    if not fresh(cache.get("checked_at"), now):
        raise PolicyError("共享缓存已满 72 小时或检查时间异常")
    # 查询来源也必须新鲜，不能把较旧的本机目录重标为刚刚查询。
    if not fresh(cache.get("catalog_fetched_at"), now):
        raise PolicyError("缓存的原始模型目录已满 72 小时")
    try:
        tiers, models = cache["tiers"], cache["models"]
        if not isinstance(models, dict) or not isinstance(tiers, dict):
            raise TypeError()
        for family in ("sol", "terra"):
            if tiers[family] != latest_family(models, family):
                raise PolicyError("缓存的家族模型不是目录中的最新版本")
        for slug, effort in ((tiers["sol"], "high"), (tiers["terra"], "high"),
                             (tiers["terra"], "medium"), (tiers["flagship"], "high")):
            if models[slug]["hidden"]:
                raise PolicyError("模式缓存选择了隐藏模型")
            require_pair(models, slug, effort)
    except (KeyError, TypeError, AttributeError) as exc:
        raise PolicyError("共享缓存模型/强度结构损坏") from exc
    return cache


def resolve(cache, mode, model=None, effort=None, catalog=None, now=None):
    now = now or utcnow()
    # 明确指定模型时独立校验，不要求 Sol/Terra/顶级模式先刷新。
    if model:
        if not isinstance(catalog, dict) or not fresh(catalog.get("fetched_at"), now):
            raise PolicyError("请提供 72 小时内的当前可用目录以验证指定模型")
        models = normalize_catalog(catalog)
    else:
        cache = valid_cache(cache, now)
        models = cache["models"]
        if isinstance(catalog, dict) and fresh(catalog.get("fetched_at"), now):
            models = normalize_catalog(catalog)
    agents = {}
    for role in ROLES:
        selected_effort = effort or ("medium" if role == "researcher" else "high")
        if model:
            selected_model = model
        elif role in ("qa", "researcher"):
            selected_model = cache["tiers"]["terra"]
        else:
            selected_model = cache["tiers"]["flagship" if mode == "疯狂" else "sol"]
        require_pair(models, selected_model, selected_effort)
        agents[role] = {"model": selected_model, "reasoning_effort": selected_effort}
    return {"mode": mode, "override": {"model": model, "reasoning_effort": effort},
            "agents": agents}


def atomic_save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as stream:
            temporary = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "refresh", "resolve"))
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--mode", choices=("默认", "疯狂"), default="默认")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--flagship")
    parser.add_argument("--source", action="append", default=[])
    args = parser.parse_args()
    now = utcnow()
    try:
        if args.command == "refresh":
            cache = make_cache(read_json(args.catalog), args.flagship, args.source, now)
            atomic_save(args.cache, cache)
            result = {"status": "refreshed", "checked_at": cache["checked_at"],
                      "tiers": cache["tiers"]}
        else:
            if args.command == "status":
                cache = valid_cache(read_json(args.cache), now)
                result = {"status": "fresh", "checked_at": cache["checked_at"],
                          "tiers": cache["tiers"]}
            else:
                cache = None if args.model else read_json(args.cache)
                try:
                    catalog = read_json(args.catalog)
                except PolicyError:
                    catalog = None
                result = resolve(cache, args.mode, args.model, args.effort, catalog, now)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (PolicyError, OSError) as exc:
        status = "refresh_required" if args.command == "status" else "blocked"
        print(json.dumps({"status": status, "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
