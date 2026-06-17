# User Story Template

Copy this structure for each story. Keep the field set stable — specs cite story IDs and
acceptance criteria directly. One story = one `###` block.

**Story ID convention:** `<PERSONA-PREFIX>-NN` (e.g. `REV-01`, `AUT-03`). IDs are stable
once assigned; never renumber. Mark out-of-scope items explicitly rather than deleting
them, so specs can see what was considered and excluded.

**Status values:** Proposed · Accepted · Implemented · Out-of-scope (v1).

Every story must name a persona that exists in [`../personas/`](../personas/) and stay
consistent with the v1 exclusions in
[`../research/user-research.md`](../research/user-research.md) (E11).

---

### <STORY-ID> — <short title>

**Persona:** [`<persona-id>`](../personas/<persona-file>.md)
**Status:** Proposed
**Priority:** Must | Should | Could

**Story.** As a `<persona>`, I want `<capability>`, so that `<outcome>`.

**Acceptance criteria**

```gherkin
Scenario: <name>
  Given <precondition>
  When <action>
  Then <observable result>
```

**Notes / out-of-scope.** *(Edge cases, related excluded behavior, evidence tags.)*
