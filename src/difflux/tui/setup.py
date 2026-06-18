from __future__ import annotations

from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, Static

# Sensible default model for a Direct OpenAI setup.
_OPENAI_DEFAULT_MODEL = "gpt-4o"

# Connection choices shown on the first wizard step.
_CHOICES: list[tuple[str, str]] = [
    ("anthropic", "Direct Anthropic"),
    ("openai", "Direct OpenAI"),
    ("gateway", "Custom gateway (e.g. LiteLLM)"),
]

_DIALOG_CSS = """
width: 70;
height: auto;
border: solid $accent;
background: $surface;
padding: 1 2;
"""


@dataclass
class SetupResult:
    provider: str
    base_url: str | None
    model: str
    key: str
    label: str = ""


class SetupWizardApp(App[SetupResult | None]):
    """First-run wizard: collect provider/base_url/model/key, then return them.

    Thin by design — this app only gathers input and returns a SetupResult.
    Persistence is the caller's job (see apply_setup).
    """

    CSS = f"""
    SetupWizardApp {{ align: center middle; }}
    #d {{ {_DIALOG_CSS} }}
    #hint {{ color: $text-muted; margin-top: 1; }}
    #tip {{ margin-top: 1; }}
    .choice {{ height: 1; padding: 0 1; }}
    .choice:focus {{ background: $accent 20%; }}
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, *, default_anthropic_model: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._default_anthropic_model = default_anthropic_model
        # Accumulated values across steps.
        self._provider: str = ""
        self._base_url: str | None = None
        self._model: str = ""
        self._choice_index = 0

    # ---- step 1: choose how to reach a model ------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="d"):
            yield Static("[bold]difflux — First-run setup[/bold]", markup=True)
            yield Static("How do you reach a model?", id="hint")
            for value, text in _CHOICES:
                w = Static(text, classes="choice", id=f"choice-{value}")
                w.can_focus = True
                yield w
            yield Static(
                "[dim]j/k or ↑/↓  move · Enter  select · Esc  cancel[/dim]",
                markup=True,
                id="tip",
            )

    def on_mount(self) -> None:
        self._focus_choice(0)

    def _choice_widgets(self) -> list[Static]:
        return list(self.query(".choice"))

    def _focus_choice(self, index: int) -> None:
        choices = self._choice_widgets()
        if not choices:
            return
        self._choice_index = max(0, min(index, len(choices) - 1))
        choices[self._choice_index].focus()

    async def on_key(self, event) -> None:
        # Only act on the choice step (the choices are still mounted).
        if not self._choice_widgets():
            return
        if event.key in ("down", "j"):
            self._focus_choice(self._choice_index + 1)
            event.stop()
        elif event.key in ("up", "k"):
            self._focus_choice(self._choice_index - 1)
            event.stop()
        elif event.key == "enter":
            await self._select_choice(_CHOICES[self._choice_index][0])
            event.stop()

    async def _select_choice(self, choice: str) -> None:
        if choice == "gateway":
            # Gateways like LiteLLM are OpenAI-compatible, so route through the
            # OpenAI provider even when the underlying model is Claude.
            self._provider = "openai"
            await self._prompt_base_url()
        elif choice == "anthropic":
            self._provider = "anthropic"
            self._base_url = None
            await self._prompt_model(self._default_anthropic_model)
        elif choice == "openai":
            self._provider = "openai"
            self._base_url = None
            await self._prompt_model(_OPENAI_DEFAULT_MODEL)

    # ---- step 2 (gateway only): base url ----------------------------------

    async def _prompt_base_url(self) -> None:
        await self._swap_to_input(
            title="Custom gateway",
            hint="Base URL of your OpenAI/Anthropic-compatible gateway",
            placeholder="https://litellm.example.com",
            input_id="base-url-input",
            password=False,
        )

    # ---- step 3: model ----------------------------------------------------

    async def _prompt_model(self, default: str) -> None:
        await self._swap_to_input(
            title="Model",
            hint="Which model should difflux use?",
            placeholder="model name",
            input_id="model-input",
            password=False,
            value=default,
        )

    # ---- step 4: key ------------------------------------------------------

    async def _prompt_key(self) -> None:
        await self._swap_to_input(
            title="API key",
            hint="Your API key (from your provider or gateway admin)",
            placeholder="API key",
            input_id="key-input",
            password=True,
        )

    # ---- helpers ----------------------------------------------------------

    async def _swap_to_input(
        self,
        *,
        title: str,
        hint: str,
        placeholder: str,
        input_id: str,
        password: bool,
        value: str = "",
    ) -> None:
        dialog = self.query_one("#d", Vertical)
        # Await the removal so the old #hint/#tip nodes are gone before the new
        # ones mount — otherwise Textual raises DuplicateIds on the transition.
        await dialog.remove_children()
        await dialog.mount(
            Static(f"[bold]difflux — {title}[/bold]", markup=True),
            Static(hint, id="hint"),
            Input(value=value, placeholder=placeholder, password=password, id=input_id),
            Static("[dim]Enter  next · Esc  cancel[/dim]", markup=True, id="tip"),
        )
        self.query_one(f"#{input_id}", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if event.input.id == "base-url-input":
            if not value:
                return
            self._base_url = value
            await self._prompt_model("")
        elif event.input.id == "model-input":
            if not value:
                return
            self._model = value
            await self._prompt_key()
        elif event.input.id == "key-input":
            if not value:
                return
            self.exit(
                SetupResult(
                    provider=self._provider,
                    base_url=self._base_url,
                    model=self._model,
                    key=value,
                )
            )

    def action_cancel(self) -> None:
        self.exit(None)


def apply_setup(result: SetupResult) -> None:
    """Persist a wizard result: defaults first, then the API key."""
    from difflux import config_file

    config_file.save_defaults(
        provider=result.provider,
        base_url=result.base_url,
        model=result.model,
    )
    config_file.save_api_key(result.provider, result.key, result.label)
