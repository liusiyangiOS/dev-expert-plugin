from pathlib import Path
import hashlib, json, os, subprocess, sys, tempfile
ROOTS = {"product": Path("/Users/liusiyang/Documents/GitHubOfMine/product-expert-plugin"), "dev": Path("/Users/liusiyang/Documents/GitHubOfMine/dev-expert-plugin")}
BASES = {"product": "9dc152fce02f76e596546c3532558a99f7468ad0", "dev": "b91de1a6ec07fbe3a0d36ede06fd333b3cb3e3d0"}
sys.path.insert(0,str(ROOTS["dev"] / "tests"))
from support import isolated_environment

def call(args, env, cwd):
 p=subprocess.run(args,env=env,cwd=cwd,text=True,capture_output=True)
 if p.returncode: raise RuntimeError(str(args)+"\n"+p.stdout+"\n"+p.stderr)
 return p.stdout

results={}
with tempfile.TemporaryDirectory(prefix="dual-expert-upgrade-") as tmp:
 base=Path(tmp); old={}
 for name,repo in ROOTS.items():
  dst=base/(name+"-old");dst.mkdir();old[name]=dst
  names=subprocess.check_output(["git","ls-tree","-r","--name-only",BASES[name],"packages"],cwd=repo,text=True).splitlines()
  for namepath in names:
   file=dst/namepath;file.parent.mkdir(parents=True,exist_ok=True)
   file.write_bytes(subprocess.check_output(["git","show",BASES[name]+":"+namepath],cwd=repo))
 for host in ("codex","claude"):
  home=base/(host+" 中文 home");home.mkdir();env=isolated_environment(home)
  for source in (old,ROOTS):
   for name in ("product","dev"):
    call([sys.executable,str(source[name]/"packages"/host/"install.py"),"install","--home",str(home)],env,home)
  checks={name:call([sys.executable,str(repo/"packages"/host/"install.py"),"check","--home",str(home)],env,home).strip() for name,repo in ROOTS.items()}
  states={}
  for name,folder in (("product","product-expert-team"),("dev","expert-team")):
   manifest=home/("."+host)/folder/"install-manifest.json";m=json.loads(manifest.read_text())
   assert all(hashlib.sha256((home/f).read_bytes()).hexdigest()==h for f,h in m["files"].items())
   assert list((manifest.parent/"backups").glob("*/manifest.json"))
   states[name]={"version":m["version"],"files":len(m["files"])}
  results[host]={"checks":checks,"states":states,"old_to_new_coexist":True}
print(json.dumps(results,ensure_ascii=False,indent=2))
