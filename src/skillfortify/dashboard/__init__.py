"""HTML Dashboard Report Generator for SkillFortify scan results.

Produces a single self-contained HTML file with embedded CSS and JavaScript
for visualizing supply chain security scan results across 22 AI agent
frameworks. No external dependencies -- everything is inline.

Submodules:
    data_prep  -- Transforms AnalysisResult/ParsedSkill into JSON-safe dicts.
    template   -- HTML structure with placeholder markers.
    styles     -- Embedded CSS stylesheet.
    scripts    -- Embedded JavaScript for interactivity.
    generator  -- Orchestrates data preparation and template rendering.

Usage::

    from skillfortify.dashboard import DashboardGenerator

    gen = DashboardGenerator()
    html = gen.render(results, skills)
    Path("report.html").write_text(html)
"""

from skillfortify.dashboard.generator import DashboardGenerator

__all__ = [
    "DashboardGenerator",
]
