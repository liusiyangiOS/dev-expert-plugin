#!/usr/bin/env python3
"""隔离验证 Codex CLI 重启后恢复同一聊天是否重新加载角色/技能。

只向本机回环发送发现请求，固定返回 HTTP 400，不调用模型，不读取个人配置。
此结果不等同于 ChatGPT 桌面已有聊天的验收。
"""
import http.server
import json
from pathlib import Path
import tempfile
import threading

from host_smoke import ROOT, ROLES, SKILLS, call
from support import isolated_environment


def main():
    requests = []

    class Capture(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"offline reload probe captured",'
                             b'"type":"invalid_request_error"}}')

        def log_message(self, *_):
            pass

    with tempfile.TemporaryDirectory(prefix="expert-resume-probe-") as folder:
        user = Path(folder).resolve()
        env = isolated_environment(user)
        legacy = json.loads((ROOT / "tests/fixtures/legacy-2.0.1.json").read_text(
            encoding="utf-8"))["packages"]["codex"]
        import hashlib
        for name, data in legacy.items():
            dest = user / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data.encode("utf-8"))
        state = user / ".codex/expert-team/install-manifest.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({
            "schema_version": 1, "package": "dev-expert-codex", "version": "2.0.1",
            "files": {name: hashlib.sha256(data.encode()).hexdigest()
                      for name, data in legacy.items()},
        }), encoding="utf-8")
        server = http.server.HTTPServer(("127.0.0.1", 0), Capture)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            provider = json.dumps(f"http://127.0.0.1:{server.server_port}/v1")
            options = ["--json", "--skip-git-repo-check", "--ignore-user-config",
                       "-m", "installation-probe", "-c", 'model_provider="reload_probe"',
                       "-c", 'model_providers.reload_probe={name="Offline probe",base_url='
                       + provider + ',wire_api="responses",requires_openai_auth=false}']
            first = call(["codex", "--no-daemon", "exec", *options,
                          "仅核对安装发现，不执行任务。"], env, user, success=False)
            events = [json.loads(line) for line in first.stdout.splitlines()
                      if line.startswith("{")]
            ids = [event["thread_id"] for event in events if event.get("type") == "thread.started"]
            assert ids and requests, first.stdout + first.stderr
            first_tools = json.dumps(requests[-1].get("tools", []))
            assert 'dev-researcher' not in first_tools and 'researcher' in first_tools
            previous = len(requests)
            import sys
            call([sys.executable, str(ROOT / "packages/codex/install.py"), "install",
                  "--home", str(user)], env, user)
            resumed = call(["codex", "--no-daemon", "exec", "resume", *options,
                            ids[0], "仅重新核对新版安装发现，不执行任务。"],
                           env, user, success=False)
            assert len(requests) > previous, resumed.stdout + resumed.stderr
            latest = requests[-1]
            schemas = json.dumps(latest.get("tools", []), ensure_ascii=False)
            for role in ROLES:
                assert role in schemas, f"恢复会话未加载新角色：{role}"
            def strings(value):
                if isinstance(value, str):
                    yield value
                elif isinstance(value, (dict, list)):
                    for child in (value.values() if isinstance(value, dict) else value):
                        yield from strings(child)

            context = "\n".join(strings(latest.get("input", []))).replace("\\", "/")
            for skill in SKILLS:
                assert f"/{skill}/SKILL.md" in context, f"恢复会话未加载新技能：{skill}"
            print("PASS：同一 Codex CLI 聊天在进程退出、安装迁移、resume 后加载全部 8 个新角色及 4 个新技能。")
            print("范围：隔离本地请求捕获；模型故意返回 400；不是桌面旧聊天或业务执行验收。")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
