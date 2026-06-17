import os

DEFAULT_MODEL = os.environ.get("DIFFLUX_MODEL", "claude-opus-4-8")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HUNK_CEILING = 300
TOKEN_CEILING = 150_000
