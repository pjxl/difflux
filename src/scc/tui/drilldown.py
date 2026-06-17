from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Footer
from textual.containers import VerticalScroll

from scc.enrich import ClusterView, ReviewSession
from scc.tui.widgets import HunkBlock


class DrillDownScreen(Screen):
    """Phase two: hunks for a single cluster."""

    BINDINGS = [
        ("escape,q", "go_back", "Back"),
        ("space", "toggle_reviewed", "Mark reviewed"),
    ]

    def __init__(self, view: ClusterView, **kwargs):
        super().__init__(**kwargs)
        self._view = view

    def compose(self) -> ComposeResult:
        v = self._view
        yield Static(
            f"[bold]{v.cluster.name}[/bold]\n[dim]{v.cluster.summary}[/dim]",
            markup=True,
            id="drill-header",
        )
        with VerticalScroll(id="hunk-scroll"):
            for hunk in v.hunks:
                yield HunkBlock(hunk)
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_toggle_reviewed(self) -> None:
        self._view.reviewed = not self._view.reviewed
        self.app.pop_screen()


class SingleIdeaScreen(Screen):
    """Shown when clustering_type is single_idea — no overview to navigate."""

    BINDINGS = [("q,escape", "quit", "Quit")]

    def __init__(self, session: ReviewSession, **kwargs):
        super().__init__(**kwargs)
        self._session = session

    def compose(self) -> ComposeResult:
        s = self._session
        note = s.note or "This diff is a single uniform operation — no conceptual separation to show."
        yield Static(
            f"[bold]scc[/bold] · single idea\n\n{note}\n\n"
            f"[dim]{s.total_hunks} hunks · {s.total_files} files[/dim]",
            markup=True,
        )
        if s.clusters:
            with VerticalScroll():
                for v in s.clusters:
                    for hunk in v.hunks:
                        yield HunkBlock(hunk)
        yield Footer()

    def action_quit(self) -> None:
        self.app.exit()
