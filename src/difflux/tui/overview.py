from __future__ import annotations

import asyncio
from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Static, Footer, LoadingIndicator
from textual.containers import VerticalScroll
from textual.worker import Worker, WorkerState

from difflux.enrich import ClusterView, ReviewSession
from difflux.tui.widgets import ClusterCard, HelpModal


class OverviewScreen(Screen):
    """Phase one: navigable cluster list."""

    DEFAULT_CSS = """
    OverviewScreen #overview-banner {
        color: $warning;
        padding: 0 0 1 0;
    }
    OverviewScreen #cluster-list {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("j,down", "move_down", "Down"),
        ("k,up", "move_up", "Up"),
        ("enter", "drill_in", "Expand"),
        ("space", "toggle_reviewed", "Mark reviewed"),
        ("r", "regen", "Regenerate (same model)"),
        ("K", "manage_keys", "API Keys"),
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
        provider: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.session = session
        self._regenerate = regenerate
        self.model = model
        self._provider = provider
        self._focused_index = 0
        self._help_visible = False

    def compose(self) -> ComposeResult:
        yield Static(id="overview-header")
        yield Static(id="overview-banner", markup=False)
        yield Static(id="rule-top", markup=False)
        with VerticalScroll(id="cluster-list"):
            pass
        yield Static(id="rule-bottom", markup=False)
        yield Footer()

    async def on_mount(self) -> None:
        await self._rebuild_list()

    async def _rebuild_list(self) -> None:
        s = self.session
        self._update_header()
        self._update_banner()
        rule = "─" * 58
        self.query_one("#rule-top", Static).update(rule)
        self.query_one("#rule-bottom", Static).update(rule)

        max_churn = max((v.churn for v in s.clusters), default=0)
        container = self.query_one("#cluster-list", VerticalScroll)
        await container.remove_children()
        cards = [
            ClusterCard(view, i + 1, max_churn=max_churn, id=f"card-{i}")
            for i, view in enumerate(s.clusters)
        ]
        if cards:
            await container.mount(*cards)

        self._focus_card(self._focused_index)

    def _update_header(self) -> None:
        s = self.session
        reviewed = sum(1 for v in s.clusters if v.reviewed)
        self.query_one("#overview-header", Static).update(
            f"[bold]difflux[/bold]  ·  {self.model}  ·  {len(s.clusters)} clusters"
            f"  ·  {s.total_files} files  ·  {reviewed}/{len(s.clusters)} reviewed",
        )

    def _update_banner(self) -> None:
        s = self.session
        banner = self.query_one("#overview-banner", Static)
        parts = []
        if s.note:
            parts.append(f"Note: {s.note}")
        if s.coverage:
            parts.append(f"Coverage: {s.coverage}")
        if parts:
            banner.update("\n".join(parts))
            banner.display = True
        else:
            banner.display = False

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
        index = self._focused_index
        view = self.session.clusters[index]
        from difflux.tui.drilldown import DrillDownScreen

        def _on_drill_closed(reviewed: bool) -> None:
            if reviewed:
                cards[index].sync_reviewed()
                self._update_header()

        self.app.push_screen(DrillDownScreen(view), _on_drill_closed)

    def action_toggle_reviewed(self) -> None:
        cards = list(self.query(ClusterCard))
        if not cards:
            return
        cards[self._focused_index].toggle_reviewed()
        self._update_header()

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

    def action_manage_keys(self) -> None:
        from difflux.tui.key_entry import WalletModal
        self.app.push_screen(WalletModal(self._provider), self._on_wallet_closed)

    def _on_wallet_closed(self, _: None) -> None:
        pass

    def action_regen(self) -> None:
        self.mount(LoadingIndicator())
        self._regen_worker = self.run_worker(self._do_regen, exclusive=True, exit_on_error=False)

    async def _do_regen(self) -> None:
        new_session = await asyncio.to_thread(self._regenerate)
        self.post_message(self.ClusteringComplete(new_session))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.ERROR:
            try:
                self.query_one(LoadingIndicator).remove()
            except Exception:
                pass
            self.notify(str(event.worker.error), severity="error")

    @on(ClusteringComplete)
    async def on_clustering_complete(self, event: ClusteringComplete) -> None:
        try:
            self.query_one(LoadingIndicator).remove()
        except Exception:
            pass
        self.session = event.session
        self.app.session = event.session
        self._focused_index = 0
        await self._rebuild_list()

    def action_quit_app(self) -> None:
        self.app.exit()
