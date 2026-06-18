# AGENTS.md — difflux (semantic change clustering)

This file is for AI coding agents working in this repository. It covers project purpose,
setup, architecture, and invariants that must be preserved. Read it before writing any code.

---

## What this project is

`difflux` is a CLI tool that accepts a git diff (from stdin or a GitHub PR URL) and decomposes
it into conceptual clusters — groups of hunks that belong to the same idea — presented in
a Textual terminal TUI so a reviewer can navigate the change by idea rather than by file.
The tool is built on Python 3.11+, Textual (TUI), Pydantic (schema), and the Anthropic SDK
(Claude, via tool use for structured output).

---

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in ANTHROPIC_API_KEY
```

The entry point is registered as `difflux = "difflux.cli:main"` in `pyproject.toml`.
`python -m difflux` also works via `src/difflux/__main__.py`.

---

## Running tests

```bash
pytest tests/          # full offline suite — no API key needed
python -m difflux          # requires ANTHROPIC_API_KEY and piped diff input
```

To verify the diff parser alone:

```bash
git diff HEAD~1 | python -c "
from difflux.hunks import parse_diff; import sys
for h in parse_diff(sys.stdin.read()): print(h.id, h.file_path, h.new_start)
"
```

---

## Key files

| File | Purpose |
|---|---|
| `src/difflux/config.py` | Module-level constants read from the environment at import: `DEFAULT_MODEL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DIFFLUX_PROVIDER`, `DIFFLUX_BASE_URL`, `GITHUB_TOKEN`, plus `HUNK_CEILING` (300) and `TOKEN_CEILING` (150,000 estimated tokens). Calls `config_file.bootstrap_config()` at import so persisted keys/defaults populate the environment first. Note: `cli.py` also reads `DIFFLUX_*` live from `os.environ` after the first-run wizard, which may have just set them. |
| `src/difflux/config_file.py` | Reads/writes `~/.config/difflux/config.toml` (perms 0o700/0o600). Stores API keys per provider (`[keys.<provider>]`) and persisted defaults (`[defaults]`: provider/base_url/model). `bootstrap_config()` injects both into `os.environ` when unset (env wins); `save_api_key`/`save_defaults`/`load_defaults`/`delete_api_key`/`get_wallet` manage entries. Holds the `#5` org-wrapper TODO. |
| `src/difflux/models.py` | Pydantic models that exactly mirror the JSON the LLM returns via tool use. Contains `Cluster`, `ClusteringResult`, and `ClusteringType`. No locally-derived fields live here — see invariants. |
| `src/difflux/hunks.py` | Parses a unified diff string into `Hunk` dataclass objects with stable 1-based IDs assigned in encounter order. Also defines `HunkIndex`, a `dict[int, Hunk]` wrapper used for ID-keyed lookup at drill-down time. Depends only on stdlib. |
| `src/difflux/prompt.py` | Holds `SYSTEM_PROMPT` verbatim and two functions: `render_hunks(hunks)` produces the numbered hunk block sent to the LLM; `build_user_message(hunks, correction_hint)` wraps it in the user message envelope. |
| `src/difflux/clusterer.py` | Makes the LLM API call. Dispatches to an Anthropic or OpenAI provider (`detect_provider` by model name, or an explicit `provider`); each accepts an optional custom `base_url` for OpenAI/Anthropic-compatible gateways (e.g. LiteLLM). Registers `return_clustering` as the sole tool, forces a tool call, parses the response into a `ClusteringResult`, and validates that all returned hunk IDs exist locally. Raises `ClusteringError` if the LLM does not call the tool. |
| `src/difflux/enrich.py` | Joins `ClusteringResult` with `HunkIndex` to produce `ClusterView` and `ReviewSession` — the view-model layer. Computes `file_count` and `line_count` locally from resolved hunks. These fields are never requested from the model. |
| `src/difflux/render_text.py` | Plain-text fallback renderer used when `--no-tui` is passed or stdout is not a tty. `render_overview(session)` prints the cluster list; `render_cluster(view)` prints a single cluster's hunk content. Never reads `position_rationale`. |
| `src/difflux/cli.py` | Arg parsing (`argparse`: `--model`/`--provider`/`--base-url`/`--no-tui`), input-source dispatch (stdin vs. GitHub PR URL), top-level orchestration. Order matters: drains stdin and reattaches FD 0 to `/dev/tty`, **then** runs the first-run setup wizard if `_needs_setup` (cold start only — never under `--no-tui`/non-tty), resolves model/provider/base_url from live `os.environ`, calls `parse_diff → cluster → build_session`, routes to TUI or text renderer, re-prompts on 401. On TUI exit, prints the session summary line. |
| `src/difflux/__main__.py` | One-liner: `from difflux.cli import main; main()`. Enables `python -m difflux`. |
| `src/difflux/__init__.py` | Empty package marker. |
| `src/difflux/sources/__init__.py` | Empty package marker. |
| `src/difflux/tui/__init__.py` | Empty package marker. |
| `src/difflux/sources/stdin.py` | `read_stdin() -> str` — reads the piped diff from `sys.stdin`. |
| `src/difflux/sources/github.py` | `is_github_pr_url(s)` and `fetch_pr_diff(url, token)` — fetches a unified diff from the GitHub REST API using `Accept: application/vnd.github.v3.diff`. Handles 404 (PR not found / private repo) and 406 (diff too large). |
| `src/difflux/tui/app.py` | `DiffluxApp(App)` — Textual application root. Routes on mount: `single_idea` goes to `SingleIdeaScreen`; `multi_cluster` goes to `OverviewScreen`. Holds the `regenerate` callback passed in from `cli.py`. |
| `src/difflux/tui/overview.py` | `OverviewScreen` — phase-one navigable cluster list. Keybindings: `j`/`k` navigate, `Enter` drills in, `Space` toggles reviewed, `r` regenerates (via `asyncio.to_thread` + Textual worker so the event loop is never blocked), `?` toggles help, `q`/`Esc` quits. |
| `src/difflux/tui/drilldown.py` | `DrillDownScreen` — phase-two view of a single cluster's hunks. `SingleIdeaScreen` — shown when `clustering_type` is `single_idea`; displays the `note` and raw hunks without a navigable overview. |
| `src/difflux/tui/widgets.py` | `ClusterCard` — one cluster row in the overview list, renders name/summary/metadata, tracks focus and reviewed state. `HunkBlock` — renders a single hunk with `rich.syntax.Syntax` diff highlighting. `HelpModal` — keyboard shortcut overlay. |
| `src/difflux/tui/key_entry.py` | `KeyEntryApp` — first-run single-key entry modal (neutral framing when a custom base URL is configured). `WalletModal`/`KeyEditModal` — view/add/edit/delete stored keys per provider, opened via the `K` keybinding in the overview. |
| `src/difflux/tui/setup.py` | `SetupWizardApp` — first-run setup wizard (Direct Anthropic / Direct OpenAI / Custom gateway → model → key); thin UI returning a `SetupResult`. `apply_setup(result)` persists via `config_file.save_defaults` + `save_api_key`. A custom gateway routes through the OpenAI-compatible provider. |
| `tests/test_hunks.py` | Tests for `parse_diff` and `HunkIndex`. Covers: empty diff returns `[]`, sequential IDs starting at 1, correct file path extraction from `+++` line, deletion fallback to `a/`-side path, IDs incrementing across files, line number parsing, body content, verbatim header string, and `HunkIndex.by_ids` ordering and missing-ID handling. Uses inline diff strings; no fixture files loaded. |
| `tests/test_models.py` | Tests for Pydantic schema validation. Covers: `multi_cluster` and `single_idea` result parse, cluster field access, `position_rationale` present in JSON schema, `file_count`/`line_count`/`position` absent from JSON schema, `too_large` not a valid `ClusteringType` value (raises `ValidationError`), `note` defaults to `None`, `coverage` optional. Uses inline Python dicts, not JSON strings or fixture files. |
| `tests/test_prompt.py` | Tests for `SYSTEM_PROMPT`, `render_hunks`, and `build_user_message`. Covers: prompt is a non-empty string with required keywords (`CONCEPTUAL CLUSTERS`, `return_clustering`, `single_idea`, `position_rationale`, `ESCAPE HATCH`), `render_hunks` includes hunk ID/file/line/header/body, uses en-dash (`–`) in line ranges, separates hunks with blank lines, `build_user_message` includes hunk count and file count, omits `CORRECTION HINT` when not provided and includes it when provided, `render_hunks` never emits `position_rationale`. Uses `Hunk` objects constructed inline. |
| `tests/test_enrich.py` | Tests for `build_session`. Covers: returns `ReviewSession`, `ClusterView.hunks` resolved from `HunkIndex`, `file_count` computed from unique file paths (not from model), `line_count` counts `+` and `-` lines but not context lines, `total_files` across clusters, `total_hunks`, `reviewed` defaults to `False`, `position_rationale` not a top-level attribute of `ClusterView` (only accessible via `.cluster.position_rationale`), `single_idea` clustering type propagated. Uses `Hunk` and `Cluster` objects constructed inline. |
| `tests/test_clusterer.py` | Tests `detect_provider` (model name → provider) and that a custom `base_url` is forwarded to both the Anthropic and OpenAI SDK clients. |
| `tests/test_config_file.py` | Tests `[defaults]` persistence: round-trip, partial merge, immediate `os.environ` injection, `bootstrap_config` population (env wins over persisted), and keys + defaults coexisting in one file. |
| `tests/test_setup.py` | Tests `apply_setup` persistence calls, the `_needs_setup` truth table, and Pilot-driven wizard flows (gateway / direct / cancel). |
| `tests/test_cli.py` | Tests `main()` ordering: the setup wizard runs only after stdin is drained and FD 0 is reattached to `/dev/tty`, and is skipped when setup isn't needed. |
| `tests/fixtures/` | `diff1_tui_rail.diff`, `diff2_editorial.diff`, `diff3_pci_tokens.diff` — reference diffs for manual testing. Unit tests do not load from these files; they embed their own diff strings inline. |

---

## Architecture

### Dependency flow

Dependencies flow downward only. Nothing in `hunks`, `models`, `prompt`, `clusterer`, or
`enrich` imports from `cli` or `tui`. The TUI is a consumer of `enrich`'s output, not a
peer of the core pipeline.

```
config  ←──────────────────── clusterer imports config for DEFAULT_MODEL, ceilings
hunks   (stdlib only)
  └── prompt
models
  └── clusterer (anthropic SDK, imports config + prompt + models + hunks)
  └── enrich    (imports models + hunks)
        ├── render_text
        └── tui/
              ├── app
              ├── overview
              ├── drilldown
              └── widgets
cli (top-level orchestrator — imports config, hunks, clusterer, enrich, render_text, tui)
sources/stdin   (stdlib only)
sources/github  (httpx)
```

### Data pipeline

```
stdin / GitHub PR URL
  → parse_diff(diff_text) → list[Hunk]          (hunks.py)
  → HunkIndex(hunks)                              (hunks.py)
  → cluster(hunks, model, api_key)               (clusterer.py)
      → render_hunks(hunks) → user message        (prompt.py)
      → Anthropic SDK: tool_use → ClusteringResult (models.py, Pydantic)
  → build_session(result, index) → ReviewSession  (enrich.py)
  → DiffluxApp(session, regenerate).run()             (tui/)
      OR render_overview(session)                  (render_text.py)
```

### Why hunk content stays local

The LLM receives numbered hunks with full content in the user message but returns **hunk
IDs only** — no content is echoed back. The `ClusteringResult` holds only IDs (integers)
in each `Cluster.hunk_ids`. Content is joined back at drill-down time by calling
`HunkIndex.by_ids(cluster.hunk_ids)`. This keeps the response payload small, avoids
hallucinated content mutations, and makes the schema validation simple: bad IDs are caught
by `_validate_hunk_ids` in `clusterer.py` before any rendering happens.

### Truncation

Before the LLM call, `clusterer.py` truncates the hunk list if it exceeds `HUNK_CEILING`
(300 hunks) or if the estimated token count (`len(rendered) // 4`) exceeds `TOKEN_CEILING`
(150,000). Truncation drops hunks from the end and prints a warning to stderr. There is no
second pass in v1.

### TUI regeneration

`r` in the overview calls `OverviewScreen.action_regen()`, which runs the full
`cluster → build_session` pipeline in a thread via `asyncio.to_thread` inside a Textual
worker. A `LoadingIndicator` is mounted during the call. On completion, a
`ClusteringComplete` message replaces the session and rebuilds the list. The event loop is
never blocked.

---

## Invariants to preserve

These are hard constraints. Do not violate them.

### `models.py` is LLM output schema only

`file_count`, `line_count`, and `position` are **not** in `Cluster` or `ClusteringResult`.
They are computed locally in `enrich.py` after the LLM call returns. Adding them to
`models.py` breaks the design contract: the model would need to produce them, they would be
duplicated, and the Pydantic schema sent to the API would include fields the LLM cannot
reliably populate.

### `position_rationale` is internal — never render it

`Cluster.position_rationale` exists in the schema because it improves LLM ordering quality
as chain-of-thought scaffolding (the LLM writes its reasoning here before deciding order).
It must **never** be read or displayed by any render path. `render_text.py` does not access
it. No widget in `tui/` reads or displays it. If you add a new render path, do not include
`position_rationale`.

### `ClusteringType` has exactly two members

`ClusteringType` is `StrEnum` with `MULTI_CLUSTER = "multi_cluster"` and
`SINGLE_IDEA = "single_idea"`. Do not add `too_large` or any other member in v1. The
two-pass chunking approach that would use `too_large` is explicitly out of scope for v1.
The comment `# "too_large" is intentionally NOT in the v1 enum` in `models.py` is
intentional — leave it.

### `tool_choice={"type": "any"}` — do not change the API call pattern

`clusterer.py` registers exactly one tool (`return_clustering`) and passes
`tool_choice={"type": "any"}`. This is the reliable path to forcing a tool call rather
than prose. Do not change to `tool_choice={"type": "tool", "name": "..."}`, do not add
a second tool, and do not attempt to parse prose fallback JSON. If the LLM does not call
the tool, `ClusteringError` is raised — that is correct behavior.

### Hunk IDs are stable within a session

`parse_diff` assigns IDs 1-based in encounter order across the entire diff (not per-file).
The IDs are stable because they derive purely from parse order of an immutable input. The
LLM references these IDs in `hunk_ids`; `_validate_hunk_ids` checks them; `HunkIndex`
looks up content by them. If you change how `parse_diff` assigns IDs, prompt/schema tests
will break and existing cached LLM results will reference wrong hunks.

### Tests use inline diff strings — not fixture files

`test_hunks.py`, `test_models.py`, `test_prompt.py`, and `test_enrich.py` embed their own
diff strings and JSON inline. The files in `tests/fixtures/` are reference material, not
test input. Do not refactor tests to load from fixture files — the inline approach keeps
tests self-contained and offline.

---

## What v1 explicitly excludes

Do not implement these. They are out of scope.

- **`too_large` clustering type / two-pass chunking.** v1 truncates at the hunk ceiling
  with a warning. The sketch+detail two-pass approach is v1.5.
- **Directed regeneration.** `r` is a plain re-run. The `correction_hint` parameter in
  `build_user_message` and `cluster()` is wired but unused in v1. Do not add a UI to
  collect a correction hint.
- **Manual cluster editing in the TUI.** No dragging hunks between clusters, merging,
  splitting, or renaming. Not in v1.
- **Persisted review state.** Reviewed checkboxes are in-memory and session-local. No
  review log, no file on disk, no sync. The only trace is the stdout summary line on exit.
- **`--granularity` flag.** The prompt's built-in 4–8 cluster preference handles this. Do
  not add `--granularity`, `--clusters N`, or similar flags.
- **Keyword filter (`/`).** The `/` keybinding is reserved but not implemented.
- **Streaming LLM output into the TUI.** v1 does one blocking call (offloaded to a thread)
  with a spinner. The full response is available before any rendering begins.
- **Caching LLM results across sessions or multi-model fallback.**
