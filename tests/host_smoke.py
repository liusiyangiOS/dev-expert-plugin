#!/usr/bin/env python3
"""真实 CLI 的隔离加载测试。只用空配置；不登录、不调用远程模型。"""
import argparse
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from support import isolated_environment, native_cli

ROOT = Path(__file__).resolve().parents[1]
ROLES = {"dev-planner", "dev-developer", "dev-qa", "dev-debugger", "dev-researcher",
         "dev-code-reviewer", "dev-security-auditor", "dev-team-lead"}
SKILLS = {"dev-expert-team-review", "dev-bugfix-pipeline", "dev-post-coding-pipeline", "dev-quick-fix"}


def call(args, env, cwd, *, success=True):
    if args[0] in ("codex", "claude"):
        args = [native_cli(args[0]), *args[1:]]
    p = subprocess.run(args, env=env, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", timeout=45, stdin=subprocess.DEVNULL)
    if success and p.returncode:
        raise RuntimeError(f"{args[:3]}: {p.stdout}\n{p.stderr}")
    return p


def claude_probe(base):
    user = base / "claude-user"
    user.mkdir()
    env = isolated_environment(user)
    print(call(["claude", "--version"], env, user).stdout.strip())
    for path in (ROOT, ROOT / "packages/claude"):
        call(["claude", "plugin", "validate", str(path)], env, user)
    call(["claude", "plugin", "marketplace", "add", str(ROOT)], env, user)
    call(["claude", "plugin", "install", "dev-expert-plugin@dev-expert"], env, user)
    details = call(["claude", "plugin", "details", "dev-expert-plugin@dev-expert"], env, user)
    assert "Skills (4)" in details.stdout and "Agents (8)" in details.stdout, details.stdout
    for name in ROLES | SKILLS:
        assert name in details.stdout, name
    cache = user / ".claude/plugins/cache"
    roots = list(cache.glob("dev-expert/dev-expert-plugin/*"))
    assert roots, "Claude 未产生实际插件缓存"
    installed = roots[0]
    for folder in ("agents", "skills"):
        for src in (ROOT / "packages/claude" / folder).rglob("*"):
            if src.is_file():
                dst = installed / src.relative_to(ROOT / "packages/claude")
                assert dst.is_file() and dst.read_bytes() == src.read_bytes(), dst
                assert not dst.is_symlink() and dst.stat().st_nlink == 1, dst
    call(["claude", "plugin", "update", "dev-expert-plugin@dev-expert"], env, user)
    call(["claude", "plugin", "uninstall", "dev-expert-plugin@dev-expert"], env, user)
    print("PASS Claude：真实市场安装、4 技能/8 角色发现、文件一致、更新与卸载")


def codex_probe(base, wire):
    user = base / "codex-user"
    user.mkdir()
    env = isolated_environment(user)
    print(call(["codex", "--version"], env, user).stdout.strip())
    install = [sys.executable, str(ROOT / "packages/codex/install.py")]
    call([*install, "install", "--home", str(user)], env, user)
    call([*install, "check", "--home", str(user)], env, user)
    prompt = call(["codex", "--no-daemon", "debug", "prompt-input"], env, user)
    decoded = json.loads(prompt.stdout)
    # JSON wire escapes Windows backslashes; compare decoded text, not raw JSON.
    visible = "\n".join(part.get("text", "") for item in decoded
                        for part in item.get("content", [])).replace("\\", "/")
    for skill in SKILLS:
        assert f"- {skill}:" in visible and f"/{skill}/SKILL.md" in visible, skill
    assert (user / ".agents/skills").as_posix() in visible
    print("PASS Codex：真实宿主上下文发现 4 个技能")
    if wire:
        # Capture native tool schemas on loopback. The fixture deliberately
        # rejects the request before inference; no API credentials are used.
        requests = []

        class Capture(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"offline install probe captured",'
                                 b'"type":"invalid_request_error"}}')

            def log_message(self, *_):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Capture)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            provider = json.dumps(f"http://127.0.0.1:{server.server_port}/v1")
            call(["codex", "--no-daemon", "exec", "--ephemeral", "--skip-git-repo-check",
                  "--ignore-user-config", "-m", "installation-probe",
                  "-c", 'model_provider="installation_probe"',
                  "-c", 'model_providers.installation_probe={name="Offline probe",base_url='
                  + provider + ',wire_api="responses",requires_openai_auth=false}',
                  "Installation discovery only; do not execute tasks."], env, user, success=False)
            assert requests, "未捕获本地请求，不能证明角色工具加载"
            schemas = json.dumps(json.loads(requests[0]).get("tools", []))
            for role in ROLES:
                assert role in schemas, f"宿主工具未发现角色：{role}"
            print("PASS Codex：原生委派工具包含全部 8 个角色（本地请求捕获，无模型推理）")
        finally:
            server.shutdown()
            server.server_close()
    call([*install, "uninstall", "--home", str(user)], env, user)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["both", "claude", "codex"], default="both")
    parser.add_argument("--codex-wire", action="store_true",
                        help="用仅监听 127.0.0.1 的临时 HTTP 服务核对 Codex 角色工具")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="expert-host-smoke-") as folder:
        base = Path(folder).resolve()
        for name, fn in (("claude", claude_probe), ("codex", codex_probe)):
            if args.platform not in ("both", name):
                continue
            native_cli(name)
            fn(base, args.codex_wire) if name == "codex" else fn(base)


if __name__ == "__main__":
    main()
