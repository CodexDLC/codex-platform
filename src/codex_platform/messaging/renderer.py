"""Jinja2-based HTML template renderer and template-name resolver."""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False

DEFAULT_TEMPLATE_PREFIX_MAP = {
    "bk_": "booking",
    "ct_": "contacts",
    "mk_": "marketing",
    "acc_": "account",
}


def resolve_template_path(template_name: str, prefix_map: dict[str, str] | None = None) -> str:
    """Map a template key such as ``bk_confirmation`` to a template path."""

    if "/" in template_name or "\\" in template_name:
        return template_name
    if template_name.endswith(".html"):
        return template_name

    prefixes = DEFAULT_TEMPLATE_PREFIX_MAP if prefix_map is None else prefix_map
    for prefix, directory in prefixes.items():
        if template_name.startswith(prefix):
            return f"{directory}/{template_name}.html"
    return f"{template_name}.html"


class TemplateRenderer:
    """Jinja2 HTML template renderer."""

    def __init__(self, templates_dir: str) -> None:
        if not _JINJA2_AVAILABLE:
            raise RuntimeError(
                "jinja2 is not installed. "
                "Run: pip install codex-platform[notifications]\n"
                "If you are passing pre-rendered html_content to the worker, "
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
        """Render a template with the given context."""

        log.debug("TemplateRenderer | rendering template='%s'", template_name)
        template = self.env.get_template(template_name)
        return str(template.render(context))


__all__ = ["DEFAULT_TEMPLATE_PREFIX_MAP", "TemplateRenderer", "resolve_template_path"]
