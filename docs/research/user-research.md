# User Research — difflux

**Status:** Provisional (synthesis-based). Not yet validated with real users.
**Last updated:** 2026-06-17
**Owner:** plaughlin

---

## 1. Method & honesty note

This research was produced by **inference from existing project artifacts**, not from
interviews, surveys, or usage analytics. At the time of writing, difflux has no released
user base to observe and no instrumentation. The "research" here is therefore a
disciplined reading of what the product *claims to be for* and *how it is meant to be
used*, cross-checked against its actual implemented scope.

What this method **licenses**:

- Identifying the jobs the tool is explicitly designed to do.
- Inferring the contexts and pains those jobs imply.
- Producing provisional personas precise enough to anchor spec-driven development.

What this method **does not license**:

- Claims about real user behavior, frequency, willingness to pay, or satisfaction.
- Invented quotes, metrics, or "interview findings." There are none in these docs.
- Treating personas as settled. They are hypotheses to be confirmed or refuted (§5).

Every inferred claim below is traceable to a cited artifact in §3. Where the artifacts
are silent or in tension, that is flagged rather than papered over.

---

## 2. Product in one paragraph

difflux is a CLI/TUI that takes a git diff (piped from stdin or fetched from a GitHub PR
URL), sends the numbered hunks to a language model, and gets back a grouping of those
hunks into **conceptual clusters** ordered in the sequence that best builds understanding
(entry point → core logic → edge handling → tests). The reviewer navigates the change by
*idea* rather than by *file*. (`README.md` §"The problem", §"How it works"; `AGENTS.md`
§"What this project is".)

---

## 3. Evidence base

Citations point to the source artifact and the specific claim relied upon.

### From `README.md`

- **E1 — Core problem statement.** "Standard diff tools present changes in file order.
  File order has no relationship to conceptual order or to where the risk lives."
  (§"The problem".) → Establishes the central pain: file order ≠ reading order ≠ risk.
- **E2 — The triggering scenario.** "A 40-file agent-generated PR might interleave a
  rename, a core feature, and incidental reformatting across dozens of files — and the
  file tree gives you no signal about which is which, or what to read first." (§"The
  problem".) → The acute case is the **large, agent-generated PR**.
- **E3 — Value scales with size.** "In a two-file diff the gain is modest. In a 50-file
  agent PR the reordering is the difference between understanding the change and reading
  it." (§"Example".) → Primary value is concentrated at high diff size; small diffs are a
  weak use case.
- **E4 — Two input paths.** `git diff … | difflux` (local, pre-push) and
  `difflux https://github.com/owner/repo/pull/123` (reviewing someone else's PR).
  (§"Usage".) → Two distinct usage *moments*: authoring locally vs. reviewing remotely.
- **E5 — Plain-text fallback.** `--no-tui` exists, and text output is used when stdout is
  not a TTY. (§"Usage".) → A non-interactive / piping / CI-adjacent context is anticipated.
- **E6 — Navigation model.** Keybindings (`j`/`k`, `Enter` to drill in, `Space` to mark
  reviewed, `r` to regenerate, `?` help, `q`/`Esc`). (§"Keybindings".) → Implies a
  keyboard-driven, terminal-resident user.
- **E7 — Setup cost.** Requires an API key; `GITHUB_TOKEN` for private repos.
  (§"Setup".) → User is comfortable with env vars, tokens, and the terminal.

### From `AGENTS.md`

- **E8 — Reviewer-centric framing.** "presented in a Textual terminal TUI so a reviewer
  can navigate the change by idea rather than by file." (§"What this project is".) →
  The named user is "a reviewer."
- **E9 — Scale ceilings.** `HUNK_CEILING` = 300, `TOKEN_CEILING` = 150,000; diffs beyond
  this are truncated with a stderr warning. (§"Truncation".) → The tool is built for
  large diffs but has a known upper bound; very large diffs degrade gracefully, not
  silently.
- **E10 — Oversized-input handling on the source side.** GitHub fetch handles 404
  (private/not found) and 406 (diff too large). (§"Key files", `sources/github.py`.) →
  Failure modes around big/private PRs are first-class concerns.
- **E11 — Explicit v1 exclusions.** No manual cluster editing, no persisted review state
  (reviewed checkboxes are in-memory only; the only trace is a stdout summary on exit),
  no `--granularity` flag, no directed regeneration, no cross-session caching.
  (§"What v1 explicitly excludes".) → Bounds what stories may assume as available.
- **E12 — Single-idea path.** Clustering can return `single_idea` (a small/cohesive diff
  that is one idea), rendered without an overview. (§"Architecture", `tui/drilldown.py`.)
  → The tool must behave sensibly on small diffs even though they are a weak value case
  (cf. E3).

### From git history

- **E13 — Provider-agnostic LLM support.** The most recent commit
  (`46b430a`, 2026-06-17) added Anthropic **and** OpenAI support; `config.py` reads
  `OPENAI_API_KEY` and `DIFFLUX_PROVIDER`. → User may already have a preferred LLM
  provider/account and expects to use it. (Note: `README.md` §"Setup"/"Configuration"
  still documents Anthropic only — a documentation lag, not a capability gap.)
- **E14 — Young, single-author project.** Three commits, one author, initial
  implementation through rename to "difflux" on a single day. → No installed base yet;
  personas are forward-looking, which reinforces their provisional status.

---

## 4. Inferred user segments

Two **primary** segments and one **secondary/future** segment. The split is driven by
*usage moment* (E4), not by job title — the same person may occupy more than one.

### Primary 1 — The Reviewer (reviewing someone else's change)

A developer who must understand a large or unfamiliar PR — increasingly one that an AI
agent generated — well enough to approve it or send it back. Enters via a GitHub PR URL
(E4) or a piped diff. Core pain: file order gives no signal about what matters or what to
read first, and that pain scales with PR size (E1, E2, E3, E8). Detailed in
[`../personas/reviewer.md`](../personas/reviewer.md).

### Primary 2 — The Author (self-reviewing their own change before pushing)

A developer — often one who just had an agent produce a sprawling diff — who wants to
sanity-check the *shape* of the change before they push or open a PR. Enters via
`git diff … | difflux` (E4). Core job: confirm the diff contains what they intended and
nothing stray (a rename smeared with incidental reformatting, E2) before exposing it to
reviewers. Detailed in [`../personas/author.md`](../personas/author.md).

### Secondary / future — The Tech Lead / Release Reviewer

Someone doing a higher-altitude pass over an aggregate change (a release branch, a
sequence of merged PRs) primarily to assess risk and decide what to scrutinize. The
"where the risk lives" framing (E1) and ordering-by-understanding both serve this, but
nothing in the artifacts targets multi-PR or release-scoped input, and key supports
(persisted state, multi-PR aggregation) are explicitly excluded in v1 (E11). **Not given
a full persona** to avoid specifying a user the tool does not yet serve; revisit if/when
release-scoped input is in scope.

---

## 5. Validation protocol

This is the runnable research to convert provisional personas into grounded ones. Execute
with real developers before treating any persona claim as fact.

### 5.1 Screener (who qualifies)

Recruit developers who, in the last month, have:

- Reviewed at least one PR touching **10+ files**, AND
- Worked with AI-generated code (agent or assistant) that produced a multi-file diff, AND
- Are comfortable in a terminal (use the CLI/`git` directly, not solely a GUI).

Target a mix of: people who mostly *review* others' PRs, and people who mostly *author*
large changes. Aim for 5–8 conversations (enough to expose pattern breaks; this is
qualitative, not statistical).

### 5.2 Interview guide (~6–8 questions, ~30 min)

1. Walk me through the last big or unfamiliar PR you reviewed. Where did you start, and
   why there?
2. When a diff spans many files, how do you figure out what actually matters vs. noise
   (renames, reformatting)? *(tests E1, E2)*
3. Has an AI agent ever handed you (or you generated) a sprawling diff? What made it hard
   to review? *(tests E2, E3)*
4. Before you open a PR, do you review your own diff? How — and what are you looking for?
   *(tests Author segment, E4)*
5. At what change size does file-by-file reading stop working for you? *(tests E3, E9)*
6. If a tool grouped a diff by *idea* and told you what to read first, what would you
   still not trust about it? *(tests value prop + trust/failure modes)*
7. Where does your code review happen today — terminal, web PR UI, IDE? Would a terminal
   tool fit or fight that? *(tests E6, E7 — terminal-residence assumption)*
8. Which LLM provider/account would you expect to use, and would the API-key setup be a
   barrier? *(tests E7, E13)*

### 5.3 Hypotheses to confirm or refute

| ID | Hypothesis | Refuted if… |
|----|------------|-------------|
| H1 | Reviewers abandon or distrust file-order review on PRs above some size threshold (~10–50 files). | They report file order works fine at any size, or they already have an effective non-file strategy. |
| H2 | The acute trigger is AI-/agent-generated PRs specifically, not just large human PRs. | Large human PRs are reported as equally or more painful, making "agent-generated" incidental. |
| H3 | Authors want a pre-push "shape check" of their own diff (the Author segment is real). | Authors say they never self-review the raw diff, or only ever review in the PR web UI after pushing. |
| H4 | A terminal/TUI tool fits reviewers' existing workflow rather than fighting it. | Reviewers live in the web PR UI or IDE and won't context-switch to a terminal for review. |
| H5 | "Group by idea + tell me what to read first" is the core value; manual editing of clusters is not needed for v1. | Users immediately demand to re-cluster/edit groupings themselves before they'll trust output (would pressure the E11 exclusion). |
| H6 | The small-diff case (single_idea) is genuinely low-value and not worth optimizing. | Users reach for the tool mostly on small diffs, inverting the E3 assumption. |

Record results back into this file (replace "Status: Provisional" once H1–H4 hold) and
update the personas accordingly.

---

## 6. Cross-references

- Personas: [`../personas/reviewer.md`](../personas/reviewer.md),
  [`../personas/author.md`](../personas/author.md)
- Persona standard: [`../personas/_template.md`](../personas/_template.md)
- User stories: [`../user-stories/`](../user-stories/)
- Docs index: [`../README.md`](../README.md)
