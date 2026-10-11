#!/usr/bin/env python3
"""Mirror the MC Zone site (mczone.co, 2012-2013) from the Wayback Machine as static files.

  scrape.py fetch     [edition]  download the newest capture of every archived URL in the edition's window
  scrape.py ext       [edition]  download assets the pages use: off-site ones, and on-site ones
                                 missing from the window (nearest capture from any date)
  scrape.py fill                 download stock library files the archive never captured into fill/
  scrape.py redirects [edition]  record where archived 301/302 responses pointed
  scrape.py avatars              download archived minotar/cravatar heads used by any edition into avatars/
  scrape.py build     [edition]  write a servable static tree into site-<edition>/ plus Caddy routes

Editions are the site's successive designs (see EDITIONS); the default is main.

Captures are fetched with the `id_` flag, so bytes are exactly what the
original server sent, with no Wayback toolbar or link rewriting. The site's
own links are left as they were; query-string urls are routed by Caddy using
the generated routes.caddy.
"""
import concurrent.futures as cf
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import struct
import sys
import time
import urllib.parse as up
import zlib

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")
CDX_FILES = ["cdx.json", "cdx_shop.json"]
# Hosts we mirror, and the path prefix each one is served under.
HOST_PREFIX = {"mczone.co": "", "www.mczone.co": "", "shop.mczone.co": "/shop"}
HOSTS = set(HOST_PREFIX)
# Avatar services are referenced ~33k times; leave them as live links.
LIVE_HOSTS = {"minotar.net", "cravatar.eu"}
# Each edition is one design of the site, mirrored from captures in
# [start, end). In early November 2013 the site was rebranded to the Avicus
# Network, which ends the main edition.
EDITIONS = {
    "v1": ("20121101", "20121110"),    # blue Bootstrap "Welcome, MC gamers!"
    "v2": ("20121110", "20130401"),    # dark theme, script logo, planet banner
    "v3": ("20130401", "20130701"),    # "Minecraft Zone", the PHP code in mczone-web
    "main": ("20130701", "20131108"),  # Rails rewrite, forums and stats
}
EDITION = sys.argv[2] if len(sys.argv) > 2 else "main"
ERA_START, CUTOFF = EDITIONS[EDITION]
SUFFIX = "" if EDITION == "main" else "-" + EDITION
SITE = os.path.join(ROOT, "site" + SUFFIX)
MANIFEST = os.path.join(ROOT, f"manifest{SUFFIX}.json")
ROUTES = os.path.join(ROOT, f"routes{SUFFIX}.caddy")
MISSING = os.path.join(ROOT, f"missing{SUFFIX}.txt")
NOT_MCZONE_TITLE = re.compile(rb"<title>\s*Avicus", re.I)

session = requests.Session()
session.headers["User-Agent"] = "mczone-archive-mirror (personal archival; contact keenan)"


def url_key(url):
    p = up.urlsplit(url)
    path = up.unquote(p.path) or "/"
    prefix = HOST_PREFIX.get(p.hostname or "", "")
    return prefix + path + ("?" + p.query if p.query else "")


def raw_name(key, ts):
    return ts + "_" + hashlib.sha1(key.encode()).hexdigest()[:16]


def wayback_get(ts, url):
    """Fetch one raw capture, backing off when the archive throttles us."""
    for attempt in range(8):
        try:
            r = session.get(f"https://web.archive.org/web/{ts}id_/{url}", timeout=90)
        except requests.RequestException:
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code in (429, 503, 504) or b"Temporarily Offline" in r.content[:2000]:
            time.sleep(15 * (attempt + 1))
            continue
        return r
    return None


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {"pages": {}, "ext": {}}


def save_manifest(m):
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    os.replace(tmp, MANIFEST)


def cdx_rows():
    for name in CDX_FILES:
        with open(os.path.join(ROOT, name)) as f:
            yield from json.load(f)[1:]


def in_era(ts):
    return ERA_START <= ts < CUTOFF


def is_mczone(info):
    return not NOT_MCZONE_TITLE.search(read_raw(info)[:5000])


def download_all(jobs, table, m):
    """jobs: list of (key, ts, url). Results land in table[key]."""
    os.makedirs(RAW, exist_ok=True)

    def one(job):
        key, ts, url = job
        r = wayback_get(ts, url)
        if r is None:
            return key, None
        # Wayback redirects to the nearest capture when the exact one is gone.
        m_ts = re.search(r"/web/(\d{14})", r.url)
        got_ts = m_ts.group(1) if m_ts else ts
        name = raw_name(key, got_ts)
        with open(os.path.join(RAW, name), "wb") as f:
            f.write(r.content)
        return key, {
            "ts": got_ts,
            "url": url,
            "status": r.status_code,
            "type": r.headers.get("content-type", "").split(";")[0].strip(),
            "raw": name,
        }

    done = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for key, info in ex.map(one, jobs):
            done += 1
            if info:
                table[key] = info
            else:
                print("FAILED", key, file=sys.stderr)
            if done % 25 == 0:
                save_manifest(m)
                print(f"{done}/{len(jobs)}", flush=True)
    save_manifest(m)


def cmd_fetch():
    captures = {}
    for ts, url, _mime, status, _len in cdx_rows():
        if status == "200" and in_era(ts):
            captures.setdefault(url_key(url), []).append((ts, url))
    m = load_manifest()
    rejected = m.setdefault("rejected", {})
    while True:
        jobs = []
        for key, caps in sorted(captures.items()):
            have = m["pages"].get(key)
            if have and have.get("nearest"):
                continue
            if have and have["status"] == 200 and in_era(have["ts"]) and have["ts"] not in rejected.get(key, []):
                continue
            # newest capture that is in range and not known to be Avicus-branded
            for ts, url in sorted(caps, reverse=True):
                if ts not in rejected.get(key, []):
                    jobs.append((key, ts, url))
                    break
            else:
                m["pages"].pop(key, None)
        print(f"{len(captures)} urls, {len(jobs)} to fetch")
        if not jobs:
            save_manifest(m)
            break
        download_all(jobs, m["pages"], m)
        # A capture can be served from a nearby date; reject Avicus pages and retry older ones.
        for key, _ts, _url in jobs:
            info = m["pages"].get(key)
            if info and info["status"] == 200 and (not in_era(info["ts"]) or not is_mczone(info)):
                rejected.setdefault(key, []).append(info["ts"])
                rejected[key].append(_ts)
        save_manifest(m)


# --- link discovery and rewriting -------------------------------------------

ATTR_RE = re.compile(r"""(\b(?:href|src|action|data-src|background)\s*=\s*)(["'])(.*?)\2""", re.I | re.S)
CSS_URL_RE = re.compile(r"""url\(\s*(["']?)([^"')]+?)\1\s*\)""", re.I)
CSS_IMPORT_RE = re.compile(r"""@import\s+(["'])(.+?)\1""", re.I)


def is_text(info):
    t = info["type"]
    return t.startswith("text/") or "javascript" in t or t in ("application/json", "image/svg+xml")


def is_html(info):
    return info["type"] in ("text/html", "application/xhtml+xml")


def read_raw(info):
    with open(os.path.join(RAW, info["raw"]), "rb") as f:
        return f.read()


def asset_refs(info, base_url):
    """Absolute URLs of things a page or stylesheet loads (not plain links)."""
    text = read_raw(info).decode("utf-8", "replace")
    out = set()
    if is_html(info):
        for m in re.finditer(r"<(img|script|link|input|embed|source|video|iframe)\b[^>]*>", text, re.I):
            tag = m.group(0)
            if m.group(1).lower() == "link" and not re.search(r"""rel\s*=\s*["']?(stylesheet|icon|shortcut icon|apple-touch-icon)""", tag, re.I):
                continue
            for a in ATTR_RE.finditer(tag):
                out.add(up.urljoin(base_url, html.unescape(a.group(3).strip())))
        for s in re.findall(r"<style[^>]*>(.*?)</style>", text, re.I | re.S) + re.findall(r"""style\s*=\s*["']([^"']*)""", text, re.I):
            out |= {up.urljoin(base_url, u[1]) for u in CSS_URL_RE.findall(s)}
    elif info["type"] == "text/css":
        out |= {up.urljoin(base_url, u[1]) for u in CSS_URL_RE.findall(text)}
        out |= {up.urljoin(base_url, u[1]) for u in CSS_IMPORT_RE.findall(text)}
    return {u.split("#")[0] for u in out if u.startswith("http")}


def site_pages(m):
    return {k: v for k, v in m["pages"].items()
            if v["status"] == 200 and (in_era(v["ts"]) or v.get("nearest"))}


def external(u):
    host = up.urlsplit(u).hostname or ""
    return not (host in HOSTS or host in LIVE_HOSTS or host.endswith("archive.org"))


def cmd_ext():
    """Fetch off-site assets (fonts, CDN scripts, images) the pages depended on."""
    m = load_manifest()
    for _round in range(2):  # second round picks up urls inside fetched css
        wanted = {}
        for table in (site_pages(m), m["ext"]):
            for key, info in table.items():
                if info["status"] != 200:
                    continue
                for u in asset_refs(info, info["url"]):
                    if external(u) and (u not in m["ext"] or m["ext"][u]["status"] != 200):
                        wanted[u] = info["ts"]
        jobs = [(u, ts, u) for u, ts in sorted(wanted.items())]
        print(f"{len(jobs)} external assets to fetch")
        download_all(jobs, m["ext"], m)
    fetch_nearest_assets(m)


def fetch_nearest_assets(m):
    """On-site assets the pages load but that have no capture in the window:
    use the capture closest in time to the page, like the Wayback Machine does."""
    captures = {}
    for ts, url, _mime, status, _len in cdx_rows():
        if status == "200":
            captures.setdefault(url_key(url), []).append((ts, url))
    for _round in range(2):  # css can pull in more assets
        pages = site_pages(m)
        wanted = {}
        for info in pages.values():
            for u in asset_refs(info, info["url"]):
                if (up.urlsplit(u).hostname or "") not in HOSTS:
                    continue
                key = url_key(u)
                if key in pages or key in wanted or key not in captures:
                    continue
                ts, url = min(captures[key], key=lambda c: abs(int(c[0]) - int(info["ts"])))
                wanted[key] = (ts, url)
        jobs = [(k, ts, url) for k, (ts, url) in sorted(wanted.items())]
        print(f"{len(jobs)} on-site assets from outside the window")
        if not jobs:
            break
        download_all(jobs, m["pages"], m)
        for key, _ts, _url in jobs:
            if key in m["pages"]:
                m["pages"][key]["nearest"] = True
        save_manifest(m)


def ext_for(info):
    t = info["type"]
    return {"text/html": ".html", "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
            "text/css": ".css", "application/javascript": ".js", "application/x-javascript": ".js",
            "text/javascript": ".js", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico",
            "text/plain": ".txt"}.get(t) or mimetypes.guess_extension(t) or ""


def safe(s):
    return re.sub(r"[^A-Za-z0-9._=-]+", "_", s).strip("_")[:150]


def local_path(key, info):
    """Where a captured URL lives in the static tree (url path, leading slash)."""
    path, _, query = key.partition("?")
    base, ext = os.path.splitext(path)
    if is_html(info):
        if query:
            stem = path.rstrip("/") or "/index"
            return f"{stem}__{safe(query)}.html"
        if path.endswith("/"):
            return path + "index.html"
        if ext in ("", ".php"):
            return (base if ext else path) + "/index.html"
        return path
    if query:
        # keep a real extension (fonts with ?v= are often served as text/plain)
        return f"{base}__{safe(query)}{ext or ext_for(info)}"
    if ext in ("", ".php"):
        return (base if ext else path) + ext_for(info)
    return path


# Unmodified third-party files the site shipped but the archive missed, taken
# from the same upstream releases (versions confirmed from the archived css/js).
CDN = "https://cdnjs.cloudflare.com/ajax/libs"
FILL = {
    "/img/glyphicons-halflings.png": f"{CDN}/twitter-bootstrap/2.3.2/img/glyphicons-halflings.png",
    "/img/glyphicons-halflings-white.png": f"{CDN}/twitter-bootstrap/2.3.2/img/glyphicons-halflings-white.png",
    **{f"/assets/{d}/fontawesome-webfont.{e}": f"{CDN}/font-awesome/3.2.1/font/fontawesome-webfont.{e}"
       for d in ("font", "fonts") for e in ("eot", "svg", "ttf", "woff")},
    **{f"/assets/datatables/{n}.png": f"{CDN}/datatables/1.9.4/images/{n}.png"
       for n in ("sort_asc", "sort_asc_disabled", "sort_both", "sort_desc", "sort_desc_disabled")},
    **{f"/assets/theme/fancybox/{n}": f"{CDN}/fancybox/2.1.4/{n}"
       for n in ("blank.gif", "fancybox_loading.gif", "fancybox_overlay.png", "fancybox_sprite.png")},
}
FILL_DIR = os.path.join(ROOT, "fill")
# Bump to force browsers and Cloudflare to refetch the site's css/js.
ASSET_VERSION = b"1"

# Small compatibility fixes appended to archived files. The game tiles are
# <img> tags with no src and a css background; modern Firefox/Safari treat
# those as inline and ignore their width/height, so the pictures vanish.
PATCHES = {
    "/assets/custom.css": "\n/* mczone mirror: keep src-less game images sized in modern browsers */\n"
                          ".game-image { display: inline-block; }\n",
}


def cmd_fill():
    for path, url in FILL.items():
        dest = os.path.join(FILL_DIR, path.lstrip("/"))
        if os.path.exists(dest):
            continue
        r = session.get(url, timeout=60)
        if r.status_code != 200:
            print("FAILED", path, url, r.status_code, file=sys.stderr)
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(r.content)


def cmd_redirects():
    """Resolve the archived 3xx captures for urls that have no 200 capture."""
    m = load_manifest()
    have = set(site_pages(m))
    latest = {}
    for ts, url, _mime, status, _len in cdx_rows():
        if status not in ("301", "302") or not in_era(ts):
            continue
        key = url_key(url)
        if key in have:
            continue
        if key not in latest or ts > latest[key][0]:
            latest[key] = (ts, url, status)
    redirects = m.setdefault("redirects", {})
    jobs = [(k, v) for k, v in sorted(latest.items()) if k not in redirects]
    print(f"{len(jobs)} redirects to resolve")

    def one(job):
        key, (ts, url, status) = job
        for attempt in range(6):
            try:
                r = session.head(f"https://web.archive.org/web/{ts}id_/{url}", timeout=60, allow_redirects=False)
            except requests.RequestException:
                time.sleep(10 * (attempt + 1))
                continue
            if r.status_code in (429, 503, 504):
                time.sleep(15 * (attempt + 1))
                continue
            loc = r.headers.get("location", "")
            mo = re.match(r"https?://web\.archive\.org/web/\d+(?:id_)?/(.*)", loc)
            target = mo.group(1) if mo else loc
            return key, {"status": int(status), "to": target, "ts": ts} if target and r.status_code in (301, 302) else None
        return key, None

    done = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for key, info in ex.map(one, jobs):
            done += 1
            if info:
                redirects[key] = info
            if done % 50 == 0:
                save_manifest(m)
                print(f"{done}/{len(jobs)}", flush=True)
    save_manifest(m)


NOT_FOUND_PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>MC Zone » Not archived</title>
  <link href="{css}" media="all" rel="stylesheet" type="text/css" />
</head>
<body>
  <div class="container" style="padding-top: 60px">
    <div class="page-header"><h1>Not archived</h1></div>
    <p>This page of MC Zone was never captured by the Wayback Machine for this version of the site, so it is not part of this mirror.</p>
    <p><a id="wayback" class="btn" href="https://web.archive.org/web/*/mczone.co">Look for other captures on the Wayback Machine</a>
       <a class="btn btn-primary" href="/">MC Zone home</a>
       <a class="btn" href="https://mczone.co/">About this archive</a></p>
  </div>
  <script>
    document.getElementById("wayback").href =
      "https://web.archive.org/web/*/mczone.co" + location.pathname + location.search;
  </script>
</body>
</html>
"""


# Injected into pages that link to unarchived pages: those links show a note
# on hover instead of navigating. Typing such a url still shows the 404 page.
MIRROR_HEAD = '<script src="/_mirror/mirror.js" defer></script>'
MIRROR_JS = """(function () {
  var tip = document.createElement("div");
  tip.textContent = "Sorry, this link is broken. It's not part of the archive.";
  tip.style.cssText = "position:fixed;z-index:100000;display:none;pointer-events:none;" +
    "background:#222;color:#fff;font:12px/1.4 Helvetica,Arial,sans-serif;padding:5px 9px;" +
    "border-radius:4px;box-shadow:0 2px 6px rgba(0,0,0,.3);white-space:nowrap";
  var css = document.createElement("style");
  css.textContent = "a[data-mz-missing]{cursor:not-allowed}";
  document.head.appendChild(css);
  document.body.appendChild(tip);
  function missing(el) { return el && el.closest && el.closest("a[data-mz-missing]"); }
  document.addEventListener("mousemove", function (e) {
    if (missing(e.target)) {
      tip.style.display = "block";
      tip.style.left = Math.min(e.clientX + 12, window.innerWidth - tip.offsetWidth - 8) + "px";
      tip.style.top = (e.clientY + 16) + "px";
    } else {
      tip.style.display = "none";
    }
  });
  document.addEventListener("click", function (e) {
    if (missing(e.target)) { e.preventDefault(); e.stopPropagation(); }
  }, true);
})();
"""


# --- archived player heads --------------------------------------------------

AVATARS = os.path.join(ROOT, "avatars")
AVATAR_CDX = ["cdx_av_minotar.txt", "cdx_av_cravatar.txt"]
AVATAR_RE = re.compile(r"(minotar\.net)/helm/([^/]+)/(\d+)(?:\.png)?$|(cravatar\.eu)/helmavatar/([^/]+)/(\d+)(?:\.png)?$", re.I)
AVATAR_TARGET_TS = 20130901000000  # prefer heads captured closest to the site's heyday


def avatar_parse(url):
    """(host, user, size) for a minotar/cravatar head url, else None."""
    p = up.urlsplit(url if "//" in url else "//" + url)
    mo = AVATAR_RE.search((p.hostname or "") + p.path)
    if not mo:
        return None
    if mo.group(1):
        return "minotar.net", mo.group(2), int(mo.group(3))
    return "cravatar.eu", mo.group(5), int(mo.group(6))


def avatar_file(url):
    """Path under avatars/ (and /_avatars/ on the site) for a head url."""
    host, user, size = avatar_parse(url)
    # Minecraft names are [A-Za-z0-9_]; keep them exact (safe() strips "_").
    name = user if re.fullmatch(r"\w+", user) else safe(user)
    return f"{host}/{name}/{size}.png"


def cmd_avatars():
    """Pick, download and (if needed) resize an archived head for every avatar
    any edition shows. Heads never archived for that player stay live links."""
    archived, by_user = {}, {}
    for name in AVATAR_CDX:
        for line in open(os.path.join(ROOT, name)):
            parts = line.split()
            if len(parts) < 3 or not parts[2].startswith("image/"):
                continue
            ts, url = parts[0], parts[1]
            a = avatar_parse(url)
            if not a:
                continue
            archived.setdefault(a, []).append((ts, url))
            by_user.setdefault(a[1].lower(), []).append((a[2], ts, url))
    wanted = set()
    for ed, (start, end) in EDITIONS.items():
        path = os.path.join(ROOT, "manifest.json" if ed == "main" else f"manifest-{ed}.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            em = json.load(f)
        for info in em["pages"].values():
            if info["status"] == 200 and is_html(info) and (start <= info["ts"] < end or info.get("nearest")):
                for u in asset_refs(info, info["url"]):
                    a = avatar_parse(u)
                    if a:
                        wanted.add(a)
    near = lambda ts: abs(int(ts) - AVATAR_TARGET_TS)
    plan = {}
    for a in wanted:
        # Candidates in order of preference: this exact url closest to the
        # site's heyday, then the same player at other sizes (bigger first).
        # Minotar sometimes served blank heads, so later ones are fallbacks.
        exact = [(ts, url, False) for ts, url in sorted(archived.get(a, []), key=lambda c: near(c[0]))]
        # Any size that is a multiple of 8 holds the 8x8 head exactly, so
        # prefer the smallest of those (fastest to decode), nearest in time.
        other = [(ts, url, True) for size, ts, url in
                 sorted(by_user.get(a[1].lower(), []), key=lambda c: (c[0] % 8 != 0, c[0], near(c[1])))
                 if size != a[2] and size >= 8]
        if exact or other:
            plan[a] = exact + other
    print(f"{len(wanted)} heads used, {sum(bool(v[0][2] is False) for v in plan.values())} archived at this size, "
          f"{sum(v[0][2] for v in plan.values())} only at another size, {len(wanted) - len(plan)} left live")

    def one(item):
        (host, user, size), candidates = item
        dest = os.path.join(AVATARS, avatar_file(f"{host}/{'helm' if host == 'minotar.net' else 'helmavatar'}/{user}/{size}"))
        if os.path.exists(dest):
            return True
        for ts, url, resize in candidates[:8]:
            r = wayback_get(ts, url)
            if r is None or r.status_code != 200 or not r.content.startswith(b"\x89PNG"):
                continue
            if png_quick_blank(r.content):
                continue
            img = png_decode(r.content)
            if img is None or png_is_blank(img):
                continue
            data = png_resize_nearest(img, size) if resize else r.content
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            return True
        return False

    ok = done = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, sorted(plan.items())):
            done += 1
            ok += bool(res)
            if done % 250 == 0:
                print(f"{done}/{len(plan)}", flush=True)
    print(f"{ok} heads saved, {len(plan) - ok} failed")


def png_decode(data):
    """Decode a non-interlaced 8- or 16-bit PNG into unfiltered rows.
    Returns None for formats this small decoder does not handle."""
    pos, chunks = 8, []
    while pos < len(data):
        n, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunks.append((typ, data[pos + 8:pos + 8 + n]))
        pos += 12 + n
    w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if depth not in (8, 16) or interlace or not channels:
        return None
    raw = zlib.decompress(b"".join(c for t, c in chunks if t == b"IDAT"))
    bpp = channels * depth // 8
    stride = w * bpp
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(h):
        ftype, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b, c = prev[x], (prev[x - bpp] if x >= bpp else 0)
            if ftype == 1:
                line[x] = (line[x] + a) & 255
            elif ftype == 2:
                line[x] = (line[x] + b) & 255
            elif ftype == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif ftype == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return {"w": w, "h": h, "depth": depth, "ctype": ctype, "bpp": bpp, "rows": rows, "chunks": chunks}


def png_quick_blank(data):
    """Cheap check for Minotar's empty heads: a fully transparent image
    compresses to all-zero filtered rows, so no unfiltering is needed."""
    try:
        pos, idat, ihdr = 8, [], None
        while pos < len(data):
            n, typ = struct.unpack(">I4s", data[pos:pos + 8])
            if typ == b"IHDR":
                ihdr = struct.unpack(">IIBBBBB", data[pos + 8:pos + 21])
            elif typ == b"IDAT":
                idat.append(data[pos + 8:pos + 8 + n])
            pos += 12 + n
        w, h, depth, ctype = ihdr[:4]
        if ctype not in (4, 6):
            return False
        raw = zlib.decompress(b"".join(idat))
        stride = 1 + w * {4: 2, 6: 4}[ctype] * depth // 8
        return not any(raw[i + 1:i + stride].strip(b"\0") for i in range(0, len(raw), stride))
    except Exception:
        return False


def png_is_blank(img):
    """True for Minotar's empty heads: one flat colour, or fully transparent."""
    first = bytes(img["rows"][0][:img["bpp"]])
    if all(bytes(row) == first * img["w"] for row in img["rows"]):
        return True
    alpha = {4: 1, 6: 3}.get(img["ctype"])
    if alpha is None:
        return False
    sample = img["depth"] // 8
    off = alpha * sample
    return not any(any(row[x + off:x + off + sample]) for row in img["rows"]
                   for x in range(0, len(row), img["bpp"]))


def png_resize_nearest(img, size):
    """Scale a decoded PNG to size x size with nearest-neighbour sampling."""
    w, h, depth, ctype, bpp, rows, chunks = (img[k] for k in ("w", "h", "depth", "ctype", "bpp", "rows", "chunks"))
    out = bytearray()
    for y in range(size):
        src = rows[y * h // size]
        out.append(0)
        for x in range(size):
            sx = (x * w // size) * bpp
            out += src[sx:sx + bpp]

    def chunk(typ, body):
        return struct.pack(">I", len(body)) + typ + body + struct.pack(">I", zlib.crc32(typ + body) & 0xffffffff)

    keep = b"".join(chunk(t, c) for t, c in chunks if t in (b"PLTE", b"tRNS"))
    ihdr = struct.pack(">IIBBBBB", size, size, depth, ctype, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + keep + chunk(b"IDAT", zlib.compress(bytes(out), 9)) + chunk(b"IEND", b"")


def caddy_str(v):
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def cmd_build():
    m = load_manifest()
    pages = site_pages(m)
    local = {k: local_path(k, v) for k, v in pages.items()}

    # Off-site assets: only the ones the shipped pages (and their css) still use.
    ext_all = {k: v for k, v in m["ext"].items() if v["status"] == 200}
    used_ext, todo = set(), [v for v in pages.values()]
    while todo:
        info = todo.pop()
        for u in asset_refs(info, info["url"]):
            if u in ext_all and u not in used_ext:
                used_ext.add(u)
                todo.append(ext_all[u])
    ext = {u: ext_all[u] for u in used_ext}
    for u, v in ext.items():
        p = up.urlsplit(u)
        key = up.unquote(p.path) + ("?" + p.query if p.query else "")
        local[u] = f"/_ext/{p.hostname}" + local_path(key, v)

    def served_url(key):
        """The url a visitor uses for a key: original path and query, unchanged."""
        path, q, query = key.partition("?")
        return up.quote(path, safe="/@:+$,;=~!*'()-._") + q + query

    # Caddy routes. One map from the raw request uri to either a file to serve
    # or a redirect target. Paths that try_files {path} {path}/index.html would
    # already find are left out.
    routes = {}
    for key, lp in local.items():
        if key.startswith("http"):
            continue
        path = key.split("?")[0]
        if "?" in key or lp not in (path, path.rstrip("/") + "/index.html"):
            routes[served_url(key)] = ("file", lp)
    # A topic or listing whose first page was never captured: serve its
    # earliest captured ?page=N for the bare url.
    by_path = {}
    for key in pages:
        path, _, query = key.partition("?")
        mo = re.fullmatch(r"page=(\d+)", query)
        if mo and path not in pages:
            by_path.setdefault(path, []).append((int(mo.group(1)), key))
    for path, ps in by_path.items():
        routes.setdefault(served_url(path), ("file", local[min(ps)[1]]))
    nredir = 0
    for key, r in m.get("redirects", {}).items():
        if not in_era(r.get("ts", ERA_START)) or served_url(key) in routes:
            continue
        tp = up.urlsplit(r["to"])
        if (tp.hostname or "mczone.co") not in HOSTS:
            continue
        tkey = url_key(up.urljoin("http://mczone.co" + key, r["to"]))
        tkey = tkey.split("#")[0]
        if tkey == key or not (tkey in local or served_url(tkey) in routes or tkey.split("?")[0] in local):
            continue
        routes[served_url(key)] = ("redir" + str(r["status"]), served_url(tkey))
        nredir += 1

    def available(key):
        """Whether a visitor following a link to this key gets an archived page."""
        path = key.split("?")[0]
        if "?" in key:
            return key in local or served_url(key) in routes
        return any(k in local or served_url(k) in routes or k in FILL
                   for k in {path, path.rstrip("/") or "/", path.rstrip("/") + "/"})

    missing = {}
    used_avatars = set()

    def resolve(raw_url, base_url):
        """New value for a url in a page, or None to leave it exactly as written."""
        url = html.unescape(raw_url.strip())
        if not url or url.startswith(("#", "mailto:", "javascript:", "data:")):
            return None
        absu = up.urljoin(base_url, url)
        frag = ""
        if "#" in absu:
            absu, frag = absu.split("#", 1)
            frag = "#" + frag
        p = up.urlsplit(absu)
        if p.scheme not in ("http", "https"):
            return None
        host = p.hostname or ""
        base_host = up.urlsplit(base_url).hostname or ""
        if host in HOSTS:
            key = url_key(absu)
            if key not in local and key.split("?")[0] not in local and key.split("?")[0] not in FILL:
                missing[key] = missing.get(key, 0) + 1
            # Only links to or from a prefixed host (the shop) need rewriting.
            if HOST_PREFIX[host] or HOST_PREFIX.get(base_host):
                return served_url(key) + frag
            return None
        if absu in local:
            return local[absu] + frag
        if avatar_parse(absu) and os.path.exists(os.path.join(AVATARS, avatar_file(absu))):
            used_avatars.add(avatar_file(absu))
            return "/_avatars/" + avatar_file(absu)
        if host == "cravatar.eu":
            # cravatar.eu is gone; minotar serves the same heads by username.
            mo = re.match(r"/helmavatar/([^/]+)/(\d+)", p.path)
            if mo:
                return f"https://minotar.net/helm/{mo.group(1)}/{mo.group(2)}.png"
        return None

    def rewrite(text, info, base_url):
        def attr(mo):
            new = resolve(mo.group(3), base_url)
            if new is None:
                return mo.group(0)
            return mo.group(1) + mo.group(2) + html.escape(new, quote=False) + mo.group(2)

        def cssu(mo):
            new = resolve(mo.group(2), base_url)
            return mo.group(0) if new is None else f"url({mo.group(1)}{new}{mo.group(1)})"

        def anchor(mo):
            tag = mo.group(0)
            href = re.search(r"""\bhref\s*=\s*(["'])(.*?)\1""", tag, re.I | re.S)
            if not href:
                return tag
            url = up.urljoin(base_url, html.unescape(href.group(2).strip())).split("#")[0]
            p = up.urlsplit(url)
            if p.scheme not in ("http", "https") or (p.hostname or "") not in HOSTS or available(url_key(url)):
                return tag
            return tag[:2] + " data-mz-missing" + tag[2:]

        if is_html(info):
            marked = re.sub(r"<a\s[^>]*>", anchor, text, flags=re.I)
            if marked != text:
                text = re.sub(r"(?i)</head>", MIRROR_HEAD + "</head>", marked, count=1)
            text = ATTR_RE.sub(attr, text)
            text = re.sub(r"(<style[^>]*>)(.*?)(</style>)",
                          lambda mo: mo.group(1) + CSS_URL_RE.sub(cssu, mo.group(2)) + mo.group(3),
                          text, flags=re.I | re.S)
            text = re.sub(r"""(style\s*=\s*")([^"]*)""", lambda mo: mo.group(1) + CSS_URL_RE.sub(cssu, mo.group(2)), text, flags=re.I)
        elif info["type"] == "text/css":
            text = CSS_URL_RE.sub(cssu, text)
            text = CSS_IMPORT_RE.sub(lambda mo: f"@import {mo.group(1)}{resolve(mo.group(2), base_url) or mo.group(2)}{mo.group(1)}", text)
        return text

    if os.path.exists(SITE):
        shutil.rmtree(SITE)
    written = set()
    for key, info in list(pages.items()) + list(ext.items()):
        lp = local[key]
        if lp in written:
            continue
        written.add(lp)
        dest = os.path.join(SITE, lp.lstrip("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        data = read_raw(info)
        if is_html(info) or info["type"] == "text/css":
            text = data.decode("utf-8", "surrogateescape")
            data = rewrite(text, info, info["url"]).encode("utf-8", "surrogateescape")
        with open(dest, "wb") as f:
            f.write(data)
    for rel in used_avatars:
        dest = os.path.join(SITE, "_avatars", rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(os.path.join(AVATARS, rel), dest)
    for path in FILL:
        src = os.path.join(FILL_DIR, path.lstrip("/"))
        dest = os.path.join(SITE, path.lstrip("/"))
        if os.path.exists(src) and not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)

    # Same fix in the html, which Cloudflare does not cache: a transparent
    # placeholder src makes the game tiles real image boxes in every browser.
    blank = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    for dirpath, _dirs, files in os.walk(SITE):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                data = f.read()
            # Version the site's own css/js urls so Cloudflare's edge cache
            # can't serve copies left over from an earlier build.
            data = re.sub(rb'((?:href|src)=")(/[^"?#]+\.(?:css|js))(")',
                          lambda mo: mo.group(1) + mo.group(2) + b"?m=" + ASSET_VERSION + mo.group(3), data)
            if b'<img class="game-image" style=' in data:
                data = data.replace(b'<img class="game-image" style=', f'<img class="game-image" src="{blank}" style='.encode())
            with open(p, "wb") as f:
                f.write(data)
    for path, extra in PATCHES.items():
        if EDITION != "main" or not os.path.exists(os.path.join(SITE, path.lstrip("/"))):
            continue
        with open(os.path.join(SITE, path.lstrip("/")), "a") as f:
            f.write(extra)

    # 404 page in the site's own style.
    index = os.path.join(SITE, "index.html")
    index_html = open(index, errors="replace").read() if os.path.exists(index) else ""
    css = next((mo.group(1) for mo in re.finditer(r'<link[^>]*href="(/[^"]+\.css[^"]*)"', index_html)), "")
    os.makedirs(os.path.join(SITE, "_mirror"), exist_ok=True)
    with open(os.path.join(SITE, "_mirror/404.html"), "w") as f:
        f.write(NOT_FOUND_PAGE.replace("{css}", css))
    with open(os.path.join(SITE, "_mirror/mirror.js"), "w") as f:
        f.write(MIRROR_JS)

    lines = ["# Generated by ~/src/mczone-archive/scrape.py build. Do not edit.",
             "map {http.request.orig_uri} {mz_file} {mz_redir301} {mz_redir302} {"]
    for uri, (kind, target) in sorted(routes.items()):
        cols = [caddy_str(target) if kind == c else "-" for c in ("file", "redir301", "redir302")]
        lines.append(f"\t{caddy_str(uri)} {' '.join(cols)}")
    lines += ["}",
              # vars matchers treat an unset map output as "" (CEL does not)
              "@mz_redir301 not vars {mz_redir301} \"\"",
              "redir @mz_redir301 {mz_redir301} 301",
              "@mz_redir302 not vars {mz_redir302} \"\"",
              "redir @mz_redir302 {mz_redir302} 302",
              "@mz_file not vars {mz_file} \"\"",
              "rewrite @mz_file {mz_file}",
              # A page url with a query we have no capture for would otherwise
              # silently serve the page without its query (e.g. page 1 for
              # ?page=999). Show "not archived" instead; assets are exempt.
              "@mz_unknown_query {",
              "\tnot vars {query} \"\"",
              "\tvars {mz_file} \"\"",
              "\tnot path *.css *.js *.png *.jpg *.jpeg *.gif *.ico *.svg *.woff *.ttf *.eot *.mp4 *.json *.txt",
              "}",
              "error @mz_unknown_query 404"]
    with open(ROUTES, "w") as f:
        f.write("\n".join(lines) + "\n")

    with open(MISSING, "w") as f:
        for k, n in sorted(missing.items(), key=lambda kv: -kv[1]):
            if served_url(k) not in routes:
                f.write(f"{n}\t{k}\n")
    print(f"wrote {len(written)} files ({len(pages)} pages, {len(ext)} off-site assets, "
          f"{len(used_avatars)} archived heads), "
          f"{len(routes) - nredir} routed urls, {nredir} redirects")


if __name__ == "__main__":
    {"fetch": cmd_fetch, "ext": cmd_ext, "fill": cmd_fill, "redirects": cmd_redirects, "avatars": cmd_avatars, "build": cmd_build}[sys.argv[1]]()
