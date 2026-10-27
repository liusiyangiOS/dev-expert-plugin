#!/usr/bin/env python3
"""安装普通文件；不改全局配置、不联网、不创建链接。Claude 个人目录版；Python 3.11+。"""
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
VERSION = "3.1.0"
REQUIRED_SHARED = ('expert-performance.md', 'expert-performance-record.md', 'expert-ui-verification.md')
PACKAGE_NAME = "dev-expert-claude-personal"
# Exact file inventory of the independently distributed 2.0.1 package.
# Legacy names are accepted only in that managed manifest, never as payload.
LEGACY_PATHS = frozenset({
    ".claude/agents/code-reviewer.md",
    ".claude/agents/debugger.md",
    ".claude/agents/dev.md",
    ".claude/agents/planner.md",
    ".claude/agents/qa.md",
    ".claude/agents/researcher.md",
    ".claude/agents/security-auditor.md",
    ".claude/agents/team-lead.md",
    ".claude/skills/_shared/expert-evaluation-cases.md",
    ".claude/skills/_shared/expert-known-failures.md",
    ".claude/skills/_shared/expert-model-policy.md",
    ".claude/skills/_shared/expert-platform.md",
    ".claude/skills/_shared/expert-role-contract.md",
    ".claude/skills/_shared/expert-team-runtime.md",
    ".claude/skills/_shared/expert-workflow-contract.md",
    ".claude/skills/bugfix-pipeline/SKILL.md",
    ".claude/skills/expert-team-review/SKILL.md",
    ".claude/skills/post-coding-pipeline/SKILL.md",
    ".claude/skills/quick-fix/SKILL.md",
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
    return name == ".claude/expert-team/README.md" or (not p.is_absolute() and
            ((len(p.parts) == 3 and p.parts[:2] == (".claude", "agents")
              and p.stem in ROLES and p.suffix == ".md") or
             (len(p.parts) >= 4 and p.parts[:2] == (".claude", "skills")
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


def render_personal(relative, data):
    """仅转换安装路径与调用名称；质量、路由、模型和验证正文保持原样。"""
    text = data.decode("utf-8")
    if relative == "skills/dev-shared/expert-team-runtime.md":
        head, sep, layout = text.partition("## 插件发行版的名称与路径")
        # Fail closed if a future edit adds rules to the rewritten layout section.
        if not sep or digest(layout.encode("utf-8")) != "c5d5c7d127c2dc1043b665fb93c18240f8b51af381d89a5e7138f1b94d4154cc":
            raise ValueError("运行约定结构变化，请先更新个人目录适配器")
        text = head + """## 个人安装版的名称与路径

技能调用名为 `/<技能名>`，专家类型为 `<角色名>`。委派前核对宿主实际列出的角色类型，使用本个人安装的角色；缺少必需角色时报告安装缺口，不换成自审。本文中的简称仍表示相同职责，不创建额外主理人。

规则与角色均在当前用户 `~/.claude/`，读取前展开为实际绝对路径；相对链接按所在文件目录解析。不要同时启用本团同名插件和个人安装，避免两套入口混用。更新只替换源码，不重置模型缓存、历史诊断或状态。
"""
        text = text.replace("路径按当前安装者与插件根解析", "路径按当前安装者的个人目录解析")
    if relative == "skills/dev-shared/expert-platform.md":
        start = text.index("`${CLAUDE_PLUGIN_ROOT}` 是")
        end = text.index("\n\n读取文件时", start)
        if digest(text[start:end].encode("utf-8")) != "b2c1241f179e622d5045965f023719194b1a685cf65f1565546b608fcdcb5a97":
            raise ValueError("平台路径段落变化，请先审阅并更新个人目录适配器")
        text = text[:start] + "本个人安装的角色与技能根目录为当前用户 `~/.claude/`，使用前解析为真实绝对路径；不依赖插件变量或插件缓存。" + text[end:]
        text = text.replace("插件资源与本端状态", "个人资源与本端状态").replace("本插件", "本专家团").replace("插件缺少资源", "本安装缺少资源")
    return text.replace("${CLAUDE_PLUGIN_ROOT}", "~/.claude").encode("utf-8")


def payload():
    readme = PACKAGE / "personal-install.md"
    check_path(readme)
    files = {".claude/expert-team/README.md": readme.read_bytes()}
    for folder, prefix in (("agents", ".claude/agents"), ("skills", ".claude/skills")):
        for src in sorted((PACKAGE / folder).rglob("*")):
            if src.is_dir() and not is_redirect(src):
                continue
            if "__pycache__" in src.parts or src.name == ".DS_Store":
                continue
            check_path(src)
            rel = f"{prefix}/{src.relative_to(PACKAGE / folder).as_posix()}"
            if not safe_relative(rel):
                raise ValueError(f"不允许的分发路径：{rel}")
            files[rel] = render_personal(src.relative_to(PACKAGE).as_posix(), src.read_bytes())
    if len([x for x in files if x.startswith(".claude/agents/")]) != 8:
        raise ValueError("安装包缺少专家角色")
    for name in SKILLS - {"dev-shared"}:
        if f".claude/skills/{name}/SKILL.md" not in files:
            raise ValueError(f"安装包缺少技能：{name}")
    for name in REQUIRED_SHARED:
        if f".claude/skills/dev-shared/{name}" not in files:
            raise ValueError(f"安装包缺少共享资源：{name}")
    return files


def run(args):
    home = args.home.expanduser().resolve()
    if not args.explicit_home and os.environ.get("CLAUDE_CONFIG_DIR"):
        if Path(os.environ["CLAUDE_CONFIG_DIR"]).expanduser().resolve() != (home / ".claude").resolve():
            raise ValueError("当前 CLAUDE_CONFIG_DIR 非默认目录；个人目录安装只支持默认 ~/.claude 布局。")
    state = home / ".claude/expert-team/install-manifest.json"
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
    print(f"{args.command}: {home}，将变更 {len(changes)} 个文件；不修改 settings.json 或 CLAUDE.md。")
    if args.dry_run:
        for name in changes:
            print(name)
        return
    before_state = state.read_bytes() if state.exists() else None
    backup = None
    if any(before is not None for before, _ in changes.values()) or before_state:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = home / ".claude/expert-team/backups" / stamp
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
    print("完成。请新开 Claude Code 会话；模型缓存和历史失败记录保持原样。")


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
