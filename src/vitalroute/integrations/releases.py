"""Commit tested code and materialize an immutable local release."""

import json
import shutil
import subprocess

from ..pipeline.source import sha

def deploy_release(root, candidate, proposal):
    release = root / "release"
    release.mkdir(exist_ok=True)

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(release), *args], stderr=subprocess.STDOUT, text=True
        ).strip()

    if not (release / ".git").exists():
        git("init", "-b", "recovery")
        git("config", "user.name", "VitalRoute Recovery Agent")
        git("config", "user.email", "recovery@vitalroute.local")
        shutil.copy2(root / "baseline.py", release / "transform.py")
        git("add", "transform.py")
        git("commit", "-m", "Baseline incident transformation")
    shutil.copy2(candidate, release / "transform.py")
    git("add", "transform.py")
    if git("diff", "--cached", "--name-only"):
        git("commit", "-m", f"Repair: {proposal['label']}")
    commit = git("rev-parse", "HEAD")
    bundle = root / "deployments" / commit
    bundle.mkdir(parents=True, exist_ok=True)
    shutil.copy2(release / "transform.py", bundle / "transform.py")
    manifest = {
        "commit": commit,
        "code_sha256": sha(bundle / "transform.py"),
        "proposal_digest": proposal["digest"],
        "mode": "local",
        "github_push": False,
        "databricks_deploy": False,
        "file": str(bundle / "transform.py"),
    }
    (bundle / "release.json").write_text(json.dumps(manifest, indent=2))
    return manifest
