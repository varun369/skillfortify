"""Main dashboard generator: assembles data, styles, and template into HTML.

The ``DashboardGenerator`` is the single public entry point. It takes
analysis results and parsed skills, prepares the JSON payload, and
renders a self-contained HTML report with embedded CSS and JavaScript.

Usage::

    from skillfortify.dashboard import DashboardGenerator

    gen = DashboardGenerator()
    html = gen.render(results, skills)
    Path("report.html").write_text(html, encoding="utf-8")
"""

from __future__ import annotations

import html as html_mod
from pathlib import Path

from skillfortify.core.analyzer.models import AnalysisResult
from skillfortify.dashboard.data_prep import encode_dashboard_json
from skillfortify.dashboard.scripts import DASHBOARD_JS
from skillfortify.dashboard.styles import DASHBOARD_CSS
from skillfortify.dashboard.template import DASHBOARD_HTML
from skillfortify.parsers.base import ParsedSkill


class DashboardGenerator:
    """Render a self-contained HTML dashboard from scan results.

    The generated HTML file embeds all CSS and JavaScript inline -- no
    external resources, no CDN dependencies, no server required. The
    file can be opened directly in any modern browser.

    The generator is stateless except for a configurable title. It is
    safe to reuse across multiple ``render()`` calls.

    Attributes:
        title: Report title shown in the header and ``<title>`` tag.
    """

    def __init__(self, title: str = "SkillFortify Security Report") -> None:
        self.title = title

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        results: list[AnalysisResult] | None = None,
        skills: list[ParsedSkill] | None = None,
    ) -> str:
        """Generate a self-contained HTML report string.

        Args:
            results: Analysis results (may be empty or None).
            skills: Parsed skills (may be empty or None).

        Returns:
            Complete HTML5 document as a string. Never raises.
        """
        safe_results = results if results is not None else []
        safe_skills = skills if skills is not None else []

        json_payload = encode_dashboard_json(safe_results, safe_skills)

        escaped_title = html_mod.escape(self.title)

        html = DASHBOARD_HTML
        html = html.replace("{{TITLE}}", escaped_title)
        html = html.replace("{{CSS}}", DASHBOARD_CSS)
        html = html.replace("{{DATA}}", json_payload)
        html = html.replace("{{JS}}", DASHBOARD_JS)

        return html

    def write(
        self,
        output_path: str | Path,
        results: list[AnalysisResult] | None = None,
        skills: list[ParsedSkill] | None = None,
    ) -> Path:
        """Render and write the HTML report to a file.

        Args:
            output_path: Destination file path (will be created or
                overwritten). Parent directories are created if needed.
            results: Analysis results (may be empty or None).
            skills: Parsed skills (may be empty or None).

        Returns:
            The resolved ``Path`` of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.render(results=results, skills=skills)
        path.write_text(content, encoding="utf-8")
        return path.resolve()
