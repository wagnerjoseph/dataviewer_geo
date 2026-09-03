"""Interactive var_specs editor for plotting_joseph integration.

Provides Panel widgets for configuring var_specs without writing code.
"""

import panel as pn
import param

pn.extension()


class VarSpecEditor(param.Parameterized):
    """Interactive editor for building var_specs for plot_time_series.

    Each variable/panel is represented as a row of widgets. Users can add/remove
    variables, configure overlays, secondary axes, colors, transforms, thresholds, etc.
    """

    available_variables = param.List(default=[], doc="Available data columns")
    add_variable_btn = param.Action(default=lambda x: x.add_var(), doc="Add variable")

    def __init__(self, available_variables: list[str] | None = None, **params):
        super().__init__(**params)
        if available_variables:
            self.available_variables = available_variables
        self._var_widgets: list[dict] = []
        self._var_counter = 0

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
                name=f"Variable {var_id} - Name",
                options=self.available_variables,
                value=name
                if name in self.available_variables
                else (
                    self.available_variables[0] if self.available_variables else None
                ),
            ),
            "label": pn.widgets.TextInput(
                name=f"Variable {var_id} - Label",
                value=name.replace("_", " ").title() if name else "",
            ),
            "color": pn.widgets.ColorPicker(
                name=f"Variable {var_id} - Color",
                value="#1f77b4",
            ),
            "line_width": pn.widgets.FloatSlider(
                name=f"Variable {var_id} - Line Width",
                start=0.5,
                end=5,
                step=0.5,
                value=1.5,
            ),
            "alpha": pn.widgets.FloatSlider(
                name=f"Variable {var_id} - Alpha",
                start=0.1,
                end=1.0,
                step=0.1,
                value=1.0,
            ),
            "plotstyle": pn.widgets.Select(
                name=f"Variable {var_id} - Plot Style",
                options=["line", "points", "both"],
                value="line",
            ),
            "show_seasons": pn.widgets.Checkbox(
                name=f"Variable {var_id} - Show Seasons (JJA/DJF)",
                value=False,
            ),
            "interpolate": pn.widgets.Checkbox(
                name=f"Variable {var_id} - Interpolate NaNs",
                value=False,
            ),
            "add_to": pn.widgets.Select(
                name=f"Variable {var_id} - Overlay On (None = new panel)",
                options=["None"],
                value="None",
            ),
            "add_second_axis": pn.widgets.Checkbox(
                name=f"Variable {var_id} - Add Second Y-Axis",
                value=False,
            ),
            "align_zero": pn.widgets.Checkbox(
                name=f"Variable {var_id} - Align Zero Points",
                value=False,
            ),
            "compute_corr": pn.widgets.Checkbox(
                name=f"Variable {var_id} - Show Correlation",
                value=False,
            ),
            "lower_threshold_val": pn.widgets.FloatInput(
                name=f"Variable {var_id} - Lower Threshold Value",
                value=None,
            ),
            "lower_threshold_color": pn.widgets.ColorPicker(
                name=f"Variable {var_id} - Lower Threshold Color",
                value="#ff0000",
            ),
            "upper_threshold_val": pn.widgets.FloatInput(
                name=f"Variable {var_id} - Upper Threshold Value",
                value=None,
            ),
            "upper_threshold_color": pn.widgets.ColorPicker(
                name=f"Variable {var_id} - Upper Threshold Color",
                value="#0000ff",
            ),
            "apply_shading_to_all": pn.widgets.Checkbox(
                name=f"Variable {var_id} - Apply Shading to All Panels",
                value=False,
            ),
            "remove_btn": pn.widgets.Button(
                name=f"Remove Variable {var_id}",
                button_type="danger",
            ),
        }

        # Wire up remove button
        def on_remove(event):
            self.remove_var(var_id)

        widgets["remove_btn"].on_click(on_remove)
        self._var_widgets.append(widgets)
        self._update_overlay_options()

    def remove_var(self, var_id: int) -> None:
        """Remove a variable spec widget group."""
        self._var_widgets = [w for i, w in enumerate(self._var_widgets) if i != var_id]
        self._update_overlay_options()

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

    def render(self) -> pn.Column:
        """Render the editor as a Panel layout."""
        rows = []
        for i, widgets in enumerate(self._var_widgets):
            row = pn.Row(
                pn.Column(
                    widgets["name"],
                    widgets["label"],
                    widgets["color"],
                    widgets["line_width"],
                    widgets["alpha"],
                    widgets["plotstyle"],
                    width=200,
                ),
                pn.Column(
                    widgets["show_seasons"],
                    widgets["interpolate"],
                    widgets["add_to"],
                    widgets["add_second_axis"],
                    widgets["align_zero"],
                    widgets["compute_corr"],
                    width=250,
                ),
                pn.Column(
                    widgets["lower_threshold_val"],
                    widgets["lower_threshold_color"],
                    widgets["upper_threshold_val"],
                    widgets["upper_threshold_color"],
                    widgets["apply_shading_to_all"],
                    width=250,
                ),
                widgets["remove_btn"],
                margin=5,
            )
            rows.append(row)

        add_btn = pn.widgets.Button(
            name="Add Variable",
            button_type="success",
            width=200,
        )
        add_btn.on_click(lambda e: self.add_var())

        return pn.Column(
            pn.pane.Markdown("### Configure Variables / Panels"),
            pn.pane.Markdown(
                "*Each row = one variable/panel. Set 'Overlay On' to add to an existing panel.*"
            ),
            add_btn,
            *rows,
        )


def create_var_spec_editor(available_variables: list[str]) -> VarSpecEditor:
    """Create a var_spec editor with the given available variables."""
    return VarSpecEditor(available_variables=available_variables)
