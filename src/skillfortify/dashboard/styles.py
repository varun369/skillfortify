"""Embedded CSS styles for the SkillFortify HTML dashboard report.

All styles are self-contained -- no external stylesheets or CDN references.
The design uses CSS Grid and Flexbox for responsive layout.

Color scheme:
    - Dark header:  #1a1a2e
    - Card bg:      #ffffff
    - Critical:     #dc2626
    - High:         #ea580c
    - Medium:       #ca8a04
    - Low:          #16a34a
    - Safe:         #059669
"""

from __future__ import annotations

DASHBOARD_CSS: str = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,
  Oxygen,Ubuntu,sans-serif;background:#f1f5f9;color:#1e293b;line-height:1.6}
.header{background:#1a1a2e;color:#fff;padding:24px 32px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap}
.header h1{font-size:1.5rem;font-weight:700;letter-spacing:-0.02em}
.header .subtitle{font-size:0.85rem;color:#94a3b8;margin-top:2px}
.header .timestamp{font-size:0.8rem;color:#64748b}
.container{max-width:1280px;margin:0 auto;padding:24px 16px}

/* --- Stat cards --- */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:16px;margin-bottom:28px}
.stat-card{background:#fff;border-radius:10px;padding:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.08);text-align:center;
  border-top:3px solid #e2e8f0;transition:transform .15s}
.stat-card:hover{transform:translateY(-2px)}
.stat-card .value{font-size:2rem;font-weight:800;line-height:1.1}
.stat-card .label{font-size:0.82rem;color:#64748b;margin-top:4px;
  text-transform:uppercase;letter-spacing:0.04em}
.stat-card.critical{border-top-color:#dc2626}
.stat-card.critical .value{color:#dc2626}
.stat-card.high{border-top-color:#ea580c}
.stat-card.high .value{color:#ea580c}
.stat-card.medium{border-top-color:#ca8a04}
.stat-card.medium .value{color:#ca8a04}
.stat-card.low{border-top-color:#16a34a}
.stat-card.low .value{color:#16a34a}
.stat-card.safe{border-top-color:#059669}
.stat-card.safe .value{color:#059669}
.stat-card.total{border-top-color:#3b82f6}
.stat-card.total .value{color:#3b82f6}

/* --- Sections --- */
.section{background:#fff;border-radius:10px;padding:0;margin-bottom:24px;
  box-shadow:0 1px 3px rgba(0,0,0,.08);overflow:hidden}
.section-header{display:flex;align-items:center;justify-content:space-between;
  padding:16px 24px;cursor:pointer;user-select:none;background:#f8fafc;
  border-bottom:1px solid #e2e8f0}
.section-header h2{font-size:1.1rem;font-weight:600}
.section-header .toggle{font-size:1.2rem;color:#94a3b8;transition:transform .2s}
.section-header.collapsed .toggle{transform:rotate(-90deg)}
.section-body{padding:20px 24px}
.section-body.hidden{display:none}

/* --- Severity badges --- */
.badge{display:inline-block;padding:2px 10px;border-radius:9999px;
  font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.03em}
.badge-CRITICAL{background:#fef2f2;color:#dc2626;border:1px solid #fecaca}
.badge-HIGH{background:#fff7ed;color:#ea580c;border:1px solid #fed7aa}
.badge-MEDIUM{background:#fefce8;color:#ca8a04;border:1px solid #fde68a}
.badge-LOW{background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0}

/* --- Tables --- */
table{width:100%;border-collapse:collapse;font-size:0.88rem}
thead th{text-align:left;padding:10px 12px;background:#f8fafc;
  border-bottom:2px solid #e2e8f0;font-weight:600;color:#475569;
  white-space:nowrap}
tbody td{padding:10px 12px;border-bottom:1px solid #f1f5f9;
  vertical-align:top;word-break:break-word}
tbody tr:hover{background:#f8fafc}
.evidence-cell{max-width:260px;font-family:'SF Mono',SFMono-Regular,
  Menlo,Consolas,monospace;font-size:0.78rem;color:#64748b}

/* --- Filters --- */
.filters{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;
  align-items:center}
.filters label{font-size:0.82rem;font-weight:500;color:#475569}
.filters select{padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;
  font-size:0.82rem;background:#fff;color:#334155}

/* --- Framework chips --- */
.chip-grid{display:flex;flex-wrap:wrap;gap:10px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;
  border-radius:8px;background:#f1f5f9;font-size:0.84rem;font-weight:500;
  color:#334155;border:1px solid #e2e8f0}
.chip .count{background:#3b82f6;color:#fff;border-radius:9999px;
  padding:1px 8px;font-size:0.75rem;font-weight:700}
.chip.detected{background:#eff6ff;border-color:#93c5fd}

/* --- Capability matrix --- */
.cap-table td.READ{background:#dbeafe;color:#1d4ed8;text-align:center;
  font-weight:600;font-size:0.78rem}
.cap-table td.WRITE{background:#fef3c7;color:#92400e;text-align:center;
  font-weight:600;font-size:0.78rem}
.cap-table td.EXECUTE,.cap-table td.ADMIN{background:#fee2e2;color:#991b1b;
  text-align:center;font-weight:600;font-size:0.78rem}
.cap-table td.NONE{color:#cbd5e1;text-align:center;font-size:0.78rem}

/* --- Risk bar --- */
.risk-bar{display:flex;height:28px;border-radius:6px;overflow:hidden;
  margin-bottom:12px}
.risk-bar .segment{display:flex;align-items:center;justify-content:center;
  font-size:0.72rem;font-weight:700;color:#fff;min-width:2px}
.risk-bar .seg-critical{background:#dc2626}
.risk-bar .seg-high{background:#ea580c}
.risk-bar .seg-medium{background:#ca8a04}
.risk-bar .seg-low{background:#16a34a}

/* --- Print --- */
@media print{
  .header{background:#1a1a2e !important;-webkit-print-color-adjust:exact;
    print-color-adjust:exact}
  .section-header{cursor:default}
  .section-body.hidden{display:block !important}
  .filters{display:none}
  body{background:#fff}
}

/* --- Responsive --- */
@media(max-width:640px){
  .header{padding:16px;flex-direction:column;align-items:flex-start}
  .stats-grid{grid-template-columns:repeat(2,1fr)}
  .container{padding:12px 8px}
  .section-body{padding:12px}
  table{font-size:0.8rem}
  thead th,tbody td{padding:8px 6px}
}

.empty-state{text-align:center;padding:40px 20px;color:#94a3b8}
.empty-state .icon{font-size:2.5rem;margin-bottom:8px}
.empty-state p{font-size:0.95rem}
"""
