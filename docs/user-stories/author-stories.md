# User Stories — The Author (`author`)

Persona: [`../personas/author.md`](../personas/author.md) ·
Template: [`./_template.md`](./_template.md) ·
Research: [`../research/user-research.md`](../research/user-research.md)

All stories conform to the v1 scope in `AGENTS.md`; excluded behavior is listed at the
bottom rather than written as a story (E11).

---

### AUT-01 — Sanity-check a generated diff before pushing

**Persona:** [`author`](../personas/author.md)
**Status:** Proposed
**Priority:** Must

**Story.** As an author, I want to pipe my working diff into difflux and see it grouped by
idea, so that I can confirm the change matches my intent before I push or open a PR.
*(E2, E4)*

**Acceptance criteria**

```gherkin
Scenario: Cluster a local diff from stdin
  Given uncommitted or committed local changes
  When I run `git diff ... | difflux`
  Then difflux reads the diff from stdin and presents its conceptual clusters
```

**Notes / out-of-scope.** stdin is the author's primary entry path (E4).

---

### AUT-02 — Spot stray edits separated from real logic

**Persona:** [`author`](../personas/author.md)
**Status:** Proposed
**Priority:** Must

**Story.** As an author, I want incidental changes (renames, reformatting) grouped apart
from the substantive feature, so that I can catch edits I didn't intend before they reach
review. *(E2)*

**Acceptance criteria**

```gherkin
Scenario: Noise is its own cluster
  Given a diff that mixes a core feature with incidental reformatting and a rename
  When I view the difflux overview
  Then the incidental changes are grouped in cluster(s) distinct from the core feature
  And I can drill into a cluster to confirm what it actually contains
```

**Notes / out-of-scope.** Quality of separation depends on the model; difflux must present
the grouping faithfully.

---

### AUT-03 — Quick check stays quick on a small change

**Persona:** [`author`](../personas/author.md)
**Status:** Proposed
**Priority:** Should

**Story.** As an author, I want a small, cohesive diff shown as a single idea without a
navigable overview, so that a quick pre-push check stays quick. *(E12)*

**Acceptance criteria**

```gherkin
Scenario: Single-idea diff
  Given a small, cohesive diff that represents one idea
  When I run difflux
  Then difflux shows a single-idea view with a note and the raw hunks
  And it does not present a multi-cluster overview
```

**Notes / out-of-scope.** `single_idea` is one of exactly two clustering types; no
`too_large` type in v1 (`AGENTS.md` invariant, E11/E12).

---

### AUT-04 — Re-check after amending the diff

**Persona:** [`author`](../personas/author.md)
**Status:** Proposed
**Priority:** Could

**Story.** As an author, I want to regenerate the clustering, so that I can re-check the
shape after I fix or amend something. *(E6)*

**Acceptance criteria**

```gherkin
Scenario: Regenerate after a change
  Given the overview is displayed
  When I press r
  Then difflux re-clusters the current diff and rebuilds the overview
  And the interface remains responsive while it works
```

**Notes / out-of-scope.** Re-run only re-clusters the diff difflux already received; it
does not re-read `git` for new changes. Directed regeneration is out of scope (E11).

---

### AUT-05 — Plain-text output for scanning or piping

**Persona:** [`author`](../personas/author.md)
**Status:** Proposed
**Priority:** Should

**Story.** As an author, I want plain-text output instead of the TUI, so that I can scan
the result quickly or pipe it elsewhere. *(E5)*

**Acceptance criteria**

```gherkin
Scenario: Explicit no-TUI flag
  Given any diff
  When I run difflux with --no-tui
  Then difflux prints the cluster overview and contents as plain text

Scenario: Non-interactive stdout
  Given stdout is not a TTY (e.g. piped to a file or another command)
  When I run difflux
  Then difflux uses the plain-text renderer automatically
```

**Notes / out-of-scope.** The text renderer must also never print `position_rationale`
(`AGENTS.md` invariant).

---

### AUT-06 — Use my own LLM provider

**Persona:** [`author`](../personas/author.md)
**Status:** Proposed
**Priority:** Should

**Story.** As an author, I want difflux to use my configured LLM provider, so that I can
run it against the account/model I already have. *(E13)*

**Acceptance criteria**

```gherkin
Scenario: Provider auto-detected from model name
  Given an API key is set and DIFFLUX_MODEL names a known model
  When I run difflux without setting DIFFLUX_PROVIDER
  Then difflux selects the matching provider (Anthropic or OpenAI) automatically

Scenario: Explicit provider override
  Given DIFFLUX_PROVIDER is set
  When I run difflux
  Then difflux uses the specified provider
```

**Notes / out-of-scope.** Provider/model config lives in `config.py` (`DIFFLUX_MODEL`,
`DIFFLUX_PROVIDER`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). README documentation of OpenAI
support is a known lag, not a capability gap (E13). No multi-model fallback in v1 (E11).

---

## Out-of-scope for v1 (considered, deliberately not stories)

Evaluated against the Author's needs and excluded per `AGENTS.md` (E11):

- difflux modifying or rewriting the author's diff (it is read-only).
- Persisted state between pre-push runs.
- `--granularity` / `--clusters N` controls.
- Directed regeneration / correction-hint UI.
- Re-reading `git` for new changes within a session.
- Cross-session caching.
