# User Stories — The Reviewer (`reviewer`)

Persona: [`../personas/reviewer.md`](../personas/reviewer.md) ·
Template: [`./_template.md`](./_template.md) ·
Research: [`../research/user-research.md`](../research/user-research.md)

All stories conform to the v1 scope in `AGENTS.md`; excluded behavior is listed at the
bottom rather than written as a story (E11).

---

### REV-01 — See the shape of a change before reading it

**Persona:** [`reviewer`](../personas/reviewer.md)
**Status:** Proposed
**Priority:** Must

**Story.** As a reviewer, I want a large diff grouped into a handful of conceptual
clusters with one-line summaries, so that I understand the shape of the change before I
read a single hunk. *(E1, E3, E8)*

**Acceptance criteria**

```gherkin
Scenario: Multi-idea diff produces an overview
  Given a diff spanning many files and several distinct concerns
  When I run difflux on it
  Then I see an overview listing each cluster with a name, a one-sentence summary,
       its hunk count, and its file count
  And the clusters are ordered for understanding (entry point → core → edges → tests)

Scenario: Reviewer cannot see internal reasoning
  Given the overview is displayed
  When I read a cluster's summary
  Then I never see the model's position_rationale text
```

**Notes / out-of-scope.** Cluster count is model-chosen (4–8 preference); no granularity
control (E11). `position_rationale` must never render (`AGENTS.md` invariant).

---

### REV-02 — Read the highest-risk idea first

**Persona:** [`reviewer`](../personas/reviewer.md)
**Status:** Proposed
**Priority:** Must

**Story.** As a reviewer, I want clusters ordered so the entry point and core logic come
before edge handling and tests, so that I spend my first and best attention where the risk
lives. *(E1)*

**Acceptance criteria**

```gherkin
Scenario: Reading order is meaningful, not file order
  Given a diff whose tests appear before their implementation in file order
  When I view the difflux overview
  Then the core implementation cluster is ordered ahead of the test cluster
```

**Notes / out-of-scope.** Ordering quality is the model's job; difflux must preserve and
present that order, not re-sort by file.

---

### REV-03 — Drill into a cluster's actual hunks

**Persona:** [`reviewer`](../personas/reviewer.md)
**Status:** Proposed
**Priority:** Must

**Story.** As a reviewer, I want to open a cluster and see its real diff hunks gathered
together, so that I can review one idea even though its changes are scattered across the
file tree. *(E6, E8)*

**Acceptance criteria**

```gherkin
Scenario: Drill into a cluster
  Given the overview is displayed and a cluster is highlighted
  When I press Enter
  Then I see the actual diff hunks belonging to that cluster, with diff syntax
       highlighting, regardless of which files they came from
  And the hunk content matches the original diff exactly (no model-altered content)

Scenario: Return to the overview
  Given I am viewing a cluster's hunks
  When I press Esc
  Then I return to the overview with my position preserved
```

**Notes / out-of-scope.** Hunk content is joined locally by ID, never echoed by the model
(`AGENTS.md` "Why hunk content stays local").

---

### REV-04 — Track which ideas I've reviewed

**Persona:** [`reviewer`](../personas/reviewer.md)
**Status:** Proposed
**Priority:** Should

**Story.** As a reviewer, I want to mark clusters as reviewed as I go, so that I can keep
my place across a large change within a sitting. *(E6, E11)*

**Acceptance criteria**

```gherkin
Scenario: Mark a cluster reviewed
  Given the overview is displayed
  When I press Space on a cluster
  Then that cluster is shown as reviewed
  And pressing Space again clears the reviewed mark

Scenario: Summary on exit
  Given I have marked some clusters reviewed
  When I quit difflux
  Then a summary line is printed to stdout reflecting reviewed progress
```

**Notes / out-of-scope.** Reviewed state is in-memory and session-local only; **no**
persisted review log or file on disk (E11).

---

### REV-05 — Review a PR by URL, including private repos

**Persona:** [`reviewer`](../personas/reviewer.md)
**Status:** Proposed
**Priority:** Must

**Story.** As a reviewer, I want to point difflux at a GitHub PR URL, so that I can review
someone else's change without manually producing a diff. *(E4, E7, E10)*

**Acceptance criteria**

```gherkin
Scenario: Cluster a PR by URL
  Given a GitHub PR URL
  When I run difflux with that URL
  Then difflux fetches the PR's unified diff and clusters it

Scenario: Private repo without a token
  Given a private-repo PR URL and no GITHUB_TOKEN
  When I run difflux with that URL
  Then I get a clear error indicating the PR was not found or is private
```

**Notes / out-of-scope.** 404 (not found/private) and 406 (diff too large) are handled by
the GitHub source (E10).

---

### REV-06 — Regenerate when the first cut isn't useful

**Persona:** [`reviewer`](../personas/reviewer.md)
**Status:** Proposed
**Priority:** Could

**Story.** As a reviewer, I want to re-run the clustering on the same diff, so that I can
get a fresh grouping if the first one didn't help. *(E6)*

**Acceptance criteria**

```gherkin
Scenario: Regenerate from the overview
  Given the overview is displayed
  When I press r
  Then difflux re-clusters the same diff while showing a loading indicator
  And the UI stays responsive during the call
  And the overview is rebuilt from the new result when it completes
```

**Notes / out-of-scope.** `r` is a plain re-run; **no** directed regeneration / correction
hint UI in v1 (E11).

---

### REV-07 — Get a graceful result on an oversized diff

**Persona:** [`reviewer`](../personas/reviewer.md)
**Status:** Proposed
**Priority:** Should

**Story.** As a reviewer, I want oversized diffs handled predictably, so that a huge PR
degrades gracefully instead of failing silently or crashing. *(E9, E10)*

**Acceptance criteria**

```gherkin
Scenario: Diff exceeds the hunk/token ceiling
  Given a diff larger than the hunk or token ceiling
  When I run difflux
  Then difflux truncates to the ceiling and prints a warning to stderr
  And it still produces a usable clustering of the retained hunks

Scenario: GitHub diff too large to fetch
  Given a PR whose diff exceeds GitHub's size limit
  When I run difflux with that PR URL
  Then I get a clear error explaining the diff is too large
```

**Notes / out-of-scope.** Two-pass chunking for oversized diffs is **out of scope** in v1
(E11); v1 truncates with a warning.

---

## Out-of-scope for v1 (considered, deliberately not stories)

These were evaluated against the Reviewer's needs and excluded per `AGENTS.md` (E11). Kept
here so future specs see the boundary:

- Manual cluster editing (drag/merge/split/rename).
- Persisted review state across sessions.
- `--granularity` / `--clusters N` controls.
- Directed regeneration via a correction hint.
- Keyword filter (`/`) within the overview.
- Streaming LLM output into the TUI.
- Cross-session caching or multi-model fallback.
