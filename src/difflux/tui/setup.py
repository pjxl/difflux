from __future__ import annotations

from dataclasses import dataclass

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, LoadingIndicator, OptionList, Static
from textual.widgets.option_list import Option
from textual.worker import Worker, WorkerState

from difflux import clusterer

# Sensible default model for a Direct OpenAI / gateway setup.
_OPENAI_DEFAULT_MODEL = "gpt-4o"

# Connection choices shown on the first wizard step.
_CHOICES: list[tuple[str, str]] = [
    ("anthropic", "Direct Anthropic"),
    ("openai", "Direct OpenAI"),
    ("gateway", "Custom gateway (e.g. LiteLLM)"),
]

# Substring families that are almost never the chat model a user wants. Used as
# a *soft*, reversible blocklist for the large Direct-OpenAI catalog only.
_OPENAI_BLOCKLIST = (
    "embedding",
    "whisper",
    "tts",
    "dall-e",
    "audio",
    "realtime",
    "moderation",
    "image",
    "transcribe",
)

_DIALOG_CSS = """
width: 70;
height: auto;
border: solid $accent;
background: $surface;
padding: 1 2;
"""


def _is_o_series(model_id: str) -> bool:
    """True for OpenAI o-series ids (o1, o3-mini, o4, …)."""
    if len(model_id) < 2 or model_id[0] != "o" or not model_id[1].isdigit():
        return False
    return True


def _rank_models(provider: str, ids: list[str], *, base_url: str | None = None) -> list[str]:
    """Provider-scoped, reversible ranking/soft-filter of model ids.

    - anthropic: keep all, newest-first (reverse-lexical as a proxy).
    - gateway (openai provider + base_url): no name filtering, sort alphabetically.
    - openai (direct): drop obvious non-chat families, gpt-/o-series first.

    Pure and side-effect free so it is unit-testable without Textual.
    """
    if provider == "anthropic":
        return sorted(ids, reverse=True)

    # Gateway: ids are arbitrary/gateway-defined — never hide anything.
    if base_url:
        return sorted(ids)

    # Direct OpenAI: soft blocklist + prefer chat-capable families first.
    def kept(model_id: str) -> bool:
        low = model_id.lower()
        return not any(bad in low for bad in _OPENAI_BLOCKLIST)

    filtered = [m for m in ids if kept(m)]

    def group(model_id: str) -> int:
        low = model_id.lower()
        # Preferred (chat) families first.
        return 0 if (low.startswith("gpt-") or _is_o_series(low)) else 1

    # Stable two-pass sort: reverse-lexical within group, preferred group first.
    by_name = sorted(filtered, reverse=True)
    return sorted(by_name, key=group)


def _dedupe(ids: list[str]) -> list[str]:
    """Order-preserving de-duplication. Gateways (e.g. LiteLLM) can list the
    same model id more than once; duplicates would otherwise crash the picker's
    OptionList (which requires unique option ids)."""
    seen: set[str] = set()
    out: list[str] = []
    for model_id in ids:
        if model_id not in seen:
            seen.add(model_id)
            out.append(model_id)
    return out


@dataclass
class SetupResult:
    provider: str
    base_url: str | None
    model: str
    key: str
    label: str = ""


class SetupWizardApp(App[SetupResult | None]):
    """First-run wizard: collect provider/base_url/key/model, then return them.

    Step order (key precedes model because listing is authenticated):
        choice → base_url (gateway only) → key → model picker

    Thin by design — this app only gathers input and returns a SetupResult.
    Persistence is the caller's job (see apply_setup).
    """

    CSS = f"""
    SetupWizardApp {{ align: center middle; }}
    #d {{ {_DIALOG_CSS} }}
    #hint {{ color: $text-muted; margin-top: 1; }}
    #tip {{ margin-top: 1; }}
    #notice {{ color: $warning; margin-top: 1; }}
    #model-list {{ height: 12; margin-top: 1; }}
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
        self._key: str = ""
        self._model: str = ""
        self._choice_index = 0
        # Model-picker state.
        self._all_models: list[str] = []
        self._ranked_models: list[str] = []
        self._showing_all = False
        self._fetch_worker: Worker | None = None

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
        # Choice-step navigation (only while the choices are still mounted).
        if self._choice_widgets():
            if event.key in ("down", "j"):
                self._focus_choice(self._choice_index + 1)
                event.stop()
            elif event.key in ("up", "k"):
                self._focus_choice(self._choice_index - 1)
                event.stop()
            elif event.key == "enter":
                await self._select_choice(_CHOICES[self._choice_index][0])
                event.stop()
            return

        # Model-picker navigation.
        try:
            option_list = self.query_one("#model-list", OptionList)
        except Exception:
            return

        # Tab toggles the "show all N" (unfiltered) view from anywhere on the
        # model step — the heuristic ranking is always one keystroke reversible.
        if event.key == "tab":
            self._showing_all = not self._showing_all
            current_filter = self.query_one("#model-filter", Input).value
            self._rebuild_option_list(current_filter)
            event.stop()
            return

        # j/k move within the OptionList when it (not the filter Input) is
        # focused, mirroring the choice-step idiom.
        if self.focused is option_list and event.key in ("j", "k"):
            option_list.action_cursor_down() if event.key == "j" else option_list.action_cursor_up()
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
            await self._prompt_key()
        elif choice == "openai":
            self._provider = "openai"
            self._base_url = None
            await self._prompt_key()

    # ---- step 2 (gateway only): base url ----------------------------------

    async def _prompt_base_url(self) -> None:
        await self._swap_to_input(
            title="Custom gateway",
            hint="Base URL of your OpenAI/Anthropic-compatible gateway",
            placeholder="https://litellm.example.com",
            input_id="base-url-input",
            password=False,
        )

    # ---- step 3: key ------------------------------------------------------

    async def _prompt_key(self, *, notice: str | None = None) -> None:
        await self._swap_to_input(
            title="API key",
            hint="Your API key (from your provider or gateway admin)",
            placeholder="API key",
            input_id="key-input",
            password=True,
            notice=notice,
        )

    # ---- step 4: model (live picker, with free-text fallback) -------------

    def _default_model(self) -> str:
        if self._provider == "anthropic":
            return self._default_anthropic_model
        return _OPENAI_DEFAULT_MODEL

    async def _enter_model_step(self) -> None:
        """Show a loading state and kick off the threaded list_models fetch."""
        await self._swap_to_loading()
        self._fetch_worker = self._fetch_models()

    @work(thread=True, exclusive=True)
    def _fetch_models(self) -> list[str] | BaseException:
        """Blocking SDK call — run off the UI thread. The exception is captured
        and returned (not raised) so the worker always completes cleanly; the UI
        thread classifies it in on_worker_state_changed."""
        try:
            return clusterer.list_models(
                self._provider, api_key=self._key, base_url=self._base_url
            )
        except BaseException as exc:  # noqa: BLE001 - classified by the caller
            return exc

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._fetch_worker:
            return
        if event.state != WorkerState.SUCCESS:
            return
        result = event.worker.result
        if isinstance(result, BaseException):
            await self._handle_fetch_error(result)
            return
        models = result or []
        if not models:
            await self._fallback_to_manual_model(
                "Provider reported no models — type one below."
            )
        else:
            self._all_models = list(models)
            await self._swap_to_models(self._all_models)

    async def _handle_fetch_error(self, error: BaseException | None) -> None:
        msg = str(error or "").lower()
        if "401" in msg or "authentication" in msg or "api_key" in msg:
            # Bad key — let the user re-enter it (a manual-model escape is
            # available from the key screen via the tip).
            await self._prompt_key(notice="Key was rejected — re-enter it.")
        else:
            await self._fallback_to_manual_model(
                "Couldn't list models — type one below."
            )

    async def _fallback_to_manual_model(self, notice: str) -> None:
        await self._swap_to_input(
            title="Model",
            hint="Which model should difflux use?",
            placeholder="model name",
            input_id="model-input",
            password=False,
            value=self._default_model(),
            notice=notice,
        )

    def _rebuild_option_list(self, query: str = "") -> None:
        """Repopulate the OptionList from the current (ranked or full) set,
        narrowed by the case-insensitive filter query."""
        if self._showing_all:
            source = sorted(self._all_models)
        else:
            source = _rank_models(
                self._provider, self._all_models, base_url=self._base_url
            )
        self._ranked_models = source

        q = query.strip().lower()
        shown = [m for m in source if q in m.lower()] if q else source

        option_list = self.query_one("#model-list", OptionList)
        option_list.clear_options()
        seen: set[str] = set()
        for model_id in shown:
            if model_id in seen:  # defensive: never let a dup id crash the picker
                continue
            seen.add(model_id)
            option_list.add_option(Option(model_id, id=model_id))

    async def _swap_to_models(self, models: list[str]) -> None:
        self._all_models = _dedupe(models)
        self._showing_all = False
        dialog = self.query_one("#d", Vertical)
        # Await the removal so old ids are gone before mounting (avoids
        # DuplicateIds on the transition — same discipline as _swap_to_input).
        await dialog.remove_children()
        await dialog.mount(
            Static("[bold]difflux — Model[/bold]", markup=True),
            Static("Pick a model (type to filter):", id="hint"),
            Input(placeholder="filter… (Enter on no match uses it as-is)", id="model-filter"),
            OptionList(id="model-list"),
            Static(
                "[dim]↑/↓ or j/k  move · Enter  select · Tab  show all · Esc  cancel[/dim]",
                markup=True,
                id="tip",
            ),
        )
        self._rebuild_option_list()
        self.query_one("#model-filter", Input).focus()

    async def _swap_to_loading(self) -> None:
        dialog = self.query_one("#d", Vertical)
        await dialog.remove_children()
        await dialog.mount(
            Static("[bold]difflux — Model[/bold]", markup=True),
            Static("Fetching available models…", id="hint"),
            LoadingIndicator(),
            Static("[dim]Esc  cancel[/dim]", markup=True, id="tip"),
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
        notice: str | None = None,
    ) -> None:
        dialog = self.query_one("#d", Vertical)
        # Await the removal so the old #hint/#tip nodes are gone before the new
        # ones mount — otherwise Textual raises DuplicateIds on the transition.
        await dialog.remove_children()
        widgets = [
            Static(f"[bold]difflux — {title}[/bold]", markup=True),
            Static(hint, id="hint"),
        ]
        if notice:
            widgets.append(Static(notice, id="notice"))
        widgets.append(
            Input(value=value, placeholder=placeholder, password=password, id=input_id)
        )
        widgets.append(Static("[dim]Enter  next · Esc  cancel[/dim]", markup=True, id="tip"))
        await dialog.mount(*widgets)
        self.query_one(f"#{input_id}", Input).focus()

    def _finish(self, model: str) -> None:
        self.exit(
            SetupResult(
                provider=self._provider,
                base_url=self._base_url,
                model=model,
                key=self._key,
                label="",
            )
        )

    async def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        if event.option_list.id != "model-list":
            return
        model = event.option.id or str(event.option.prompt)
        self._finish(model)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if event.input.id == "base-url-input":
            if not value:
                return
            self._base_url = value
            await self._prompt_key()
        elif event.input.id == "key-input":
            if not value:
                return
            self._key = value
            await self._enter_model_step()
        elif event.input.id == "model-filter":
            # Free-text fallback: if the typed value isn't an exact id in the
            # current set, accept it verbatim (advisory). Otherwise fall through
            # to letting the user pick from the narrowed OptionList via Enter.
            if not value:
                return
            self._finish(value)
        elif event.input.id == "model-input":
            # Manual fallback path (listing unavailable).
            if not value:
                return
            self._finish(value)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "model-filter":
            self._rebuild_option_list(event.value)

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
