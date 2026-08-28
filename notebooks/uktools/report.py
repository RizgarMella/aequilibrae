"""uktools.report - unified one-page summaries.

summary_card renders headline figures and tables as ONE consistent HTML
card, so a model summary is not a mix of prints, Series and DataFrames each
formatted differently. Fully offline (inline CSS, no fonts, no images).
"""
import numpy as np
import pandas as pd
from IPython.display import HTML

_CARD = ("font-family:system-ui,Segoe UI,sans-serif;color:#111827;"
         "border:1px solid #d1d5db;border-radius:8px;padding:16px 20px;max-width:980px")
_H1 = "margin:0 0 12px 0;font-size:1.25rem"
_H2 = "margin:14px 0 6px 0;font-size:0.8rem;letter-spacing:.06em;text-transform:uppercase;color:#6b7280"
_GRID = "display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:4px 24px"
_ROW = "display:flex;justify-content:space-between;gap:12px;padding:2px 0;border-bottom:1px dotted #e5e7eb"
_LBL = "color:#374151"
_VAL = "font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap"
_TABLE = "border-collapse:collapse;width:100%;font-size:0.9rem"
_TH = "text-align:left;padding:4px 10px 4px 0;border-bottom:2px solid #d1d5db;color:#374151"
_TD = "padding:3px 10px 3px 0;border-bottom:1px solid #e5e7eb;font-variant-numeric:tabular-nums"
_BAR_BG = "background:#e5e7eb;border-radius:3px;height:10px;width:120px;display:inline-block;vertical-align:middle"
_BAR_FG = "background:#1d4ed8;border-radius:3px;height:10px;display:inline-block;vertical-align:middle"


def _fmt(v):
    if isinstance(v, (int, np.integer)):
        return f"{v:,}"
    if isinstance(v, (float, np.floating)):
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


def _table_html(df):
    cols = list(df.columns)
    has_share = "share" in cols
    head = "".join(f'<th style="{_TH}">{c}</th>' for c in cols if c != "share")
    if has_share:
        head += f'<th style="{_TH}">share</th>'
    rows = []
    for _, r in df.iterrows():
        tds = "".join(f'<td style="{_TD}">{_fmt(r[c])}</td>' for c in cols if c != "share")
        if has_share:
            pct = float(r["share"])
            tds += (f'<td style="{_TD}"><span style="{_BAR_BG}">'
                    f'<span style="{_BAR_FG};width:{max(2, pct / 100 * 120):.0f}px"></span></span>'
                    f' <span style="{_VAL}">{pct:.1f}%</span></td>')
        rows.append(f"<tr>{tds}</tr>")
    return f'<table style="{_TABLE}"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def summary_card(title, sections, tables=None, footnote=None):
    """One unified summary card.

    :param title:    heading
    :param sections: {section heading: {label: value}} - headline figures,
                     rendered as aligned label/value rows in a responsive grid
    :param tables:   optional {heading: DataFrame}; a numeric column named
                     "share" (percent) renders as a bar
    :param footnote: optional small-print line
    """
    parts = [f'<div style="{_CARD}">', f'<h2 style="{_H1}">{title}</h2>']
    parts.append(f'<div style="{_GRID}">')
    for heading, kv in sections.items():
        block = [f'<div><h3 style="{_H2}">{heading}</h3>']
        for label, value in kv.items():
            block.append(f'<div style="{_ROW}"><span style="{_LBL}">{label}</span>'
                         f'<span style="{_VAL}">{_fmt(value)}</span></div>')
        block.append("</div>")
        parts.append("".join(block))
    parts.append("</div>")
    for heading, df in (tables or {}).items():
        parts.append(f'<h3 style="{_H2}">{heading}</h3>')
        parts.append(_table_html(pd.DataFrame(df)))
    if footnote:
        parts.append(f'<p style="margin:10px 0 0 0;font-size:0.75rem;color:#6b7280">{footnote}</p>')
    parts.append("</div>")
    return HTML("".join(parts))
