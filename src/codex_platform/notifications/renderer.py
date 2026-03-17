"""
codex_platform.notifications.renderer
======================================
Jinja2-based HTML template renderer for notification workers.

OPTIONAL DEPENDENCY
-------------------
This module requires ``jinja2`` which is NOT included in the default
``codex-platform`` installation.

There are two delivery modes:

  Mode 1 — Worker renders templates itself (needs Jinja2):
      Worker receives ``template_name`` + ``context_data``,
      renders HTML internally, then sends via SMTP.

  Mode 2 — Pre-rendered HTML (no Jinja2 needed):
      Django (or any other layer) renders the template and passes
      ready ``html_content`` directly to the workers for delivery only.

If you are using Mode 1, add the following to your project dependencies:

    # pyproject.toml
    dependencies = [
        "jinja2>=3.1",
    ]

    # or via pip
    pip install jinja2

Usage
-----
    from codex_platform.notifications.renderer import TemplateRenderer

    renderer = TemplateRenderer(templates_dir="/path/to/workers/templates")
    html = renderer.render("booking/bk_confirmation.html", context={...})

Template directory structure (recommended)
------------------------------------------
    templates/
    ├── base_email.html
    ├── booking/
    │   ├── bk_confirmation.html
    │   └── bk_cancellation.html
    ├── contacts/
    │   └── ct_receipt.html
    └── marketing/
        └── mk_reengagement.html
"""

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False


class TemplateRenderer:
    """
    Jinja2 HTML template renderer.

    Requires ``jinja2`` — install via ``pip install codex-platform[jinja2]``.

    Raises:
        RuntimeError: If jinja2 is not installed.
        FileNotFoundError: If the templates directory does not exist.
    """

    def __init__(self, templates_dir: str) -> None:
        if not _JINJA2_AVAILABLE:
            raise RuntimeError(
                "jinja2 is not installed. "
                "Run: pip install codex-platform[jinja2]\n"
                "If you are passing pre-rendered html_content to the workers, "
                "you do not need TemplateRenderer at all."
            )

        if not os.path.exists(templates_dir):
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.templates_dir = templates_dir
        log.info("TemplateRenderer | initialized with dir='%s'", templates_dir)

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Relative path to template (e.g. 'booking/bk_confirmation.html').
            context: Dictionary of variables passed to the template.

        Returns:
            Rendered HTML string.

        Raises:
            jinja2.TemplateNotFound: If the template file does not exist.
            jinja2.TemplateError: On rendering errors.
        """
        log.debug("TemplateRenderer | rendering template='%s'", template_name)
        template = self.env.get_template(template_name)
        return str(template.render(context))
