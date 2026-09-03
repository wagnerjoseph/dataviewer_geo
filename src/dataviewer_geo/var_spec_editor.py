"""Interactive var_specs editor for plotting_joseph integration.

Provides Panel widgets for configuring var_specs without writing code.
Features:
- Live layout: add/remove variables updates the UI immediately
- Simplified essentials: Variable, Overlay, Color, Plot Style, Label
- Advanced controls collapsed in accordion per row
- Auto-update callback (debounced) when config changes
"""

from typing import Callable

import panel as pn
import param

pn.extension()


class VarSpecEditor(param.Parameterized):
    """Interactive editor for building var_specs for plot_time_series.

    Each variable/panel is represented as a compact row with essential controls.
    Advanced options are in a collapsible accordion per row.
    """

    available_variables = param.List(default=[], doc="Available data columns")

    def __init__(
        self,
        available_variables: list[str] | None = None,
        on_config_change: Callable | None = None,
        **params,
    ):
        super().__init__(**params)
        if available_variables:
            self.available_variables = available_variables
        self.on_config_change = on_config_change
        self._var_widgets: list[dict] = []
        self._var_counter = 0
        self._debounce_timer = None

        # Live layout container
        self.layout = pn.Column(
            pn.pane.Markdown("### Timeseries Configuration"),
            pn.pane.Markdown(
                "*Each row = one variable. Click 'Add Variable' to add more. "
                "Advanced options are in the collapsible accordion.*"
            ),
            sizing_mode="stretch_width",
        )
        self._refresh_layout()

    def _debounced_trigger(self):
        """Trigger on_config_change with debounce (~300ms)."""
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()

        def trigger():
            if self.on_config_change:
                self.on_config_change()

        # In server context, use Panel's debounce; otherwise call immediately
        if pn.state.curdoc is not None:
            self._debounce_timer = pn.state.curdoc.add_timeout_callback(trigger, 300)
        else:
            # For testing/script context, call immediately
            trigger()

    def _on_widget_change(self, event=None):
        """Called when any widget changes - triggers debounced update."""
        self._debounced_trigger()

    def _refresh_layout(self):
        """Rebuild the layout from current _var_widgets."""
        rows = []
        for i, widgets in enumerate(self._var_widgets):
            # Essentials row
            essentials = pn.Row(
                pn.Column(
                    widgets["name"],
                    widgets["label"],
                    width=200,
                ),
                pn.Column(
                    widgets["color"],
                    widgets["plotstyle"],
                    width=200,
                ),
                pn.Column(
                    widgets["add_to"],
                    width=200,
                ),
                widgets["remove_btn"],
                margin=5,
            )

            # Advanced accordion
            advanced = pn.Accordion(
                (
                    "Advanced",
                    pn.Column(
                        pn.Row(
                            pn.Column(widgets["line_width"], widgets["alpha"], width=200),
                            pn.Column(
                                widgets["show_seasons"],
                                widgets["interpolate"],
                                width=200,
                            ),
                            pn.Column(
                                widgets["add_second_axis"],
                                widgets["align_zero"],
                                widgets["compute_corr"],
                                width=200,
                            ),
                        ),
                        pn.Row(
                            pn.Column(
                                widgets["lower_threshold_val"],
                                widgets["lower_threshold_color"],
                                width=200,
                            ),
                            pn.Column(
                                widgets["upper_threshold_val"],
                                widgets["upper_threshold_color"],
                                width=200,
                            ),
                            widgets["apply_shading_to_all"],
                        ),
                        sizing_mode="stretch_width",
                    ),
                ),
                active=[],  # collapsed by default
            )

            row = pn.Column(essentials, advanced, sizing_mode="stretch_width")
            rows.append(row)

        # Add button
        add_btn = pn.widgets.Button(
            label="Add Variable",
            color="success",
            width=200,
            margin=(10, 5),
        )
        add_btn.on_click(lambda e: self.add_var())

        # Rebuild layout
        self.layout.objects = [
            self.layout.objects[0],  # Title
            self.layout.objects[1],  # Instructions
            add_btn,
            *rows,
        ]

    def add_var(self, name: str | None = None) -> None:
        """Add a new variable spec widget group."""
        var_id = self._var_counter
        self._var_counter += 1

        if name is None and self.available_variables:
            # Default to first unused variable
            used = {w["name"].value for w in self._var_widgets if w["name"].value}
            for v in self.available_variables:
                if v not in used:
                    name = v
                    break
            if name is None:
                name = self.available_variables[0] if self.available_variables else ""

        widgets = {
            "name": pn.widgets.Select(
                options=self.available_variables,
                value=name if name in self.available_variables else (self.available_variables[0] if self.available_variables else None),
            ),
            "label": pn.widgets.TextInput(
                value=name.replace("_", " ").title() if name else "",
            ),
            "color": pn.widgets.ColorPicker(value="#1f77b4"),
            "line_width": pn.widgets.FloatSlider(
                start=0.5, end=5, step=0.5, value=1.5
            ),
            "alpha": pn.widgets.FloatSlider(start=0.1, end=1.0, step=0.1, value=1.0),
            "plotstyle": pn.widgets.Select(
                options=["line", "points", "both"], value="line"
            ),
            "show_seasons": pn.widgets.Checkbox(value=False),
            "interpolate": pn.widgets.Checkbox(value=False),
            "add_to": pn.widgets.Select(options=["None"], value="None"),
            "add_second_axis": pn.widgets.Checkbox(value=False),
            "align_zero": pn.widgets.Checkbox(value=False),
            "compute_corr": pn.widgets.Checkbox(value=False),
            "lower_threshold_val": pn.widgets.FloatInput(value=None),
            "lower_threshold_color": pn.widgets.ColorPicker(value="#ff0000"),
            "upper_threshold_val": pn.widgets.FloatInput(value=None),
            "upper_threshold_color": pn.widgets.ColorPicker(value="#0000ff"),
            "apply_shading_to_all": pn.widgets.Checkbox(value=False),
            "remove_btn": pn.widgets.Button(
                label=f"Remove {var_id}",
                color="danger",
                width=100,
            ),
        }

        # Wire up all widgets to trigger change
        for key, widget in widgets.items():
            if hasattr(widget, "param") and hasattr(widget.param, "value"):
                widget.param.watch(self._on_widget_change, "value")

        # Wire up remove button
        def on_remove(event):
            self.remove_var(var_id)

        widgets["remove_btn"].on_click(on_remove)
        self._var_widgets.append(widgets)
        self._update_overlay_options()
        self._refresh_layout()
        self._on_widget_change()

    def remove_var(self, var_id: int) -> None:
        """Remove a variable spec widget group."""
        self._var_widgets = [
            w for i, w in enumerate(self._var_widgets) if i != var_id
        ]
        self._update_overlay_options()
        self._refresh_layout()
        self._on_widget_change()

    def _update_overlay_options(self) -> None:
        """Update 'add_to' dropdown options with current panel variables."""
        panel_vars = [
            w["name"].value for w in self._var_widgets if w["add_to"].value == "None"
        ]
        for widgets in self._var_widgets:
            current = widgets["add_to"].value
            widgets["add_to"].options = ["None"] + panel_vars
            if current in widgets["add_to"].options:
                widgets["add_to"].value = current

    def to_var_specs(self) -> list[dict]:
        """Collect widget states into var_specs list for plot_time_series."""
        specs = []
        for widgets in self._var_widgets:
            name = widgets["name"].value
            if not name:
                continue

            spec = {
                "name": name,
                "label": widgets["label"].value,
                "color": widgets["color"].value,
                "line_width": widgets["line_width"].value,
                "alpha": widgets["alpha"].value,
                "plotstyle": widgets["plotstyle"].value,
                "show_seasons": widgets["show_seasons"].value,
                "interpolate": widgets["interpolate"].value,
            }

            # Overlay settings
            add_to = widgets["add_to"].value
            if add_to != "None":
                spec["add_to"] = add_to
                if widgets["add_second_axis"].value:
                    spec["add_second_axis"] = True
                if widgets["align_zero"].value:
                    spec["align_zero"] = True
                if widgets["compute_corr"].value:
                    spec["compute_corr"] = True

            # Thresholds
            lower_val = widgets["lower_threshold_val"].value
            if lower_val is not None:
                spec["lower_treshold"] = (
                    lower_val,
                    widgets["lower_threshold_color"].value,
                )

            upper_val = widgets["upper_threshold_val"].value
            if upper_val is not None:
                spec["upper_treshold"] = (
                    upper_val,
                    widgets["upper_threshold_color"].value,
                )

            if widgets["apply_shading_to_all"].value:
                spec["apply_shading_to_all"] = True

            specs.append(spec)

        return specs


def create_var_spec_editor(
    available_variables: list[str], on_config_change: Callable | None = None
) -> VarSpecEditor:
    """Create a var_spec editor with the given available variables."""
    return VarSpecEditor(
        available_variables=available_variables, on_config_change=on_config_change
    )
