from __future__ import annotations

import re

import httpx

_PR_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)


def is_github_pr_url(s: str) -> bool:
    return bool(_PR_PATTERN.match(s.strip()))


def fetch_pr_diff(url: str, *, token: str | None = None) -> str:
    m = _PR_PATTERN.match(url.strip())
    if not m:
        raise ValueError(f"Not a GitHub PR URL: {url}")
    owner, repo, number = m["owner"], m["repo"], m["number"]
    headers = {"Accept": "application/vnd.github.v3.diff"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}",
            headers=headers,
            follow_redirects=True,
            timeout=30,
        )
    except httpx.RequestError as e:
        raise RuntimeError(f"Network error fetching PR diff: {e}") from e

    if resp.status_code == 404:
        raise RuntimeError("PR not found. Check the URL and set GITHUB_TOKEN for private repos.")
    if resp.status_code == 406:
        raise RuntimeError("GitHub diff too large. Use: git diff | difflux instead.")
    resp.raise_for_status()
    return resp.text
