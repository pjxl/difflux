from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import VerticalScroll
from rich.syntax import Syntax

from scc.enrich import ClusterView
from scc.hunks import Hunk


class ClusterCard(Static):
    """A single cluster row in the overview list."""

    DEFAULT_CSS = """
    ClusterCard {
        padding: 0 1;
        height: auto;
    }
    ClusterCard:focus {
        background: $accent 20%;
    }
    ClusterCard.reviewed {
        color: $success;
    }
    """

    def __init__(self, view: ClusterView, index: int, **kwargs):
        super().__init__(**kwargs)
        self._view = view
        self._index = index
        self.can_focus = True

    def render(self) -> str:
        v = self._view
        mark = "✓" if v.reviewed else " "
        name_col = v.cluster.name[:35].ljust(35)
        meta = f"{len(v.hunks)}h  {v.file_count}f  ~{v.line_count} lines"
        line1 = f" {mark} {self._index:2}  {name_col}  {meta}"
        line2 = f"       {v.cluster.summary}"
        return f"{line1}\n{line2}"

    def toggle_reviewed(self) -> None:
        self._view.reviewed = not self._view.reviewed
        if self._view.reviewed:
            self.add_class("reviewed")
        else:
            self.remove_class("reviewed")
        self.refresh()


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
            "[bold]scc keyboard shortcuts[/bold]\n\n"
            " [bold]j / k[/bold]  or  [bold]↑ / ↓[/bold]   navigate clusters\n"
            " [bold]Enter[/bold]              drill into cluster\n"
            " [bold]Space[/bold]              mark cluster reviewed\n"
            " [bold]r[/bold]                  regenerate clustering\n"
            " [bold]?[/bold]                  toggle this help\n"
            " [bold]Esc / q[/bold]            back / quit"
        )
