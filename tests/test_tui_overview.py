"""Tests for the cluster overview screen rendering path."""

import asyncio

from textual.app import App
from textual.widgets import Static

from difflux.enrich import build_session
from difflux.hunks import Hunk, HunkIndex
from difflux.models import Cluster, ClusteringResult, ClusteringType
from difflux.tui.overview import OverviewScreen


def _hunk(id: int, file_path: str = "src/foo.py") -> Hunk:
    return Hunk(
        id=id, file_path=file_path,
        old_start=1, old_count=3, new_start=1, new_count=3,
        header="@@ -1,3 +1,3 @@", body="+add\n-remove\n ctx",
    )


def _build_session(note=None, coverage=None):
    cluster = Cluster(
        id="c1", name="Cluster One", summary="A summary sentence.",
        position_rationale="internal only", hunk_ids=[1, 2],
    )
    result = ClusteringResult(
        clustering_type=ClusteringType.MULTI_CLUSTER,
        clusters=[cluster], note=note, coverage=coverage,
    )
    return build_session(result, HunkIndex([_hunk(1), _hunk(2, "src/bar.py")]))


class _Harness(App):
    def __init__(self, session):
        super().__init__()
        self._session = session

    def on_mount(self):
        self.push_screen(
            OverviewScreen(self._session, lambda: self._session, "model-x", "anthropic")
        )


def _run(session):
    async def _go():
        async with _Harness(session).run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            return str(pilot.app.screen.query_one("#overview-banner", Static).render())

    return asyncio.run(_go())


def test_overview_mounts_with_markup_in_note_and_coverage():
    # Regression: LLM note/coverage containing Rich markup delimiters must not
    # raise MarkupError when the banner renders.
    session = _build_session(
        note="Touches [/api] route and [bold] handler.",
        coverage="see [unclosed bracket",
    )
    banner = _run(session)
    assert "[/api]" in banner  # delimiters preserved verbatim, not parsed
    assert "[unclosed bracket" in banner


def test_overview_mounts_without_note_or_coverage():
    # No banner content should still mount cleanly.
    assert _run(_build_session()) == ""
