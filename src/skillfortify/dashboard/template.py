"""HTML template for the SkillFortify dashboard report.

The template is a complete HTML5 document with placeholders for:
    ``{{CSS}}``  -- embedded stylesheet (from styles module).
    ``{{DATA}}`` -- JSON payload (from data_prep module).
    ``{{JS}}``   -- embedded script (from scripts module).

The file is self-contained: no external CDN, no server, no fetch calls.
"""

from __future__ import annotations

DASHBOARD_HTML: str = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{TITLE}}</title>
<style>
{{CSS}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>{{TITLE}}</h1>
    <div class="subtitle">Supply Chain Security Scanner for AI Agent Skills</div>
  </div>
  <div class="timestamp" id="scan-ts"></div>
</div>

<div class="container">

  <!-- Executive Summary -->
  <div id="stats-grid" class="stats-grid"></div>

  <!-- Risk Summary -->
  <div class="section">
    <div class="section-header">
      <h2>Risk Distribution</h2>
      <span class="toggle">&#9660;</span>
    </div>
    <div class="section-body">
      <div id="risk-bar" class="risk-bar"></div>
    </div>
  </div>

  <!-- Framework Coverage -->
  <div class="section">
    <div class="section-header">
      <h2>Framework Coverage</h2>
      <span class="toggle">&#9660;</span>
    </div>
    <div class="section-body">
      <div id="fw-chips" class="chip-grid"></div>
    </div>
  </div>

  <!-- Findings Table -->
  <div class="section">
    <div class="section-header">
      <h2>Findings</h2>
      <span class="toggle">&#9660;</span>
    </div>
    <div class="section-body">
      <div class="filters">
        <label for="filter-severity">Severity:</label>
        <select id="filter-severity"></select>
        <label for="filter-framework">Framework:</label>
        <select id="filter-framework"></select>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>Skill</th>
              <th>Format</th>
              <th>Severity</th>
              <th>Message</th>
              <th>Attack Class</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody id="findings-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Capabilities Matrix -->
  <div class="section">
    <div class="section-header">
      <h2>Capabilities Matrix</h2>
      <span class="toggle">&#9660;</span>
    </div>
    <div class="section-body">
      <div style="overflow-x:auto">
        <table class="cap-table">
          <thead>
            <tr>
              <th>Skill</th>
              <th>Filesystem</th>
              <th>Network</th>
              <th>Shell</th>
              <th>Environment</th>
              <th>Skill Invoke</th>
              <th>Clipboard</th>
              <th>Browser</th>
              <th>Database</th>
            </tr>
          </thead>
          <tbody id="cap-body"></tbody>
        </table>
      </div>
    </div>
  </div>

</div><!-- /container -->

<script>
window.__SKILLFORTIFY_DATA__={{DATA}};
</script>
<script>
{{JS}}
</script>
</body>
</html>"""
