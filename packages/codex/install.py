#!/usr/bin/env python3
"""安装普通文件；不改全局配置、不联网、不创建链接。Python 3.11+。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone

PACKAGE = Path(__file__).resolve().parent
ROLES = {"planner", "dev", "qa", "debugger", "researcher",
         "code-reviewer", "security-auditor", "team-lead"}
SKILLS = {"expert-team-review", "bugfix-pipeline", "post-coding-pipeline",
          "quick-fix", "_shared"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(name):
    p = Path(name)
    return (not p.is_absolute() and ".." not in p.parts and
            ((len(p.parts) == 3 and p.parts[:2] == (".codex", "agents")
              and p.stem in ROLES and p.suffix == ".toml") or
             (len(p.parts) >= 4 and p.parts[:2] == (".agents", "skills")
              and p.parts[2] in SKILLS)))


def check_path(path):
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError(f"拒绝通过软链接读写：{p}")
    if path.exists():
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError(f"目标不是独立普通文件：{path}")


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
            if src.is_dir() and not src.is_symlink():
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
    for name in SKILLS - {"_shared"}:
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
    old = json.loads(state.read_text()) if state.exists() else {"files": {}}
    owned = old.get("files")
    if not isinstance(owned, dict) or any(not safe_relative(n) for n in owned):
        raise ValueError("安装清单损坏或包含越界路径")
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
                atomic_write(backup / "files" / name, before)
        atomic_write(backup / "manifest.json", json.dumps({
            "command": args.command, "previous_install_manifest": old,
            "files": {n: b is not None for n, (b, _) in changes.items()}
        }, ensure_ascii=False, indent=2).encode())
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
                "schema_version": 1, "package": "dev-expert-codex", "version": "2.0.0",
                "files": {n: digest(b) for n, b in desired.items()}
            }, ensure_ascii=False, indent=2).encode())
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
