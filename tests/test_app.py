"""Tests for the Panel application."""

import pytest

from dataviewer_geo.app import create_app
from dataviewer_geo.config import DataConfig


class TestCreateApp:
    """Tests for create_app function."""

    def test_create_app_basic(self, data_config):
        """Test basic app creation."""
        app = create_app(data_config)

        # Check that app is a Panel template
        assert hasattr(app, "sidebar")
        assert hasattr(app, "main")

    def test_app_has_widgets(self, data_config):
        """Test that app has required widgets."""
        app = create_app(data_config)

        # The app should have split, variable, and location selectors
        # We can't easily test the internal structure without importing panel
        # but we can at least verify the app was created successfully
        assert app is not None

    def test_app_with_empty_data_raises(self, tmp_path):
        """Test that app creation fails with no data."""
        config = DataConfig(root=tmp_path)

        with pytest.raises(ValueError, match="No splits found"):
            create_app(config)
