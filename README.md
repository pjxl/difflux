# scc — semantic change clustering

Decompose a git diff into conceptual clusters for review.

## The problem

Standard diff tools present changes in file order. File order has no relationship to conceptual order or to where the risk lives. A 40-file agent-generated PR might interleave a rename, a core feature, and incidental reformatting across dozens of files — and the file tree gives you no signal about which is which, or what to read first.

`scc` sends the diff to a language model, which identifies the conceptual clusters, assigns each hunk to one, and orders them in the sequence that builds understanding. You see the shape of the change before you read a line of it.

## Example

Consider a commit that changes how Enter behaves in a slash-command completion dropdown: previously Enter accepted the highlighted completion (same as Tab); after the change it accepts *and* immediately submits. The diff touches two files across four hunks.

A conventional diff presents them in file order — `tests/test_tui.py` first, then `tui.py` — so you read the updated test assertions before you've seen the implementation change that makes that behavior possible.

`scc` reorders the same hunks into three clusters:

```
1. Core behavior change        tui.py · 1 hunk
   action_submit now calls action_complete_or_focus() unconditionally;
   Enter collapses completion and submit into one keystroke.

2. User-facing signals         tui.py · 2 hunks
   Dropdown hint updated from "tab" to "tab complete · enter run";
   ChatInput docstring updated to reflect the new Enter/Tab contract.

3. Test verification           tests/test_tui.py · 1 hunk
   Test renamed and assertions updated to confirm input clears and a
   new message appears rather than the old /help residue check.
```

In a two-file diff the gain is modest. In a 50-file agent PR the reordering is the difference between understanding the change and reading it.

## Installation

```sh
pipx install scc
```

Or with pip:

```sh
pip install scc
```

Requires Python 3.11+.

## Setup

Set your Anthropic API key:

```sh
export ANTHROPIC_API_KEY=sk-ant-...
```

For private GitHub repositories, also set:

```sh
export GITHUB_TOKEN=ghp_...
```

## Usage

Pipe a diff from stdin (primary mode):

```sh
git diff HEAD~1 | scc
git diff main...feature-branch | scc
```

Pass a GitHub PR URL directly:

```sh
scc https://github.com/owner/repo/pull/123
```

For plain-text output instead of the TUI:

```sh
git diff HEAD~1 | scc --no-tui
```

## Keybindings

| Key | Action |
|-----|--------|
| `j` / `↓` | Move down |
| `k` / `↑` | Move up |
| `Enter` | Drill into cluster |
| `Space` | Mark cluster reviewed |
| `r` | Regenerate clusters |
| `Esc` / `q` | Back / quit |
| `?` | Help |

## How it works

`scc` numbers each hunk in the diff and sends them to a Claude model with a structured-output prompt. The model identifies conceptual clusters, assigns each hunk to one, orders the clusters in the reading sequence that best builds understanding (entry point → core logic → edge handling → tests), and writes a one-sentence summary per cluster. The result is a two-phase TUI: an overview listing all clusters with their summaries, hunk counts, and file counts; and a drill-down view that shows the actual diff hunks for a selected cluster, gathered from wherever in the file tree they happen to live.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `GITHUB_TOKEN` | No | GitHub personal access token for private repos |
| `SCC_MODEL` | No | Claude model to use (default: `claude-opus-4-8`) |
