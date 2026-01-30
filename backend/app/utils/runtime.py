import os
import platform
import subprocess
from typing import Optional


def runtime_context(project_root: str) -> dict:
    ctx = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": None,
    }
    git_dir = project_root
    try:
        commit = subprocess.check_output(["git", "-C", git_dir, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        ctx["git_commit"] = commit.decode().strip()
    except Exception:
        ctx["git_commit"] = None
    return ctx


def provider_runtime_info(base_url: Optional[str], timeout_s: float, retries: int, temperature: float, max_tokens: int) -> dict:
    return {
        "base_url": base_url,
        "timeout_s": timeout_s,
        "retries": retries,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
