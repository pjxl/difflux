from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import VerticalScroll, Horizontal, Vertical
from rich.syntax import Syntax

from difflux.enrich import ClusterView
from difflux.format import churn_bar, meta_label
from difflux.hunks import Hunk


class ClusterCard(Vertical):
    """A single cluster row in the overview list."""

    can_focus = True

    DEFAULT_CSS = """
    ClusterCard {
        padding: 0 1;
        height: auto;
    }
    ClusterCard:focus {
        background: $accent 20%;
    }
    ClusterCard.reviewed .mark {
        color: $success;
    }
    ClusterCard .card-row {
        height: 1;
    }
    ClusterCard .mark {
        width: 2;
        color: $success;
    }
    ClusterCard .index {
        width: 3;
        text-align: right;
        margin-right: 2;
        color: $text-muted;
    }
    ClusterCard .name {
        width: 32;
        margin-right: 2;
        text-style: bold;
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    ClusterCard .bar {
        width: 8;
        margin-right: 2;
        color: $accent;
    }
    ClusterCard .meta {
        width: auto;
        color: $text-muted;
    }
    ClusterCard .summary {
        width: 1fr;
        height: auto;
        padding-left: 7;
        text-wrap: wrap;
        color: $text-muted;
    }
    """

    def __init__(self, view: ClusterView, index: int, max_churn: int = 0, **kwargs):
        super().__init__(**kwargs)
        self._view = view
        self._index = index
        self._max_churn = max_churn

    def compose(self) -> ComposeResult:
        v = self._view
        with Horizontal(classes="card-row"):
            yield Label(self._mark(), classes="mark")
            yield Label(str(self._index), classes="index")
            yield Label(v.cluster.name, classes="name", markup=False)
            yield Label(churn_bar(v.churn, self._max_churn), classes="bar")
            yield Label(self._meta(), classes="meta")
        yield Label(v.cluster.summary, classes="summary", markup=False)

    def _mark(self) -> str:
        return "✓" if self._view.reviewed else " "

    def _meta(self) -> str:
        v = self._view
        return meta_label(len(v.hunks), v.file_count, v.added, v.removed)

    def toggle_reviewed(self) -> None:
        self._view.reviewed = not self._view.reviewed
        self.sync_reviewed()

    def sync_reviewed(self) -> None:
        self.set_class(self._view.reviewed, "reviewed")
        self.query_one(".mark", Label).update(self._mark())


class HunkBlock(Static):
    """Renders a single hunk with syntax highlighting in the drill-down view."""

    DEFAULT_CSS = """
    HunkBlock {
        padding: 1 0;
        height: auto;
    }
    """

    def __init__(self, hunk: Hunk, **kwargs):
        super().__init__(**kwargs)
        self._hunk = hunk

    def compose(self) -> ComposeResult:
        h = self._hunk
        end_line = h.new_start + h.new_count - 1
        yield Label(
            f"[dim]{h.file_path}  lines {h.new_start}–{end_line}[/dim]",
            markup=True,
        )
        syntax = Syntax(h.header + "\n" + h.body, "diff", theme="monokai")
        yield Static(syntax)


class HelpModal(Static):
    """Help overlay content."""

    DEFAULT_CSS = """
    HelpModal {
        background: $surface;
        border: solid $accent;
        padding: 1 2;
        width: 50;
        height: auto;
    }
    """

    def render(self) -> str:
        return (
            "[bold]difflux keyboard shortcuts[/bold]\n\n"
            " [bold]j / k[/bold]  or  [bold]↑ / ↓[/bold]   navigate clusters\n"
            " [bold]Enter[/bold]              drill into cluster\n"
            " [bold]Space[/bold]              mark cluster reviewed\n"
            " [bold]r[/bold]                  regenerate (re-run same model)\n"
            " [bold]K[/bold]                  manage API keys\n"
            " [bold]?[/bold]                  toggle this help\n"
            " [bold]Esc / q[/bold]            back / quit"
        )
