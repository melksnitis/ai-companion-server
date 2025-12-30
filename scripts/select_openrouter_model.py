#!/usr/bin/env python
"""
Interactive TUI for selecting a free OpenRouter model and updating the .env file.

Usage:
    python scripts/select_openrouter_model.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from decimal import Decimal, InvalidOperation

from dotenv import set_key
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, Switch

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.free_model_policy import OpenRouterModel, free_model_policy_service


LONG_CONTEXT_THRESHOLD = 100_000


def format_price(pricing: dict[str, str]) -> str:
    prompt = pricing.get("prompt") or "0"
    completion = pricing.get("completion") or "0"
    return f"{prompt}/{completion}"


def price_value(pricing: dict[str, str]) -> Decimal:
    try:
        prompt = Decimal(str(pricing.get("prompt") or 0))
        completion = Decimal(str(pricing.get("completion") or 0))
    except (InvalidOperation, TypeError):
        return Decimal("0")
    return prompt + completion


class ModelSelectorApp(App[Optional[OpenRouterModel]]):
    """Textual UI that lists free OpenRouter models and allows selecting one."""

    active_tab = reactive("free")
    filter_long_context = reactive(False)
    sort_mode = reactive("context")

    CSS = """
    Screen {
        layout: vertical;
    }

    .toolbar-label {
        padding-left: 1;
        color: $text-muted;
    }

    #search {
        dock: top;
        padding: 1 2;
        border: tall $primary;
    }

    #toolbar {
        padding: 1;
        border-bottom: solid $panel;
        background: $surface;
        align: center middle;
    }

    #toolbar > * {
        margin-right: 1;
    }

    #filter_container {
        align: center middle;
    }

    Button.tab {
        margin-right: 1;
        background: $surface;
        color: $text-muted;
    }

    Button.tab.-active {
        background: $primary;
        color: $text;
    }

    #content {
        height: 1fr;
    }

    #models {
        width: 2fr;
    }

    #details {
        width: 1fr;
        border: tall $secondary;
        padding: 1 2;
    }

    #status {
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("enter", "select_model", "Select model"),
        ("/", "focus_search", "Search"),
        ("f", "show_free", "Free tab"),
        ("p", "show_paid", "Paid tab"),
        ("l", "toggle_long_context", "Filter ≥100k ctx"),
        ("s", "cycle_sort", "Sort price/context"),
    ]

    def __init__(self, models: List[OpenRouterModel]) -> None:
        super().__init__()
        self._all_models = models
        self._free_models = [m for m in models if m.is_free()]
        self._paid_models = [m for m in models if not m.is_free()]
        self._filtered_models = []
        self._row_to_model: dict[str, OpenRouterModel] = {}
        self.selected_model: Optional[OpenRouterModel] = None
        self._search_query: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="Press '/' to search free models...", id="search")
        with Horizontal(id="toolbar"):
            yield Button("Free Models (F)", id="tab_free", classes="tab")
            yield Button("Paid Models (P)", id="tab_paid", classes="tab")
            yield Button("Sort: Context ↓ (S)", id="sort_button")
            with Horizontal(id="filter_container"):
                yield Switch(id="filter_switch", value=False)
                yield Static("≥100k ctx (L)", classes="toolbar-label")
        with Horizontal(id="content"):
            yield DataTable(id="models")
            with Vertical(id="details"):
                yield Static("Select a model to see details.", id="details_text")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#models", DataTable)
        table.focus()
        table.add_columns("Model ID", "Name", "Context", "Provider", "Prompt/Completion")
        self._refresh_table()
        search = self.query_one("#search", Input)
        search.display = False
        self._update_status(
            f"Loaded {len(self._free_models)} free models and {len(self._paid_models)} paid models."
        )
        self._update_tab_buttons()
        self._update_sort_button()

    def action_focus_search(self) -> None:
        search = self.query_one("#search", Input)
        search.display = True
        search.value = ""
        self.set_focus(search)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search":
            event.input.blur()
            event.input.display = False

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search":
            return
        self._search_query = event.value.strip().lower()
        self._refresh_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        table = event.data_table
        if not table.row_count:
            return
        row_key = event.row_key
        model = self._row_to_model.get(row_key)
        if model:
            self.selected_model = model
            self._render_details(model)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        model = self._row_to_model.get(event.row_key)
        if model:
            self._finalize_selection(model)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "tab_free":
            self.action_show_free()
        elif event.button.id == "tab_paid":
            self.action_show_paid()
        elif event.button.id == "sort_button":
            self.action_cycle_sort()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "filter_switch":
            self.filter_long_context = event.value
            self._refresh_table()

    def watch_filter_long_context(self, value: bool) -> None:
        switch = self.query_one("#filter_switch", Switch)
        switch.value = value
        self._refresh_table()

    def watch_sort_mode(self, _: str) -> None:
        self._update_sort_button()
        self._refresh_table()

    def watch_active_tab(self, _: str) -> None:
        self._update_tab_buttons()
        self._refresh_table()

    def action_show_free(self) -> None:
        self.active_tab = "free"

    def action_show_paid(self) -> None:
        self.active_tab = "paid"

    def action_toggle_long_context(self) -> None:
        self.filter_long_context = not self.filter_long_context

    def action_cycle_sort(self) -> None:
        order = ["context", "price_asc", "price_desc"]
        idx = order.index(self.sort_mode)
        self.sort_mode = order[(idx + 1) % len(order)]

    def _refresh_table(self) -> None:
        models = self._apply_filters()
        table = self.query_one("#models", DataTable)
        table.clear()
        self._row_to_model.clear()
        self._filtered_models = models
        if not self._filtered_models:
            self._update_status("No models matched your search.")
            return
        for idx, model in enumerate(self._filtered_models):
            table.add_row(
                model.id,
                model.name or "—",
                f"{model.context_length or '—'} tokens",
                model.provider or "—",
                format_price(model.pricing),
                key=str(idx),
            )
            self._row_to_model[str(idx)] = model
        table.cursor_type = "row"
        table.cursor_coordinate = (0, 0)
        first_model = self._row_to_model.get("0")
        if first_model:
            self._render_details(first_model)

    def _render_details(self, model: OpenRouterModel) -> None:
        details = self.query_one("#details_text", Static)
        pricing_lines = "\n".join(
            f"- {key.title()}: {value}"
            for key, value in model.pricing.items()
            if value not in (None, "")
        ) or "- None"
        details.update(
            f"[b]{model.name or model.id}[/b]\n"
            f"ID: [cyan]{model.id}[/cyan]\n"
            f"Provider: {model.provider or 'Unknown'}\n"
            f"Context Length: {model.context_length or 'Unknown'}\n"
            f"\nPricing:\n{pricing_lines}\n"
            f"\nDescription:\n{model.description or 'No description provided.'}"
        )

    def action_select_model(self) -> None:
        table = self.query_one("#models", DataTable)
        if not table.row_count:
            return
        row_key = table.coordinate_to_key(table.cursor_coordinate)
        model = self._row_to_model.get(row_key)
        if model:
            self._finalize_selection(model)

    def _finalize_selection(self, model: OpenRouterModel) -> None:
        self.selected_model = model
        self.exit(model)

    def action_quit(self) -> None:
        self.exit(None)

    def _update_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _update_tab_buttons(self) -> None:
        free_button = self.query_one("#tab_free", Button)
        paid_button = self.query_one("#tab_paid", Button)
        free_button.set_class(self.active_tab == "free", "-active")
        paid_button.set_class(self.active_tab == "paid", "-active")

    def _update_sort_button(self) -> None:
        button = self.query_one("#sort_button", Button)
        label = {
            "context": "Sort: Context ↓ (S)",
            "price_asc": "Sort: Price ↑ (S)",
            "price_desc": "Sort: Price ↓ (S)",
        }[self.sort_mode]
        button.label = label

    def _apply_filters(self) -> List[OpenRouterModel]:
        models = self._free_models if self.active_tab == "free" else self._paid_models
        if self.filter_long_context:
            models = [m for m in models if (m.context_length or 0) >= LONG_CONTEXT_THRESHOLD]
        models = self._sort_models(models)
        if not self._search_query:
            return models
        query = self._search_query
        return [
            model
            for model in models
            if query in model.id.lower()
            or (model.name and query in model.name.lower())
            or (model.provider and query in model.provider.lower())
        ]

    def _sort_models(self, models: Iterable[OpenRouterModel]) -> List[OpenRouterModel]:
        if self.sort_mode == "context":
            return sorted(
                models,
                key=lambda model: (
                    -(model.context_length or 0),
                    price_value(model.pricing),
                    model.id,
                ),
            )
        if self.sort_mode == "price_asc":
            return sorted(
                models,
                key=lambda model: (price_value(model.pricing), -(model.context_length or 0), model.id),
            )
        # price_desc
        return sorted(
            models,
            key=lambda model: (
                -price_value(model.pricing),
                -(model.context_length or 0),
                model.id,
            ),
        )


def ensure_env_file(path: Path) -> None:
    if not path.exists():
        path.touch()


def update_env_value(env_path: Path, key: str, value: str) -> None:
    ensure_env_file(env_path)
    set_key(str(env_path), key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select a free OpenRouter model and update .env.")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the env file to update (default: .env)",
    )
    parser.add_argument(
        "--update-example",
        action="store_true",
        help="Also update .env.example with the selected model.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not modify files; just display the selection.",
    )
    return parser.parse_args()


def run_cli(args: argparse.Namespace) -> int:
    env_file = Path(args.env_file)
    example_file = Path(".env.example")

    try:
        models = asyncio.run(free_model_policy_service.fetch_models(force_refresh=True))
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Failed to fetch OpenRouter models: {exc}", file=sys.stderr)
        return 1

    if not models:
        print("❌ No OpenRouter models available for your account.", file=sys.stderr)
        return 1

    selection = ModelSelectorApp(models).run()
    if selection is None:
        print("No model selected. Exiting.")
        return 1

    print(f"✅ Selected model: {selection.id}")
    if args.dry_run:
        print("Dry-run enabled; no files updated.")
        return 0

    update_env_value(env_file, "OPENROUTER_MODEL_ID", selection.id)
    print(f"Updated {env_file} with OPENROUTER_MODEL_ID={selection.id}")

    if args.update_example:
        update_env_value(example_file, "OPENROUTER_MODEL_ID", selection.id)
        print(f"Updated {example_file} with OPENROUTER_MODEL_ID={selection.id}")

    print("\nPlease restart the server or reload configuration to apply the new model.")
    return 0


def main() -> None:
    args = parse_args()
    raise SystemExit(run_cli(args))


if __name__ == "__main__":
    main()
