from __future__ import annotations

import asyncio
from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Static, Footer, LoadingIndicator
from textual.containers import VerticalScroll

from difflux.enrich import ClusterView, ReviewSession
from difflux.tui.widgets import ClusterCard, HelpModal


class OverviewScreen(Screen):
    """Phase one: navigable cluster list."""

    BINDINGS = [
        ("j,down", "move_down", "Down"),
        ("k,up", "move_up", "Up"),
        ("enter", "drill_in", "Expand"),
        ("space", "toggle_reviewed", "Mark reviewed"),
        ("r", "regen", "Regenerate (same model)"),
        ("question_mark", "help", "Help"),
        ("q,escape", "quit_app", "Quit"),
    ]

    class ClusteringComplete(Message):
        def __init__(self, session: ReviewSession):
            super().__init__()
            self.session = session

    def __init__(
        self,
        session: ReviewSession,
        regenerate: Callable[[], ReviewSession],
        model: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.session = session
        self._regenerate = regenerate
        self.model = model
        self._focused_index = 0
        self._help_visible = False

    def compose(self) -> ComposeResult:
        yield Static(id="overview-header")
        yield Static(id="rule-top", markup=False)
        with VerticalScroll(id="cluster-list"):
            pass
        yield Static(id="rule-bottom", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        s = self.session
        header = self.query_one("#overview-header", Static)
        header.update(
            f"[bold]difflux[/bold]  ·  {self.model}  ·  {len(s.clusters)} clusters  ·  {s.total_files} files",
        )
        rule = "─" * 58
        self.query_one("#rule-top", Static).update(rule)
        self.query_one("#rule-bottom", Static).update(rule)

        container = self.query_one("#cluster-list", VerticalScroll)
        container.remove_children()
        for i, view in enumerate(s.clusters):
            card = ClusterCard(view, i + 1, id=f"card-{i}")
            container.mount(card)

        if s.coverage:
            container.mount(Static(f"\n[dim]Coverage note: {s.coverage}[/dim]", markup=True))

        self._focus_card(self._focused_index)

    def _focus_card(self, index: int) -> None:
        cards = self.query(ClusterCard)
        card_list = list(cards)
        if not card_list:
            return
        self._focused_index = max(0, min(index, len(card_list) - 1))
        for i, card in enumerate(card_list):
            if i == self._focused_index:
                card.focus()

    def action_move_down(self) -> None:
        self._focus_card(self._focused_index + 1)

    def action_move_up(self) -> None:
        self._focus_card(self._focused_index - 1)

    def action_drill_in(self) -> None:
        cards = list(self.query(ClusterCard))
        if not cards:
            return
        view = self.session.clusters[self._focused_index]
        from difflux.tui.drilldown import DrillDownScreen
        self.app.push_screen(DrillDownScreen(view))

    def action_toggle_reviewed(self) -> None:
        cards = list(self.query(ClusterCard))
        if not cards:
            return
        cards[self._focused_index].toggle_reviewed()

    def action_help(self) -> None:
        if self._help_visible:
            try:
                self.query_one(HelpModal).remove()
            except Exception:
                pass
            self._help_visible = False
        else:
            self.mount(HelpModal())
            self._help_visible = True

    def action_regen(self) -> None:
        self.mount(LoadingIndicator())
        self.run_worker(self._do_regen, exclusive=True)

    async def _do_regen(self) -> None:
        new_session = await asyncio.to_thread(self._regenerate)
        self.post_message(self.ClusteringComplete(new_session))

    @on(ClusteringComplete)
    def on_clustering_complete(self, event: ClusteringComplete) -> None:
        try:
            self.query_one(LoadingIndicator).remove()
        except Exception:
            pass
        self.session = event.session
        self._focused_index = 0
        self._rebuild_list()

    def action_quit_app(self) -> None:
        self.app.exit()
