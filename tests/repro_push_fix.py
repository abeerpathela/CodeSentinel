"""Regression test — fresh-source deploy from shallow-clone workspace."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _make_shallow_mock(workspace: Path) -> None:
    git_dir = workspace / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "shallow").write_text("deadbeef\n", encoding="utf-8")
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "config").write_text(
        "[core]\n\trepositoryformatversion = 0\n",
        encoding="utf-8",
    )
    (workspace / "app.py").write_text("print('audit snapshot')\n", encoding="utf-8")
    (workspace / "README.md").write_text("# shallow mock\n", encoding="utf-8")


def main() -> None:
    from core.github_deploy import (
        COMMIT_MESSAGE,
        deploy_fresh_source,
        is_shallow_repository,
        purge_git_metadata,
    )
    from core.github_handler import GitHubHandler

    handler = GitHubHandler()
    tmp_root = Path(tempfile.mkdtemp(prefix="codesentinel_push_"))
    workspace = tmp_root / "workspace"
    bare_origin = tmp_root / "origin.git"
    workspace.mkdir()

    try:
        _make_shallow_mock(workspace)
        rel_ws = workspace.relative_to(ROOT) if workspace.is_relative_to(ROOT) else workspace.name
        print(f"[OK] Shallow mock workspace at {rel_ws}")
        assert (workspace / ".git" / "shallow").is_file(), "shallow marker missing"

        init_bare = subprocess.run(
            ["git", "init", "--bare", str(bare_origin)],
            capture_output=True,
            text=True,
            check=False,
        )
        if init_bare.returncode != 0:
            print(f"[FAIL] Could not create bare origin: {init_bare.stderr}", file=sys.stderr)
            sys.exit(1)

        origin_url = bare_origin.as_uri()
        steps: list[str] = []

        deploy_fresh_source(
            workspace,
            origin_url,
            on_progress=lambda msg: steps.append(msg),
        )

        assert not (workspace / ".git" / "shallow").exists(), "shallow file should be gone"
        assert not is_shallow_repository(workspace), "repository must not be shallow after fresh init"
        print("[OK] Fresh repository is not shallow (git rev-parse --is-shallow-repository = false)")

        expected_steps = (
            "🧹 Scrubbing Metadata",
            "🔨 Initializing",
            "🚀 Pushing",
        )
        for fragment in expected_steps:
            assert any(fragment in s for s in steps), f"missing progress step: {fragment}"
        print("[OK] Deploy progress chain emitted scrub -> init -> push")

        log = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        )
        assert COMMIT_MESSAGE in log.stdout.strip(), "commit message mismatch"
        print(f"[OK] Local commit message: {COMMIT_MESSAGE}")

        remote_head = subprocess.run(
            ["git", "rev-parse", "main"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        bare_head = subprocess.run(
            ["git", "rev-parse", "refs/heads/main"],
            cwd=bare_origin,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "GIT_DIR": str(bare_origin)},
        ).stdout.strip()
        assert remote_head == bare_head, "push did not update bare origin main"
        print("[OK] init -> add -> commit -> push sequence succeeded against bare origin")

        purge_git_metadata(workspace)
        assert not (workspace / ".git").exists(), "purge should remove .git"
        print("[OK] purge_git_metadata removes shallow .git cleanly")

        print("\n=== repro_push_fix PASSED ===")
    finally:
        handler.cleanup(tmp_root)


if __name__ == "__main__":
    main()
