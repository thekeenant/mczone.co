"""Build site-v0/, the TerraScape website (terrascapemc.weebly.com, 2011-2012).

Unlike the MC Zone editions, this site was never captured by the Wayback
Machine but was still live on Weebly in 2026, so raw/v0/ holds a wget mirror
of the live pages (see README). This copies it to site-v0/ as plain static
files: query strings come off asset filenames, Weebly's scripts and modern
footer are dropped, and links that pointed to the old Weebly host are made
local. Old personal email addresses are redacted.

Usage: python3 build_v0.py
"""
import os
import re
import shutil

from scrape import redact_emails

SRC = "raw/v0"
OUT = "site-v0"
NOT_FOUND = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Terrascape - Not archived</title>
</head>
<body style="font-family: sans-serif; max-width: 640px; margin: 60px auto; padding: 0 16px">
  <h1>Not archived</h1>
  <p>This page of the TerraScape website was not saved, so it is not part of this archive.</p>
  <p><a href="/">TerraScape home</a> &middot; <a href="https://mczone.co/">About this archive</a></p>
</body>
</html>
"""
PAGES = ["index", "guides", "online-shop", "donate", "plugins", "gallery", "contact"]

# "main_style.css?1380295471.css" and "main_style.css%3F1380295471.css" are
# both "main_style.css" once copied.
QUERY_RE = re.compile(r"(\.(?:css|js|png|gif|jpe?g|woff2?|ttf|eot|svg))(?:%3F|\?)[^\"')\s]*")


def clean_name(name):
    return name.split("?", 1)[0]


def clean_html(html):
    html = QUERY_RE.sub(r"\1", html)
    html = re.sub(r"(?s)<script\b.*?</script>", "", html)
    html = re.sub(r"(?s)<noscript\b.*?</noscript>", "", html)
    # Old personal addresses, hidden by Cloudflare; redacted like scrape.py does.
    html = re.sub(r'<a[^>]*class="__cf_email__"[^>]*>.*?</a>', "[email removed]", html)
    html = redact_emails(html.encode()).decode()
    # Weebly's present-day "Powered by / Create your own website" footer.
    html = re.sub(r'(?s)<div id="weebly-footer-signup-container-v3">.*?</a>\s*</div>', "", html)
    html = re.sub(r"(['\"])https?://terrascapemc\.weebly\.com/\1", r"\1./\1", html)
    html = re.sub(r"https?://terrascapemc\.weebly\.com/", "", html)
    # minestatus.net now serves its own ad in place of the old server banner.
    html = re.sub(r"(?s)<a[^>]*minestatus\.net/18828-terrascape-city-survival-server[^>]*>\s*<img[^>]*>\s*</a>", "", html)
    # News redirects to the home page today; nothing of it survives.
    html = re.sub(r"<li id='pg\d+'><a href='news\.html'>News</a></li>", "", html)
    return html


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for root, _, files in os.walk(SRC):
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(src, SRC)
            if rel.startswith(("cdn-cgi", "18828-")):
                continue
            dst = os.path.join(OUT, os.path.dirname(rel), clean_name(f))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if f.endswith(".html") and os.path.splitext(f)[0] in PAGES:
                with open(src, encoding="utf-8") as fh:
                    html = clean_html(fh.read())
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(html)
            elif clean_name(f).endswith(".css"):
                with open(src, encoding="utf-8", errors="surrogateescape") as fh:
                    css = QUERY_RE.sub(r"\1", fh.read())
                with open(dst, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(css)
            elif not os.path.exists(dst):
                shutil.copyfile(src, dst)
    os.makedirs(os.path.join(OUT, "_mirror"))
    with open(os.path.join(OUT, "_mirror", "404.html"), "w") as fh:
        fh.write(NOT_FOUND)
    # Caddy imports a routes file per edition; TerraScape needs no redirects.
    with open("routes-v0.caddy", "w") as fh:
        fh.write("# TerraScape (v0) has no redirects; see build_v0.py.\n")
    print(f"built {OUT}/")


if __name__ == "__main__":
    main()
