#!/usr/bin/env python3
"""安装普通文件；不改全局配置、不联网、不创建链接。Python 3.11+。"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
from datetime import datetime, timezone

PACKAGE = Path(__file__).resolve().parent
ROLES = {"dev-planner", "dev-developer", "dev-qa", "dev-debugger", "dev-researcher",
         "dev-code-reviewer", "dev-security-auditor", "dev-team-lead"}
SKILLS = {"dev-expert-team-review", "dev-bugfix-pipeline", "dev-post-coding-pipeline",
          "dev-quick-fix", "dev-shared"}
VERSION = "3.0.0"
PACKAGE_NAME = "dev-expert-codex"
# Exact file inventory of the independently distributed 2.0.1 package.
# Legacy names are accepted only in that managed manifest, never as payload.
LEGACY_PATHS = frozenset({
    ".agents/skills/_shared/expert-evaluation-cases.md",
    ".agents/skills/_shared/expert-known-failures.md",
    ".agents/skills/_shared/expert-model-policy.md",
    ".agents/skills/_shared/expert-platform.md",
    ".agents/skills/_shared/expert-role-contract.md",
    ".agents/skills/_shared/expert-workflow-contract.md",
    ".agents/skills/_shared/expert_models.py",
    ".agents/skills/_shared/test_expert_models.py",
    ".agents/skills/bugfix-pipeline/SKILL.md",
    ".agents/skills/bugfix-pipeline/agents/openai.yaml",
    ".agents/skills/bugfix-pipeline/references/original-workflow.js",
    ".agents/skills/expert-team-review/SKILL.md",
    ".agents/skills/expert-team-review/agents/openai.yaml",
    ".agents/skills/expert-team-review/references/original-workflow.js",
    ".agents/skills/post-coding-pipeline/SKILL.md",
    ".agents/skills/post-coding-pipeline/agents/openai.yaml",
    ".agents/skills/post-coding-pipeline/references/original-workflow.js",
    ".agents/skills/quick-fix/SKILL.md",
    ".agents/skills/quick-fix/agents/openai.yaml",
    ".agents/skills/quick-fix/references/model-selection.md",
    ".codex/agents/code-reviewer.toml",
    ".codex/agents/debugger.toml",
    ".codex/agents/dev.toml",
    ".codex/agents/planner.toml",
    ".codex/agents/qa.toml",
    ".codex/agents/researcher.toml",
    ".codex/agents/security-auditor.toml",
    ".codex/agents/team-lead.toml",
})


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(name):
    # Manifest keys use POSIX separators on every OS. Reject Windows drive,
    # UNC, ADS and ambiguous filename forms even when validating on Unix.
    if not isinstance(name, str) or "\\" in name or ":" in name:
        return False
    parts = name.split("/")
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
    if any(not part or part in (".", "..") or part.endswith((" ", "."))
           or part.split(".")[0].upper() in reserved
           or any(ord(c) < 32 or c in '<>"|?*' for c in part) for part in parts):
        return False
    p = PurePosixPath(name)
    return (not p.is_absolute() and
            ((len(p.parts) == 3 and p.parts[:2] == (".codex", "agents")
              and p.stem in ROLES and p.suffix == ".toml") or
             (len(p.parts) >= 4 and p.parts[:2] == (".agents", "skills")
              and p.parts[2] in SKILLS)))


def managed_files(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("安装清单必须是 JSON 对象")
    owned = manifest.get("files")
    legacy_manifest = (manifest.get("schema_version") == 1
                       and manifest.get("package") == PACKAGE_NAME
                       and manifest.get("version") == "2.0.1")
    if not isinstance(owned, dict) or any(
            not (safe_relative(name) or (legacy_manifest and name in LEGACY_PATHS))
            or not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
            for name, value in owned.items()):
        raise ValueError("安装清单损坏或包含越界路径")
    return owned


def check_path(path):
    for p in (path, *path.parents):
        if is_redirect(p):
            raise ValueError(f"拒绝通过软链接或目录联接读写：{p}")
    if path.exists():
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError(f"目标不是独立普通文件：{path}")


def is_redirect(path):
    if path.is_symlink():
        return True
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    # Path.is_junction() requires Python 3.12; this also covers Python 3.11.
    return getattr(info, "st_reparse_tag", None) == getattr(
        stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".expert-install-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def payload():
    files = {}
    for folder, prefix in (("agents", ".codex/agents"), ("skills", ".agents/skills")):
        for src in sorted((PACKAGE / folder).rglob("*")):
            if src.is_dir() and not is_redirect(src):
                continue
            if "__pycache__" in src.parts or src.name == ".DS_Store":
                continue
            check_path(src)
            rel = f"{prefix}/{src.relative_to(PACKAGE / folder).as_posix()}"
            if not safe_relative(rel):
                raise ValueError(f"不允许的分发路径：{rel}")
            files[rel] = src.read_bytes()
    if len([x for x in files if x.startswith(".codex/agents/")]) != 8:
        raise ValueError("安装包缺少专家角色")
    for name in SKILLS - {"dev-shared"}:
        if f".agents/skills/{name}/SKILL.md" not in files:
            raise ValueError(f"安装包缺少技能：{name}")
    return files


def run(args):
    home = args.home.expanduser().resolve()
    # A custom Codex home needs a matching packaging adapter; do not install
    # into a directory the running host will not discover.
    if not args.explicit_home and os.environ.get("CODEX_HOME"):
        if Path(os.environ["CODEX_HOME"]).expanduser().resolve() != (home / ".codex").resolve():
            raise ValueError("当前 CODEX_HOME 非默认目录；本安装包只支持默认用户布局。请使用独立测试 --home，或先按 README 处理自定义布局。")
    state = home / ".codex/expert-team/install-manifest.json"
    check_path(state)
    old = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {"files": {}}
    owned = managed_files(old)
    desired = payload() if args.command in ("install", "check") else {}
    if args.command == "check":
        errors = []
        for name in set(desired) | set(owned):
            dest = home / name
            check_path(dest)
            actual = digest(dest.read_bytes()) if dest.exists() else None
            if name not in desired or actual != digest(desired[name]) or owned.get(name) != actual:
                errors.append(name)
        if not state.exists() or errors:
            raise ValueError("安装不完整、与当前包不同或文件已修改：" + ", ".join(sorted(errors)))
        print(f"安装完整：8 个角色、4 个技能，{len(desired)} 个普通文件。")
        return
    if args.command == "uninstall" and not state.exists():
        raise ValueError("未找到本安装器的安装清单；不删除未经管理的文件")
    changes = {}
    for name in sorted(set(desired) | set(owned)):
        dest = home / name
        check_path(dest)
        before = dest.read_bytes() if dest.exists() else None
        if before is not None:
            managed_unchanged = name in owned and digest(before) == owned[name]
            if not managed_unchanged and not args.replace:
                raise ValueError(f"保留已有或被修改的文件：{dest}；审阅后用 --replace 备份并替换/卸载")
        after = desired.get(name)
        if before != after:
            changes[name] = (before, after)
    print(f"{args.command}: {home}，将变更 {len(changes)} 个文件；不修改 config.toml 或 AGENTS.md。")
    if args.dry_run:
        for name in changes:
            print(name)
        return
    before_state = state.read_bytes() if state.exists() else None
    backup = None
    if any(before is not None for before, _ in changes.values()) or before_state:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = home / ".codex/expert-team/backups" / stamp
        check_path(backup / "manifest.json")
        for name, (before, _) in changes.items():
            if before is not None:
                check_path(backup / "files" / name)
                atomic_write(backup / "files" / name, before)
        atomic_write(backup / "manifest.json", json.dumps({
            "command": args.command, "previous_install_manifest": old,
            "files": {n: b is not None for n, (b, _) in changes.items()}
        }, ensure_ascii=False, indent=2).encode("utf-8"))
    applied = []
    try:
        for name, (before, after) in changes.items():
            dest = home / name
            if after is None:
                dest.unlink(missing_ok=True)
            else:
                atomic_write(dest, after)
            applied.append(name)
        if args.command == "install":
            atomic_write(state, json.dumps({
                "schema_version": 1, "package": PACKAGE_NAME, "version": VERSION,
                "files": {n: digest(b) for n, b in desired.items()}
            }, ensure_ascii=False, indent=2).encode("utf-8"))
        else:
            state.unlink()
    except BaseException:
        for name in reversed(applied):
            before = changes[name][0]
            if before is None:
                (home / name).unlink(missing_ok=True)
            else:
                atomic_write(home / name, before)
        if before_state is None:
            state.unlink(missing_ok=True)
        else:
            atomic_write(state, before_state)
        raise
    if backup:
        print(f"原文件备份：{backup}")
    print("完成。请新开 Codex 会话；模型缓存和历史失败记录保持原样。")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["install", "check", "uninstall"])
    parser.add_argument("--home", type=Path, default=Path.home(), help="目标用户目录；测试用空目录")
    parser.add_argument("--dry-run", action="store_true", help="仅预览写入")
    parser.add_argument("--replace", action="store_true", help="明确备份并处理同名/被修改的文件")
    args = parser.parse_args()
    args.explicit_home = "--home" in sys.argv or any(a.startswith("--home=") for a in sys.argv)
    try:
        run(args)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"未完成：{exc}\n")


if __name__ == "__main__":
    main()
