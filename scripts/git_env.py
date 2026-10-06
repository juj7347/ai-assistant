#!/usr/bin/env python3
"""Run Git with the project's origin and GitHub credentials from .env."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def read_project_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.is_file():
        raise SystemExit(f"Missing {ENV_FILE}; copy .env.example to .env first.")

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key, value = key.strip(), value.strip()
        if value[:1] in ("'", '"') and value[-1:] == value[:1]:
            value = value[1:-1]
        values[key] = value

    origin = values.get("GIT_ORIGIN_URL", "")
    parsed = urlparse(origin)
    if parsed.scheme != "https" or not parsed.hostname:
        raise SystemExit("GIT_ORIGIN_URL must be an HTTPS repository URL in .env.")
    if parsed.username or parsed.password:
        raise SystemExit("Keep credentials out of GIT_ORIGIN_URL; use GITHUB_TOKEN.")
    return values


def askpass(prompt: str, values: dict[str, str]) -> int:
    if urlparse(values["GIT_ORIGIN_URL"]).hostname != "github.com":
        print("")
    elif "username" in prompt.lower():
        print("x-access-token")
    elif "password" in prompt.lower():
        print(values.get("GITHUB_TOKEN", ""))
    else:
        print("")
    return 0


def run_git(args: list[str], values: dict[str, str]) -> int:
    if not args:
        raise SystemExit("Usage: python scripts/git_env.py <git arguments>")

    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    origin_url = values["GIT_ORIGIN_URL"]
    if remote.returncode:
        subprocess.run(["git", "remote", "add", "origin", origin_url], cwd=ROOT, check=True)
    elif remote.stdout.strip() != origin_url:
        subprocess.run(["git", "remote", "set-url", "origin", origin_url], cwd=ROOT, check=True)

    env = os.environ.copy()
    env["GIT_ORIGIN_URL"] = origin_url
    env["GITHUB_TOKEN"] = values.get("GITHUB_TOKEN", "")
    env["GIT_ASKPASS"] = str(Path(__file__).resolve())
    env["GIT_ASKPASS_REQUIRE"] = "force"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git", "-c", "credential.helper=", *args], cwd=ROOT, env=env, check=False
    ).returncode


def main() -> int:
    values = read_project_env()
    if os.environ.get("GIT_ASKPASS") == str(Path(__file__).resolve()):
        return askpass(sys.argv[1] if len(sys.argv) > 1 else "", values)
    return run_git(sys.argv[1:], values)


if __name__ == "__main__":
    raise SystemExit(main())
