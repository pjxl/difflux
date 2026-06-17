# Persona: Marcus — The Author

**Persona ID:** `author`
**Type:** Primary
**Status:** Provisional *(synthesis-based; see [research](../research/user-research.md))*
**Last updated:** 2026-06-17

## One-line summary
> A developer who just had an agent generate a sprawling diff and wants to sanity-check
> the *shape* of the change — that it contains what he intended and nothing stray — before
> he pushes or opens a PR.

## Context & environment
Marcus writes code with heavy AI-agent assistance. A single prompt can produce a change
that touches many files at once, mixing the feature he asked for with renames and
incidental cleanup (E2, E13). He works locally in a terminal and reaches difflux at
**pre-push time**, piping his working diff straight in: `git diff … | difflux` (E4). His
diffs are often large enough that eyeballing them in `git diff` is no longer practical
(E3). He's fluent with `git`, env vars, and his LLM provider's API key (E7, E13).

## Goals
- Confirm the change does what he intended — and *only* that — before others see it (E2).
- Catch stray edits (an unintended rename, reformatting noise) before they reach review.
- Open a PR he can stand behind, reducing review back-and-forth.
- Spend seconds, not minutes, on the sanity check.

## Pains & frustrations (today, without difflux)
- An agent-generated diff "interleaves a rename, a core feature, and incidental
  reformatting across dozens of files," and the file tree gives no signal about which is
  which (E2).
- Reviewing his own large diff in file order is as disorienting for him as for any
  reviewer — file order ≠ conceptual order (E1).
- Without a shape-level view, stray or unintended changes slip into the PR and surface as
  review comments later.

## Jobs-To-Be-Done
- When an agent hands me a multi-file diff, I want to see its ideas grouped before I push,
  so I can verify it matches my intent. (E2, E4)
- When I skim the clusters, I want incidental reformatting separated from real logic, so I
  can spot edits I didn't mean to make. (E2)
- When my change is actually small and cohesive, I want the tool to just show it as one
  idea without ceremony, so a quick check stays quick. (E12)

## Behaviors & tools
- Pipes local diffs from stdin rather than fetching PR URLs (E4).
- Iterates: may regenerate the clustering after amending the diff (E6, `r` keybinding).
- Sometimes wants non-interactive output to scan or pipe elsewhere (`--no-tui`) (E5).
- Has an LLM provider account (Anthropic or OpenAI) configured already (E13).

## What success looks like
- He notices a stray rename/reformat *before* pushing, not in a review comment afterward.
- He confirms his intended feature is one coherent cluster, not scattered noise.
- A small, clean change shows as a single idea and he moves on in seconds (E12).
- His PRs arrive tighter, with less "what is this unrelated change?" review churn.

## Anti-goals / non-needs
- Does **not** want difflux to *modify* his diff — it's a read-only shape check, not an
  editor (E11).
- Does **not** want persisted state between runs; each pre-push check is fresh (E11).
- Does **not** want a granularity knob; defaults should be sensible (E11).
- Does **not** need value on tiny diffs to be impressive — he accepts the single-idea path
  is lightweight (E3, E12).

## Open questions / validation status
- Whether authors actually self-review the raw diff pre-push, or only review later in the
  PR web UI (**H3**) — this hypothesis is what makes or breaks this persona.
- Whether the small/cohesive (single_idea) case is genuinely low-stakes for him (**H6**).
- Whether agent-generated diffs are the real trigger vs. any large diff (**H2**).

## Related
- Stories: [`../user-stories/author-stories.md`](../user-stories/author-stories.md)
- Research: [`../research/user-research.md`](../research/user-research.md)
