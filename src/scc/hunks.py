from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Hunk:
    id: int
    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str   # verbatim "@@ ... @@" line
    body: str     # verbatim "+"/"-"/" " lines


class HunkIndex:
    def __init__(self, hunks: list[Hunk]):
        self._map: dict[int, Hunk] = {h.id: h for h in hunks}

    def by_ids(self, ids: list[int]) -> list[Hunk]:
        return [self._map[i] for i in ids if i in self._map]


_DIFF_GIT = re.compile(r"^diff --git ", re.MULTILINE)
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)", re.MULTILINE)
_PLUS_PATH = re.compile(r"^\+\+\+ (?:b/)?(.+)$", re.MULTILINE)
_MINUS_PATH = re.compile(r"^--- (?:a/)?(.+)$", re.MULTILINE)


def parse_diff(diff_text: str) -> list[Hunk]:
    if not diff_text or not diff_text.strip():
        return []

    hunks: list[Hunk] = []
    next_id = 1

    # Split into per-file sections on "diff --git" boundaries
    sections = _DIFF_GIT.split(diff_text)

    for section in sections:
        if not section.strip():
            continue

        # Reconstruct the full section header line (split removed "diff --git ")
        full_section = "diff --git " + section

        # Resolve file path: prefer +++ b/... line, fall back to --- a/...
        plus_m = _PLUS_PATH.search(full_section)
        minus_m = _MINUS_PATH.search(full_section)

        if plus_m and plus_m.group(1) != "/dev/null":
            file_path = plus_m.group(1)
        elif minus_m and minus_m.group(1) != "/dev/null":
            file_path = minus_m.group(1)
        else:
            # Binary file or mode-only change — extract path from diff --git line
            first_line = full_section.splitlines()[0]
            # "diff --git a/foo b/foo" -> "foo"
            parts = first_line.split(" b/", 1)
            file_path = parts[1] if len(parts) == 2 else first_line

        # Find all hunk headers in this section
        hunk_matches = list(_HUNK_HEADER.finditer(full_section))

        if not hunk_matches:
            # Binary or mode-change: emit a single placeholder hunk
            hunks.append(Hunk(
                id=next_id,
                file_path=file_path,
                old_start=0, old_count=0,
                new_start=0, new_count=0,
                header="(binary or mode-change — no hunk content)",
                body="",
            ))
            next_id += 1
            continue

        for i, m in enumerate(hunk_matches):
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) is not None else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) is not None else 1
            header = m.group(0).rstrip()

            # Body: from end of this hunk header to start of next (or end of section)
            body_start = m.end()
            body_end = hunk_matches[i + 1].start() if i + 1 < len(hunk_matches) else len(full_section)
            body = full_section[body_start:body_end].rstrip("\n")

            hunks.append(Hunk(
                id=next_id,
                file_path=file_path,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                header=header,
                body=body,
            ))
            next_id += 1

    return hunks
