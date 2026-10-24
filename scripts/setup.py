#!/usr/bin/env python3
"""Install project-local tools. Never installs a cloud job or paid service."""

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"


def archive(url, name):
    target = TOOLS / name
    print("Downloading " + name, flush=True)
    urllib.request.urlretrieve(url, target)
    with tarfile.open(target) as tar:
        if sys.version_info >= (3, 12):
            tar.extractall(TOOLS, filter="data")
        else:
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in Path(member.name).parts:
                    raise RuntimeError("Unsafe archive path")
            tar.extractall(TOOLS)
    target.unlink()


def main():
    TOOLS.mkdir(exist_ok=True)
    system = "mac" if platform.system() == "Darwin" else "linux"
    arch = "aarch64" if platform.machine() in ("arm64", "aarch64") else "x64"
    if not os.getenv("JAVA_HOME") and not list(TOOLS.glob("jdk-*")):
        archive(
            f"https://api.adoptium.net/v3/binary/latest/17/ga/{system}/{arch}/jdk/hotspot/normal/eclipse",
            "java.tar.gz",
        )
    if not (ROOT / ".venv/bin/python").exists():
        candidates = [
            sys.executable,
            shutil.which("python3.12"),
            shutil.which("python3.11"),
            str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"),
        ]
        chosen = None
        for python in candidates:
            if (
                python
                and Path(python).exists()
                and subprocess.run(
                    [python, "-c", "import sys; sys.exit(sys.version_info < (3,11))"], capture_output=True
                ).returncode
                == 0
            ):
                chosen = python
                break
        if not chosen:
            sys.exit("Install Python 3.11+ and rerun make setup.")
        subprocess.run([chosen, "-m", "venv", str(ROOT / ".venv")], check=True)
    subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "pip", "install", "-r", str(ROOT / "requirements.lock")],
        check=True,
    )
    subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "pip", "install", "-e", str(ROOT), "--no-deps"], check=True
    )
    from run import runtime_env

    env = runtime_env()
    node = shutil.which("node", path=env["PATH"])
    if not node:
        # Resolve LTS dynamically rather than require a globally installed package manager.
        releases = json.load(urllib.request.urlopen("https://nodejs.org/dist/index.json"))
        release = next(r for r in releases if r["lts"] and int(r["version"].split(".")[0][1:]) >= 22)
        node_arch = "arm64" if arch == "aarch64" else "x64"
        node_os = "darwin" if system == "mac" else "linux"
        folder = f"node-{release['version']}-{node_os}-{node_arch}"
        archive(f"https://nodejs.org/dist/{release['version']}/{folder}.tar.gz", "node.tar.gz")
        (TOOLS / folder).rename(TOOLS / "node")
        env = runtime_env()
    npm = shutil.which("npm", path=env["PATH"])
    pnpm = shutil.which("pnpm", path=env["PATH"]) or str(
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm"
    )
    if npm:
        subprocess.run([npm, "install"], cwd=ROOT / "frontend", env=env, check=True)
    elif Path(pnpm).exists():
        subprocess.run([pnpm, "install"], cwd=ROOT / "frontend", env=env, check=True)
    else:
        sys.exit("Install npm or pnpm, then run it in frontend/.")
    if not (ROOT / ".env").exists():
        shutil.copy2(ROOT / ".env.example", ROOT / ".env")
    subprocess.run([sys.executable, str(ROOT / "scripts/run.py"), "build"], check=True)
    print("Ready. Run make start. Optional local model: ollama pull qwen3:8b", flush=True)


if __name__ == "__main__":
    main()
