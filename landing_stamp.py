#!/usr/bin/env python3
"""Stamp the content hash of landing/_landing/site.css into every landing page,
so browsers and Cloudflare fetch a fresh stylesheet whenever it changes."""
import glob, hashlib, os, re
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "landing")
h = hashlib.md5(open(os.path.join(root, "_landing/site.css"), "rb").read()).hexdigest()[:8]
for page in [os.path.join(root, "index.html")] + glob.glob(os.path.join(root, "*/index.html")):
    if "incoming" in page or not os.path.exists(page):
        continue
    s = open(page).read()
    n = re.sub(r"site\.css\?v=\w+", f"site.css?v={h}", s)
    if n != s:
        open(page, "w").write(n)
print("site.css", h)
