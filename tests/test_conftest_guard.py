"""Regression tests for the live-checkout git mutation interlock (#90182)."""

import subprocess

import pytest

# Import the fixture module directly so its pure guard helper can be tested.
from tests import conftest


@pytest.mark.parametrize(
    ("command", "cwd", "blocked"),
    [
        # These cases prove the live checkout and its descendants are protected.
        (["git", "checkout", "topic"], "PROJECT_ROOT", True),
        (["git", "reset", "--hard"], None, True),
        (["git", "-C", "PROJECT_ROOT", "clean", "-fd"], ".", True),
        (["git", "--work-tree=PROJECT_ROOT", "add", "x"], ".", True),
        (["git", "-C", "PROJECT_ROOT", "status"], "PROJECT_ROOT", False),
        # A temporary repository remains a valid fixture target for mutating tests.
        (["git", "-C", "/tmp/90182-repo", "checkout", "topic"], "/tmp", False),
        # Non-git subprocesses must retain their existing behavior.
        (["python", "-c", "pass"], "PROJECT_ROOT", False),
        (["git", "-C", "PROJECT_ROOT", "fetch"], "PROJECT_ROOT", True),
        (["git", "-C", "/tmp/90182-repo", "push"], "/tmp", False),
    ],
)
def test_git_guard_target_matrix(monkeypatch, command, cwd, blocked):
    """Reject only protected git mutations without spawning a subprocess."""
    root = str(conftest.PROJECT_ROOT)
    command = [root if item == "PROJECT_ROOT" else item for item in command]
    cwd = root if cwd == "PROJECT_ROOT" else cwd
    if cwd == ".":
        cwd = root + "/tests"
    if cwd is None:
        monkeypatch.chdir(root)

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append(args))
    if blocked:
        with pytest.raises(RuntimeError, match="git"):
            conftest._check_git_subprocess_cmd("run", command, cwd=cwd)
        assert calls == []  # The rejection must happen before subprocess.run.
    else:
        conftest._check_git_subprocess_cmd("run", command, cwd=cwd)


def test_git_guard_threads_cwd_through_run_and_popen(monkeypatch, tmp_path):
    """Pass cwd into both wrappers so target resolution matches the child process."""
    seen = []

    def record(name, command, cwd):
        seen.append((name, cwd))

    monkeypatch.setattr(conftest, "_check_git_subprocess_cmd", record)
    subprocess.run(["true"], cwd=tmp_path)
    process = subprocess.Popen(["true"], cwd=tmp_path)
    process.wait()
    # run delegates to Popen, so both wrapper layers must carry the same cwd.
    assert seen == [("run", tmp_path), ("Popen", tmp_path), ("Popen", tmp_path)]
