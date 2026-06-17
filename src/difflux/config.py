import os

DEFAULT_MODEL = os.environ.get("DIFFLUX_MODEL", "claude-opus-4-8")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DIFFLUX_PROVIDER = os.environ.get("DIFFLUX_PROVIDER", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HUNK_CEILING = 300
TOKEN_CEILING = 150_000
