#!/usr/bin/env python3
"""只读审计发行包；--installed 同时检查当前用户的专家团，不读取凭据。"""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("dev-expert-team-review", "dev-bugfix-pipeline", "dev-post-coding-pipeline", "dev-quick-fix", "dev-shared")
ROLES = ("dev-planner", "dev-developer", "dev-qa", "dev-debugger", "dev-researcher",
         "dev-code-reviewer", "dev-security-auditor", "dev-team-lead")
# A literal OS user directory is not portable. ~, environment variables,
# plugin root tokens and project-relative resources are intentionally allowed.
PERSONAL = re.compile(
    r"(?:/(?:Users|home)/|/mnt/[a-zA-Z]/Users/|[a-zA-Z]:[\\/]+Users[\\/]+)"
    r"([^/\\\s`\"<>$%]+)[\\/]"
)


def scan(label, paths, base):
    files = list(dict.fromkeys(p for p in paths if p.is_file()
                               and p.suffix in (".md", ".toml", ".json", ".py", ".js", ".yaml")))
    issues = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        # Repeated backslashes in JSON/TOML represent the same Windows path.
        text = text.replace("\\\\", "\\")
        for number, line in enumerate(text.splitlines(), 1):
            if PERSONAL.search(line):
                issues.append({"file": path.relative_to(base).as_posix(), "line": number})
    return {"group": label, "files": len(files), "personal_path_references": issues}


def audit(installed=False):
    results = []
    for platform in ("codex", "claude"):
        base = ROOT / "packages" / platform
        paths = [p for name in ("agents", "skills") for p in (base / name).rglob("*")
                 if "__pycache__" not in p.parts]
        results.append(scan("package-" + platform, paths, base))
    if installed:
        user = Path.home()
        for platform, skill_dir, extension in (
            ("codex", ".agents/skills", ".toml"), ("claude", ".claude/skills", ".md")
        ):
            paths = [user / ("." + platform) / "agents" / (r + extension) for r in ROLES]
            paths += [p for name in SKILLS for p in (user / skill_dir / name).rglob("*")
                      if "__pycache__" not in p.parts]
            results.append(scan("installed-" + platform, paths, user))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    result = audit(args.installed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if any(r["personal_path_references"] for r in result) else 0)
