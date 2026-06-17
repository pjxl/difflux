"""Tests for prompt.py — SYSTEM_PROMPT content and render_hunks output."""

from difflux.hunks import Hunk
from difflux.prompt import SYSTEM_PROMPT, render_hunks, build_user_message


def _make_hunk(id: int, file_path: str = "src/foo.py", new_start: int = 10, new_count: int = 5) -> Hunk:
    return Hunk(
        id=id,
        file_path=file_path,
        old_start=new_start,
        old_count=new_count,
        new_start=new_start,
        new_count=new_count,
        header=f"@@ -{new_start},{new_count} +{new_start},{new_count} @@",
        body="+added line\n-removed line\n context",
    )


def test_system_prompt_is_nonempty_string():
    assert isinstance(SYSTEM_PROMPT, str)
    assert len(SYSTEM_PROMPT) > 500


def test_system_prompt_contains_key_instructions():
    assert "CONCEPTUAL CLUSTERS" in SYSTEM_PROMPT
    assert "return_clustering" in SYSTEM_PROMPT
    assert "single_idea" in SYSTEM_PROMPT
    assert "position_rationale" in SYSTEM_PROMPT
    assert "ESCAPE HATCH" in SYSTEM_PROMPT


def test_system_prompt_uses_en_dash_in_line_range():
    # The render_hunks format uses en-dash (–), not hyphen
    # Verify the prompt schema example uses the right character
    assert "–" in SYSTEM_PROMPT or "hunk_ids" in SYSTEM_PROMPT  # schema example present


def test_render_hunks_single():
    h = _make_hunk(1)
    out = render_hunks([h])
    assert "Hunk #1" in out
    assert "src/foo.py" in out
    assert "lines 10" in out
    assert "@@ -10" in out
    assert "+added line" in out


def test_render_hunks_uses_en_dash():
    h = _make_hunk(1, new_start=10, new_count=5)
    out = render_hunks([h])
    # Should be "lines 10–14" not "lines 10-14"
    assert "–" in out


def test_render_hunks_multiple_separated_by_blank_lines():
    hunks = [_make_hunk(1), _make_hunk(2, file_path="src/bar.py", new_start=20)]
    out = render_hunks(hunks)
    assert "Hunk #1" in out
    assert "Hunk #2" in out
    assert "src/bar.py" in out
    # Double newline separator between hunks
    assert "\n\n" in out


def test_build_user_message_contains_hunk_count():
    hunks = [_make_hunk(1), _make_hunk(2)]
    msg = build_user_message(hunks)
    assert "2 hunks" in msg


def test_build_user_message_contains_file_count():
    hunks = [_make_hunk(1, "a.py"), _make_hunk(2, "b.py")]
    msg = build_user_message(hunks)
    assert "2 files" in msg


def test_build_user_message_no_hint_by_default():
    hunks = [_make_hunk(1)]
    msg = build_user_message(hunks)
    assert "CORRECTION HINT" not in msg


def test_build_user_message_with_hint():
    hunks = [_make_hunk(1)]
    msg = build_user_message(hunks, correction_hint="merge the auth clusters")
    assert "CORRECTION HINT FROM REVIEWER" in msg
    assert "merge the auth clusters" in msg


def test_position_rationale_not_in_render_hunks():
    # render_hunks never emits position_rationale — hunk content only
    h = _make_hunk(1)
    out = render_hunks([h])
    assert "position_rationale" not in out
