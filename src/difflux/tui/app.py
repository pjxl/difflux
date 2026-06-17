from __future__ import annotations

from typing import Callable

from textual.app import App

from difflux.enrich import ReviewSession
from difflux.models import ClusteringType


class DiffluxApp(App):

    CSS = """
    Screen {
        background: $surface;
    }
    #overview-header {
        padding: 0 1;
        background: $panel;
        color: $text;
    }
    #rule-top, #rule-bottom {
        color: $primary-darken-2;
        padding: 0 1;
    }
    #cluster-list {
        height: 1fr;
        padding: 0 1;
    }
    #drill-header {
        padding: 1 2;
        background: $panel;
    }
    #hunk-scroll {
        height: 1fr;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        session: ReviewSession,
        regenerate: Callable[[], ReviewSession],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.session = session
        self._regenerate = regenerate

    def on_mount(self) -> None:
        from difflux.tui.overview import OverviewScreen
        from difflux.tui.drilldown import SingleIdeaScreen

        if self.session.clustering_type == ClusteringType.SINGLE_IDEA:
            self.push_screen(SingleIdeaScreen(self.session))
        else:
            self.push_screen(OverviewScreen(self.session, self._regenerate))
