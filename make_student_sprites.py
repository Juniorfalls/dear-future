#!/usr/bin/env python3
"""Three consistent back-view student sprites as transparent PNGs (vector webcomic)."""
import html, http.server, socketserver, threading, functools
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("math_engine/assets/characters")
OUT.mkdir(parents=True, exist_ok=True)
PORT = 8144
HAIRS = ["#2f231d", "#6b4a2f", "#1d1a1a"]
SHIRTS = ["#4a9d6e", "#d1604f", "#4f77c8"]
SKIN = "#f0c49c"


def svg(i: int) -> str:
    hair, shirt = HAIRS[i], SHIRTS[i]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="560" viewBox="0 0 460 560">
<g stroke="#211d24" stroke-width="7" stroke-linejoin="round" stroke-linecap="round">
  <path d="M150 545 L150 400 Q150 330 205 322 L255 322 Q310 330 310 400 L310 545 Z" fill="{shirt}"/>
  <path d="M205 322 Q230 350 255 322" fill="{SKIN}"/>
  <path d="M150 400 Q118 420 112 470 L118 512 Q122 528 136 524 Q148 520 144 504 L150 470" fill="{shirt}"/>
  <path d="M310 400 Q342 420 348 470 L342 512 Q338 528 324 524 Q312 520 316 504 L310 470" fill="{shirt}"/>
  <ellipse cx="230" cy="190" rx="86" ry="96" fill="{SKIN}"/>
  <path d="M142 184 Q140 74 230 72 Q320 74 318 184 Q300 132 256 124 Q216 118 186 142 Q160 160 142 184 Z" fill="{hair}"/>
  <path d="M142 176 Q136 210 146 236" fill="none"/>
  <path d="M318 176 Q324 210 314 236" fill="none"/>
  <path d="M168 276 Q230 310 292 276" fill="none" opacity=".18"/>
</g>
</svg>'''


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def main():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), functools.partial(Q, directory="."))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 600, "height": 700}, device_scale_factor=2)
        for i in range(3):
            page.set_content("<style>html,body{margin:0;background:transparent}</style>" + svg(i))
            page.locator("svg").screenshot(path=str(OUT / f"student_{i+1}.png"), omit_background=True)
            print("student", i + 1)
        b.close()
    httpd.shutdown()

if __name__ == "__main__":
    main()
