"""Tests for codex_platform.notifications.renderer."""


import pytest

try:
    from codex_platform.notifications.renderer import TemplateRenderer

    SKIP = False
except RuntimeError:
    SKIP = True
except ImportError:
    SKIP = True

pytestmark = [pytest.mark.unit, pytest.mark.skipif(SKIP, reason="jinja2 not installed")]


class TestTemplateRenderer:
    def test_render_basic_template(self, tmp_path):
        template_file = tmp_path / "hello.html"
        template_file.write_text("<h1>Hello, {{ name }}!</h1>")

        renderer = TemplateRenderer(str(tmp_path))
        result = renderer.render("hello.html", {"name": "World"})

        assert result == "<h1>Hello, World!</h1>"

    def test_render_with_complex_context(self, tmp_path):
        template_file = tmp_path / "booking.html"
        template_file.write_text(
            "<p>Booking #{{ booking_id }} for {{ customer }}</p>"
        )

        renderer = TemplateRenderer(str(tmp_path))
        result = renderer.render("booking.html", {"booking_id": 42, "customer": "Alice"})

        assert "Booking #42" in result
        assert "Alice" in result

    def test_render_autoescape_html(self, tmp_path):
        template_file = tmp_path / "escape.html"
        template_file.write_text("<p>{{ content }}</p>")

        renderer = TemplateRenderer(str(tmp_path))
        result = renderer.render("escape.html", {"content": "<script>alert(1)</script>"})

        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_init_raises_for_missing_dir(self):
        with pytest.raises(FileNotFoundError):
            TemplateRenderer("/nonexistent/path/that/does/not/exist")

    def test_render_subdirectory_template(self, tmp_path):
        sub = tmp_path / "booking"
        sub.mkdir()
        (sub / "confirm.html").write_text("<p>Confirmed: {{ id }}</p>")

        renderer = TemplateRenderer(str(tmp_path))
        result = renderer.render("booking/confirm.html", {"id": "BK-001"})

        assert "Confirmed: BK-001" in result

    def test_render_missing_template_raises(self, tmp_path):
        renderer = TemplateRenderer(str(tmp_path))
        from jinja2 import TemplateNotFound
        with pytest.raises(TemplateNotFound):
            renderer.render("nonexistent.html", {})
