# difflux — Product Documentation

This directory holds the **product reference layer** for difflux: who it's for and what it
must do for them. The repo's engineering docs (`../README.md`, `../AGENTS.md`) describe
*how the system works*; these documents describe *who it serves and why*, and exist to be
the durable, citable inputs to **spec-driven development (SDD)**.

> **Status: Provisional.** The personas and stories here are evidence-grounded
> *inferences* from the project's own artifacts — not from user interviews. They are
> precise enough to anchor specs, but they are hypotheses until validated. See the
> [validation protocol](research/user-research.md#5-validation-protocol).

## Contents

| Path | What it is |
|------|------------|
| [`research/user-research.md`](research/user-research.md) | Method, the cited evidence base, inferred user segments, and the runnable validation protocol (screener, interview guide, hypotheses). |
| [`personas/_template.md`](personas/_template.md) | The persona standard — copy to add a persona. |
| [`personas/reviewer.md`](personas/reviewer.md) | Primary persona: reviews large / agent-generated PRs. |
| [`personas/author.md`](personas/author.md) | Primary persona: self-reviews their own diff before pushing. |
| [`user-stories/_template.md`](user-stories/_template.md) | The user-story standard — copy to add a story. |
| [`user-stories/reviewer-stories.md`](user-stories/reviewer-stories.md) | Stories `REV-01…REV-07`. |
| [`user-stories/author-stories.md`](user-stories/author-stories.md) | Stories `AUT-01…AUT-06`. |

## Reading order

1. **[user-research.md](research/user-research.md)** — start here; it establishes the
   evidence (tagged `E#`) and hypotheses (`H#`) every other doc relies on.
2. **Personas** — the two primary users, each tracing claims back to `E#`/`H#`.
3. **User stories** — concrete capabilities per persona, with Gherkin acceptance criteria.

## The two primary personas

- **[The Reviewer (`reviewer`)](personas/reviewer.md)** — understands a large, often
  agent-generated PR well enough to approve or reject it; can't tell from the file tree
  what matters or what to read first.
- **[The Author (`author`)](personas/author.md)** — sanity-checks the shape of an
  agent-generated diff before pushing, to confirm it's what they intended and nothing stray.

A *Tech Lead / Release Reviewer* is noted as a **secondary/future** segment in the research
doc but is deliberately **not** given a full persona — the tool does not yet serve
release-scoped input. Add one (via the template) if/when that scope lands.

## How to use these docs in SDD

A spec for any new feature or change should:

1. **Name the persona(s)** it serves, by ID (`reviewer`, `author`), linking the persona file.
2. **Cite the story IDs** it satisfies (e.g. "implements `REV-03`, `REV-07`"). If no story
   fits, add one to the relevant `user-stories/*.md` first using the template.
3. **Reuse the acceptance criteria** in the cited stories as the spec's baseline behavior,
   then extend with implementation-specific scenarios.
4. **Respect the v1 exclusions** listed in each story file and in `AGENTS.md` — don't spec
   excluded behavior without first promoting it out of the out-of-scope lists.

## Conventions

- **Persona IDs** are stable kebab-case (`reviewer`, `author`).
- **Story IDs** are `REV-NN` / `AUT-NN`, stable once assigned; never renumber. Excluded
  ideas stay listed as out-of-scope rather than being deleted.
- **Evidence tags** (`E#`) and **hypothesis tags** (`H#`) are defined in
  [user-research.md](research/user-research.md) and referenced throughout.
- Every claim should trace to an `E#`, an `H#`, or be marked **(assumption)** — no invented
  quotes or metrics.

## Maintaining these docs

- Run the [validation protocol](research/user-research.md#5-validation-protocol) with real
  developers; fold results back into `user-research.md` and flip persona **Status** from
  *Provisional* to *Validated* once H1–H4 hold.
- When project scope changes (e.g. `AGENTS.md` exclusions are lifted), revisit the
  out-of-scope lists and the secondary/future segment.
- Keep persona/story claims consistent with `AGENTS.md` invariants and current capability
  (e.g. provider support, ceilings).
