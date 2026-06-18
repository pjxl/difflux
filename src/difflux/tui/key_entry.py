from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

_PROVIDERS = ["anthropic", "openai"]

_META: dict[str, dict[str, str]] = {
    "anthropic": {
        "label": "Anthropic",
        "url": "https://console.anthropic.com/",
        "placeholder": "sk-ant-...",
    },
    "openai": {
        "label": "OpenAI",
        "url": "https://platform.openai.com/",
        "placeholder": "sk-...",
    },
}

_DIALOG_CSS = """
width: 70;
height: auto;
border: solid $accent;
background: $surface;
padding: 1 2;
"""


class KeyEntryApp(App[str | None]):
    """Minimal standalone app: collect one API key at startup then exit."""

    CSS = f"""
    KeyEntryApp {{ align: center middle; }}
    #d {{ {_DIALOG_CSS} }}
    #hint {{ color: $text-muted; margin-top: 1; }}
    #tip {{ margin-top: 1; }}
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, provider: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._provider = provider

    def compose(self) -> ComposeResult:
        meta = _META[self._provider]
        with Vertical(id="d"):
            yield Static(f"[bold]difflux — {meta['label']} API Key Required[/bold]", markup=True)
            yield Static(f"Get your key at {meta['url']}", id="hint")
            yield Input(placeholder=meta["placeholder"], password=True, id="key-input")
            yield Static("[dim]Enter  save · Esc  quit without saving[/dim]", markup=True, id="tip")

    def on_mount(self) -> None:
        self.query_one("#key-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        key = event.value.strip()
        if key:
            self.exit(key)

    def action_cancel(self) -> None:
        self.exit(None)


class KeyEditModal(ModalScreen[tuple[str, str] | None]):
    """Two-field form (label + key) for adding or editing one provider slot."""

    CSS = f"""
    KeyEditModal {{ align: center middle; }}
    #d {{ {_DIALOG_CSS} }}
    .field-hint {{ margin-top: 1; }}
    #tip {{ margin-top: 1; }}
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(
        self,
        provider: str,
        existing_label: str = "",
        existing_key: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._provider = provider
        self._existing_label = existing_label
        self._existing_key = existing_key

    def compose(self) -> ComposeResult:
        meta = _META[self._provider]
        verb = "Update" if self._existing_key else "Add"
        with Vertical(id="d"):
            yield Static(f"[bold]{verb} {meta['label']} Key[/bold]", markup=True)
            yield Static('[dim]Label (optional, e.g. "work")[/dim]', markup=True, classes="field-hint")
            yield Input(value=self._existing_label, placeholder="work, personal, ...", id="label-input")
            yield Static("[dim]API Key[/dim]", markup=True, classes="field-hint")
            yield Input(
                value=self._existing_key,
                placeholder=meta["placeholder"],
                password=True,
                id="key-input",
            )
            yield Static("[dim]Tab  next field · Enter  save · Esc  cancel[/dim]", markup=True, id="tip")

    def on_mount(self) -> None:
        self.query_one("#label-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "label-input":
            self.query_one("#key-input", Input).focus()
        elif event.input.id == "key-input":
            self._submit()

    def _submit(self) -> None:
        key = self.query_one("#key-input", Input).value.strip()
        label = self.query_one("#label-input", Input).value.strip()
        if key:
            self.dismiss((key, label))

    def action_cancel(self) -> None:
        self.dismiss(None)


class WalletModal(ModalScreen[None]):
    """Wallet management overlay: add, edit, and delete per-provider API keys."""

    CSS = f"""
    WalletModal {{ align: center middle; }}
    #d {{ {_DIALOG_CSS} }}
    .slot {{ height: 3; padding: 0 1; }}
    .slot:focus {{ background: $accent 20%; }}
    .configured {{ color: $success; }}
    #tip {{ margin-top: 1; }}
    """

    BINDINGS = [
        Binding("j,down", "move_down", "Down"),
        Binding("k,up", "move_up", "Up"),
        Binding("enter", "edit_slot", "Add/Edit"),
        Binding("d", "delete_slot", "Delete"),
        Binding("escape", "dismiss_wallet", "Close"),
    ]

    def __init__(self, active_provider: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._active_provider = active_provider
        self._focused_index = 0

    def compose(self) -> ComposeResult:
        from difflux.config_file import get_wallet

        wallet = get_wallet()
        with Vertical(id="d"):
            yield Static("[bold]API Key Wallet[/bold]", markup=True)
            for provider in _PROVIDERS:
                yield self._build_slot(provider, wallet.get(provider, {}))
            yield Static(
                "[dim]Enter  add/edit · d  delete · Esc  close[/dim]",
                markup=True,
                id="tip",
            )

    def _build_slot(self, provider: str, entry: dict) -> Static:
        text = self._slot_text(provider, entry)
        configured = bool(entry.get("key"))
        classes = "slot configured" if configured else "slot"
        w = Static(text, classes=classes)
        w.can_focus = True
        return w

    def _slot_text(self, provider: str, entry: dict) -> str:
        meta = _META[provider]
        key = entry.get("key", "")
        label = entry.get("label", "")
        marker = " ✓" if provider == self._active_provider else "  "
        if key:
            masked = f"...{key[-4:]}" if len(key) > 4 else "****"
            label_str = f"[{label}]" if label else ""
            return f"{marker} {meta['label']:<12} {label_str:<14} {masked}"
        return f"{marker} {meta['label']:<12} (not configured)"

    def on_mount(self) -> None:
        self._focus_slot(0)

    def _focus_slot(self, index: int) -> None:
        slots = list(self.query(".slot"))
        if not slots:
            return
        self._focused_index = max(0, min(index, len(slots) - 1))
        slots[self._focused_index].focus()

    def action_move_down(self) -> None:
        self._focus_slot(self._focused_index + 1)

    def action_move_up(self) -> None:
        self._focus_slot(self._focused_index - 1)

    def action_edit_slot(self) -> None:
        from difflux.config_file import get_wallet

        provider = _PROVIDERS[self._focused_index]
        entry = get_wallet().get(provider, {})
        self.app.push_screen(
            KeyEditModal(
                provider,
                existing_label=entry.get("label", ""),
                existing_key=entry.get("key", ""),
            ),
            lambda result: self._on_edit_done(provider, result),
        )

    def _on_edit_done(self, provider: str, result: tuple[str, str] | None) -> None:
        if result is None:
            return
        key, label = result
        from difflux.config_file import save_api_key

        save_api_key(provider, key, label)
        self._refresh_slots()

    def action_delete_slot(self) -> None:
        provider = _PROVIDERS[self._focused_index]
        from difflux.config_file import delete_api_key

        delete_api_key(provider)
        self._refresh_slots()

    def _refresh_slots(self) -> None:
        from difflux.config_file import get_wallet

        wallet = get_wallet()
        slots = list(self.query(".slot"))
        for i, provider in enumerate(_PROVIDERS):
            entry = wallet.get(provider, {})
            configured = bool(entry.get("key"))
            slots[i].set_classes("slot configured" if configured else "slot")
            slots[i].update(self._slot_text(provider, entry))
        self._focus_slot(self._focused_index)

    def action_dismiss_wallet(self) -> None:
        self.dismiss(None)
