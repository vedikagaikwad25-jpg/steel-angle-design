"""Regenerate the fully self-contained, offline interactive browser preview.

No CDN, Python server, data upload, or network access is needed at viewing time.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with (ROOT / 'data' / 'angles.csv').open(encoding='utf-8', newline='') as f:
    data = []
    for row in csv.DictReader(f):
        data.append({key: (float(value) if key in ('a_mm','b_mm','t_mm','gross_area_mm2') else value)
                     for key, value in row.items()})
js = (ROOT / 'tools' / 'preview_calculator.js').read_text(encoding='utf-8')
template = (ROOT / 'tools' / 'preview_template.html').read_text(encoding='utf-8')
html = template.replace('/*CATALOG_JSON*/', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
html = html.replace('/*CALCULATOR_ENGINE_JS*/', js)
(ROOT / 'preview.html').write_text(html, encoding='utf-8')
print(f'Generated offline interactive preview: {len(html):,} characters, {len(data)} catalog angles')
