"""仅供测试使用的跨平台进程隔离，不进入任何运行包。"""
import os
from pathlib import Path
import shutil


def isolated_environment(user, source=None):
    source = os.environ if source is None else source
    user = Path(user).resolve()
    user.mkdir(parents=True, exist_ok=True)
    # Keep only OS process-launch requirements, never credentials/proxies/model
    # overrides or a real user's plugin/config/cache locations.
    env = {key: source[key] for key in (
        "PATH", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "SystemDrive",
    ) if key in source}
    env.update({
        "HOME": str(user), "USERPROFILE": str(user),
        "HOMEDRIVE": user.drive, "HOMEPATH": str(user)[len(user.drive):],
        "CODEX_HOME": str(user / ".codex"),
        "CLAUDE_CONFIG_DIR": str(user / ".claude"),
        "APPDATA": str(user / "AppData/Roaming"),
        "LOCALAPPDATA": str(user / "AppData/Local"),
        "XDG_CONFIG_HOME": str(user / ".config"),
        "XDG_CACHE_HOME": str(user / ".cache"),
        "XDG_STATE_HOME": str(user / ".local/state"),
        "TMP": str(user / "tmp"), "TEMP": str(user / "tmp"),
        "TMPDIR": str(user / "tmp"),
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
    })
    for key in ("APPDATA", "LOCALAPPDATA", "TMP", "CODEX_HOME", "CLAUDE_CONFIG_DIR",
                "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    return env


def native_cli(name):
    candidates = [name + ".exe", name] if os.name == "nt" else [name]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found and Path(found).suffix.lower() not in (".cmd", ".bat", ".ps1"):
            return found
    raise RuntimeError(
        f"宿主验证需要可直接执行的 {name} 二进制；Windows 请安装原生 .exe。"
        "本测试不经 cmd/PowerShell 包装器拼接参数；这不是专家团运行时的额外限制。")
