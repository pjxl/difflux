# Persona: Priya — The Reviewer

**Persona ID:** `reviewer`
**Type:** Primary
**Status:** Provisional *(synthesis-based; see [research](../research/user-research.md))*
**Last updated:** 2026-06-17

## One-line summary
> A developer who has to understand a large, often agent-generated PR well enough to
> approve it or send it back — and can't tell from the file tree what matters or what to
> read first.

## Context & environment
Priya is a working software engineer who reviews other people's pull requests as a routine
part of her week. Increasingly the PRs landing in her queue were produced by an AI agent:
they're large, span many files, and interleave unrelated concerns. She's comfortable in a
terminal, uses `git` directly, manages API keys and tokens via environment variables, and
keyboard-drives her tools (E6, E7). She encounters difflux at **review time**, entering
either through a GitHub PR URL or by piping a diff (E4, E8). The PRs that hurt are the big
ones — a 40–50 file change is the canonical case (E2, E3).

## Goals
- Understand *what a change actually does* before approving it.
- Find where the **risk** lives quickly, and spend her attention there (E1).
- Separate the substantive change from incidental noise (renames, reformatting) (E2).
- Get to a confident approve / request-changes decision without reading every file in
  tree order.

## Pains & frustrations (today, without difflux)
- File-order diffs have "no relationship to conceptual order or to where the risk lives"
  (E1) — so she has no signal about where to start.
- On a large agent PR, a rename, a core feature, and incidental reformatting are smeared
  across dozens of files and the file tree won't tell her which is which (E2).
- The pain grows with size: at ~50 files, file-by-file reading is "the difference between
  understanding the change and reading it" (E3).
- She often reads updated tests before the implementation that motivates them, because
  that's where file order put them (README §"Example").

## Jobs-To-Be-Done
- When I open a large unfamiliar PR, I want it grouped by idea and ordered for
  understanding, so I can decide what to read first instead of guessing. (E1, E8)
- When a diff mixes real logic with reformatting, I want the substantive clusters
  separated from the noise, so I don't waste scrutiny on whitespace. (E2)
- When I'm partway through a big review, I want to track which ideas I've already checked,
  so I can stop and resume without losing my place. (E6, E11)

## Behaviors & tools
- Terminal-resident; reviews from the CLI and is willing to invoke a TUI (E6).
- Pulls others' changes via GitHub PR URL, including private repos (needs `GITHUB_TOKEN`)
  (E4, E7, E10).
- Has an LLM provider account already (Anthropic or OpenAI) and expects to use it (E13).
- Routinely handles changes large enough to approach the tool's ceilings (E9).

## What success looks like
- She reads the highest-risk cluster first and reaches an approve / request-changes
  decision faster than file-by-file.
- She can articulate the *shape* of the PR (its 4–8 ideas) after the overview, before
  reading any hunk.
- Incidental reformatting is visibly quarantined from real logic.
- On an oversized PR she gets a clear, graceful signal rather than silent truncation or a
  crash (E9, E10).

## Anti-goals / non-needs
- Does **not** want to manually re-cluster, merge, split, or rename groups in v1 — she
  wants a good first cut, not an editing surface (E11).
- Does **not** need her review state persisted across sessions; in-memory tracking within
  a sitting is enough (E11).
- Does **not** want a knob for cluster count/granularity; sensible defaults are expected
  (E11).
- Does **not** need streaming output — a short wait with a clear result is fine (E11).

## Open questions / validation status
- Whether file-order review actually breaks down at a size threshold for her (**H1**), and
  whether the acute trigger is *agent-generated* PRs specifically vs. large PRs generally
  (**H2**).
- Whether a terminal/TUI fits her review workflow or competes with the web PR UI (**H4**).
- Whether a good first-cut clustering is enough, or she'll demand to edit groupings before
  trusting it (**H5**).

## Related
- Stories: [`../user-stories/reviewer-stories.md`](../user-stories/reviewer-stories.md)
- Research: [`../research/user-research.md`](../research/user-research.md)
