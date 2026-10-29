#!/usr/bin/env python3
"""Portable launcher; discovers standard tools and optional Codex bundled runtimes."""

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def runtime_env():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["VITALROUTE_HOME"] = str(ROOT)
    env["PYSPARK_PYTHON"] = str(ROOT / ".venv/bin/python")
    env.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    java = list((ROOT / ".tools").glob("jdk-*/Contents/Home")) + [
        p for p in (ROOT / ".tools").glob("jdk-*") if (p / "bin/java").exists()
    ]
    if not env.get("JAVA_HOME") and java:
        env["JAVA_HOME"] = str(java[0])
    nodes = [
        str(ROOT / ".tools/node/bin"),
        str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"),
    ]
    env["PATH"] = os.pathsep.join(nodes + [env.get("PATH", "")])
    return env

def main():
    os.chdir(ROOT)
    env = runtime_env()
    python = str(ROOT / ".venv/bin/python")
    if not Path(python).exists():
        sys.exit("Run make setup first.")
    command = sys.argv[1] if len(sys.argv) > 1 else "start"
    if command == "build":
        node = shutil.which("node", path=env["PATH"])
        if not node:
            sys.exit("Node.js 22+ is required. Run make setup.")
        for tool, args in [("typescript/bin/tsc", ["-b"]), ("vite/bin/vite.js", ["build"])]:
            subprocess.run(
                [node, str(ROOT / "frontend/node_modules" / tool), *args],
                cwd=ROOT / "frontend",
                env=env,
                check=True,
            )
    elif command == "test":
        subprocess.run([python, "-m", "pytest", "-q", *sys.argv[2:]], env=env, check=True)
    elif command == "evaluate":
        subprocess.run([python, "tools/evaluate.py", *sys.argv[2:]], env=env, check=True)
    elif command == "start":
        if not (ROOT / "frontend/dist/index.html").exists():
            subprocess.run([sys.executable, __file__, "build"], check=True)
        if "--no-browser" not in sys.argv:
            import threading

            threading.Timer(2, lambda: webbrowser.open("http://127.0.0.1:8180")).start()
        print("VitalRoute: http://127.0.0.1:8180 · Ctrl+C to stop", flush=True)
        subprocess.run(
            [
                python,
                "-m",
                "uvicorn",
                "vitalroute.api.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                "8180",
            ],
            env=env,
        )
    else:
        sys.exit("Use start, build, test, or evaluate")

if __name__ == "__main__":
    main()
