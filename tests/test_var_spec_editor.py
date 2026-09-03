"""Tests for var_spec_editor."""

from dataviewer_geo.var_spec_editor import VarSpecEditor, create_var_spec_editor


class TestVarSpecEditor:
    """Tests for VarSpecEditor class."""

    def test_create_editor(self):
        """Test creating an editor."""
        editor = VarSpecEditor(available_variables=["var1", "var2", "var3"])
        assert editor.available_variables == ["var1", "var2", "var3"]

    def test_add_var(self):
        """Test adding a variable."""
        editor = VarSpecEditor(available_variables=["var1", "var2"])
        editor.add_var("var1")
        assert len(editor._var_widgets) == 1
        assert editor._var_widgets[0]["name"].value == "var1"

    def test_remove_var(self):
        """Test removing a variable."""
        editor = VarSpecEditor(available_variables=["var1", "var2"])
        editor.add_var("var1")
        editor.add_var("var2")
        assert len(editor._var_widgets) == 2

        editor.remove_var(0)
        assert len(editor._var_widgets) == 1
        assert editor._var_widgets[0]["name"].value == "var2"

    def test_to_var_specs(self):
        """Test converting widgets to var_specs."""
        editor = VarSpecEditor(available_variables=["var1", "var2"])
        editor.add_var("var1")

        # Set some values
        editor._var_widgets[0]["label"].value = "Variable 1"
        editor._var_widgets[0]["color"].value = "#ff0000"
        editor._var_widgets[0]["line_width"].value = 2.0

        specs = editor.to_var_specs()
        assert len(specs) == 1
        assert specs[0]["name"] == "var1"
        assert specs[0]["label"] == "Variable 1"
        assert specs[0]["color"] == "#ff0000"
        assert specs[0]["line_width"] == 2.0

    def test_to_var_specs_overlay(self):
        """Test overlay configuration in var_specs."""
        editor = VarSpecEditor(available_variables=["var1", "var2"])
        editor.add_var("var1")
        editor.add_var("var2")

        # Set var2 as overlay on var1
        editor._var_widgets[1]["add_to"].value = "var1"
        editor._var_widgets[1]["add_second_axis"].value = True

        specs = editor.to_var_specs()
        assert len(specs) == 2
        assert specs[1]["add_to"] == "var1"
        assert specs[1]["add_second_axis"] is True

    def test_to_var_specs_thresholds(self):
        """Test threshold configuration in var_specs."""
        editor = VarSpecEditor(available_variables=["var1"])
        editor.add_var("var1")

        editor._var_widgets[0]["lower_threshold_val"].value = 0.5
        editor._var_widgets[0]["lower_threshold_color"].value = "#00ff00"

        specs = editor.to_var_specs()
        assert len(specs) == 1
        assert specs[0]["lower_treshold"] == (0.5, "#00ff00")

    def test_create_var_spec_editor(self):
        """Test create_var_spec_editor helper function."""
        editor = create_var_spec_editor(["var1", "var2"])
        assert isinstance(editor, VarSpecEditor)
        assert editor.available_variables == ["var1", "var2"]
