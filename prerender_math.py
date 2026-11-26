#!/usr/bin/env python3
"""Rasterise an episode's KaTeX equations to transparent PNGs for the board."""
import functools, http.server, json, socketserver, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PORT = 8139

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def main():
    ep = json.loads((ROOT / "math_engine/assets/episode.json").read_text())
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    dims = {}
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_page(viewport={"width": 2000, "height": 1200}, device_scale_factor=2)
        for eq in ep["equations"]:
            tex = eq["latex"]
            page.goto(f"http://127.0.0.1:{PORT}/math_engine/katex.html?tex={__import__('urllib.parse', fromlist=['quote']).quote(tex)}")
            page.wait_for_function("window.READY === true", timeout=60000)
            el = page.query_selector("#math")
            box = el.bounding_box()
            out = ROOT / f"math_engine/assets/eq_{eq.get('id','1')}.png"
            el.screenshot(path=str(out), omit_background=True)
            dims[eq.get("id", "1")] = {"w": box["width"], "h": box["height"]}
            print("eq", eq.get("id"), box["width"], "x", box["height"])
        b.close()
    httpd.shutdown()
    (ROOT / "math_engine/assets/eq_manifest.json").write_text(json.dumps(dims, indent=1))

if __name__ == "__main__":
    main()
