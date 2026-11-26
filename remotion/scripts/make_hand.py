#!/usr/bin/env python3
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT = Path(__file__).resolve().parent.parent / "public" / "chalk_hand.png"
SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="280" viewBox="0 0 320 280">
<g stroke="#241f26" stroke-width="7" stroke-linejoin="round" stroke-linecap="round">
  <path d="M190 150 Q172 160 174 190 Q176 232 196 246 L300 246 Q312 246 312 224 L312 170 Q312 150 292 150 Z" fill="#2f6fb3"/>
  <path d="M180 156 L202 154 L198 242 L178 240 Q170 196 180 156 Z" fill="#255a92"/>
  <ellipse cx="150" cy="198" rx="62" ry="48" fill="#f0c49c"/>
  <path d="M104 224 Q126 258 160 246 Q186 238 196 212" fill="#f0c49c"/>
  <path d="M112 190 Q138 176 166 188" fill="none"/>
  <path d="M50 250 L138 212" stroke="#f7f4e6" stroke-width="24"/>
  <path d="M50 250 L38 255" stroke="#ffffff" stroke-width="22"/>
  <path d="M58 250 L92 236" fill="none" stroke="#d9d3c4" stroke-width="7"/>
  <path d="M118 218 Q136 206 154 214" fill="none" stroke="#e0ac84" stroke-width="9"/>
  <path d="M126 238 Q146 228 162 236" fill="none" stroke="#e0ac84" stroke-width="9"/>
</g>
</svg>'''
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 320, "height": 280}, device_scale_factor=2)
    pg.set_content("<style>html,body{margin:0;background:transparent}</style>" + SVG)
    pg.locator("svg").screenshot(path=str(OUT), omit_background=True)
    b.close()
print(OUT)
