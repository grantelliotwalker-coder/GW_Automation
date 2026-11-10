"""
make_release.py - build a customer install pack and publish it on the
hidden downloads page (https://opctools.gwstudio.com.au/downloads/).

    python tools\\make_release.py hl 1.1.0
    python tools\\make_release.py dalk 1.2.0

What it does
  1. Finds the built MSI and the installation manual in the product repo
     (by default the folders next to this website repo:
     ..\\opcua-historian and ..\\opcua-DAtaBridge; change with --repo).
  2. Builds downloads\\<Product>-<version>.zip containing:
        the MSI, the Quick Start PDF and the Installation Manual PDF.
  3. Removes that product's older zip from downloads\\ (only the latest
     version is offered; old ones stay in git history).
  4. Records the release in downloads\\releases.json and rebuilds the
     hidden page downloads\\index.html and downloads\\SHA256SUMS.txt.
  5. Prints a ready-to-send email (download link + checksum). Attach the
     site's .lic file from gwlicence.py to that email.

Then publish:
    git add downloads
    git commit -m "Release HistorianLink 1.1.0"
    git push

The page is hidden, not secret: it isn't linked from the site, it's
excluded from search engines (noindex + robots.txt) and it's not in the
sitemap. Anyone with the link can download, but the software needs a
licence file, which only comes from GW Automation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import sys
import zipfile
from pathlib import Path

SITE      = "https://opctools.gwstudio.com.au"
WEB_ROOT  = Path(__file__).resolve().parent.parent
DL_DIR    = WEB_ROOT / "downloads"
RELEASES  = DL_DIR / "releases.json"
MAX_MB    = 95          # GitHub refuses files over 100 MB

PRODUCTS = {
    "HistorianLink": {
        "aliases": ("hl", "historianlink"),
        "repo": "opcua-historian",
        "msi": lambda v: [f"dist/HistorianLink-{v}-x64.msi"],
        "msi_name": lambda v: f"HistorianLink-{v}-x64.msi",
        "manual": ["docs/HistorianLink-Installation-Manual.pdf"],
        "quickstart": ["docs/HistorianLink-Quick-Start.pdf"],
        "blurb": "OPC UA historian client: exports, scheduled reports, trend analyser, dashboards and alarm history.",
        "needs": "Windows 10 / Server 2016 or later (64-bit).",
    },
    "OpcDaLink": {
        "aliases": ("dalk", "da", "opcdalink"),
        "repo": "opcua-DAtaBridge",
        "msi": lambda v: [f"dist/OpcDaLink-{v}-x64.msi", "dist/OpcDaLink.msi"],
        "msi_name": lambda v: f"OpcDaLink-{v}-x64.msi",
        "manual": ["docs/OpcDaLink_Installation_Manual.pdf", "docs/OpcDaLink-Installation-Manual.pdf"],
        "quickstart": ["docs/OpcDaLink-Quick-Start.pdf"],
        "blurb": "OPC DA to OPC UA bridge, with OPC HDA history and alarms from OPC AE or OPC UA.",
        "needs": "Windows 10 / Server 2016 or later, on a machine that can reach the OPC DA server over DCOM.",
    },
}


def product_for(name: str) -> str:
    n = name.lower()
    for p, info in PRODUCTS.items():
        if n in info["aliases"]:
            return p
    sys.exit(f"Unknown product '{name}'. Use hl or dalk.")


def first_existing(base: Path, rels: list[str], what: str) -> Path:
    for r in rels:
        if (base / r).exists():
            return base / r
    sys.exit(f"Can't find the {what}. Looked for:\n  " +
             "\n  ".join(str(base / r) for r in rels) +
             "\nBuild it first, or point --repo at the product folder.")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def human_size(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB"


def render_page(releases: dict) -> str:
    esc = html.escape
    cards = []
    for product in PRODUCTS:
        r = releases.get(product)
        if not r:
            continue
        url = f"/downloads/{r['file']}"
        cards.append(f"""
    <div class="cbox" style="margin-bottom:22px">
      <h2 style="margin-top:0">{esc(product)} <span style="color:var(--muted,#7a8a99);font-weight:400">{esc(r['version'])}</span></h2>
      <p>{esc(PRODUCTS[product]['blurb'])}</p>
      <p><a class="btn btn-a" href="{esc(url)}" download>Download {esc(r['file'])}</a>
         <span style="margin-left:10px;color:var(--muted,#7a8a99)">{esc(r['size'])} &middot; released {esc(r['date'])}</span></p>
      <p style="margin-bottom:4px">Contains the installer ({esc(r['msi'])}), the Quick Start guide and the Installation Manual.</p>
      <p style="font-size:12px;word-break:break-all;margin-top:10px">SHA-256: <code>{esc(r['sha256'])}</code></p>
    </div>""")
    body = "".join(cards) or "<p>No install packs are published here at the moment. Email us and we will send you the current one.</p>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'sha256-+He5rwAMKHlS60A3KsWW/ahi5Zm/0e7TBwm9i09ghIk=' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://cloudflareinsights.com; object-src 'none'; base-uri 'self'; form-action 'none'; upgrade-insecure-requests">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="theme-color" content="#080c10">
<title>Downloads | GW Automation</title>
<link rel="icon" href="/assets/favicon.ico" sizes="48x48">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css?v=9">
<script>(function(d){{d.className+=' js';var t;try{{t=localStorage.getItem('gw-theme')}}catch(e){{}}if(t!=='light'&&t!=='dark')t=window.matchMedia&&matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';d.setAttribute('data-theme',t)}})(document.documentElement)</script>
</head>
<body>

<header>
  <div class="hdr">
    <div class="logo" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="#00c8ff" stroke-width="2" stroke-linecap="round">
        <path d="M2 17l5-6 4 4 4-8 5 5"/><circle cx="7" cy="11" r="1.4" fill="#00c8ff" stroke="none"/>
        <circle cx="11" cy="15" r="1.4" fill="#00c8ff" stroke="none"/><circle cx="15" cy="7" r="1.4" fill="#00ff9d" stroke="none"/>
      </svg>
    </div>
    <span class="brand">GW <em>Automation</em></span>
    <nav id="nav">
      <a href="/">Home</a>
      <a href="/#contact">Contact</a>
    </nav>
    <button class="theme-btn" id="themeBtn" type="button" aria-label="Switch colour theme" title="Switch colour theme"><svg id="themeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"></svg></button>
  </div>
</header>

<main class="page">
  <div class="wrap">
    <div class="eyebrow">Downloads</div>
    <h1>Install packs</h1>
    <p>Each pack contains the installer, a Quick Start guide and the full Installation Manual.
    The software needs a licence file for your site, which GW Automation emails to you
    separately. No licence yet? <a href="mailto:gwautomation@gwstudio.com.au?subject=GW%20Automation%20trial%20request">Ask for a free 90-day trial</a>.</p>
{body}
    <h2>Checking a download</h2>
    <p>In PowerShell, run <code>Get-FileHash .\\&lt;file&gt;.zip -Algorithm SHA256</code> and compare
    the result with the SHA-256 listed with the download. If they differ, don't install it, and let us know.</p>
    <p>Questions: <a href="mailto:gwautomation@gwstudio.com.au">gwautomation@gwstudio.com.au</a></p>
  </div>
</main>

<script src="/assets/site.js?v=5"></script>
<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "8b0d29eb9cca403e8e6900666772bc1c"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>
"""


def write_outputs(releases: dict) -> None:
    RELEASES.write_text(json.dumps(releases, indent=2) + "\n", encoding="utf-8")
    (DL_DIR / "index.html").write_text(render_page(releases), encoding="utf-8")
    sums = "".join(f"{r['sha256'].lower()}  {r['file']}\n" for r in releases.values())
    (DL_DIR / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")


def email_text(product: str, r: dict) -> str:
    return f"""Subject: {product} {r['version']} install pack and licence

Hi,

Here's {product} {r['version']}.

Download (installer, Quick Start guide and Installation Manual, {r['size']}):
{SITE}/downloads/{r['file']}

SHA-256 (to check the download):
{r['sha256']}

Your licence file is attached. After installing, open the Admin UI from the
tray icon, go to the Licence page and choose the file. The Quick Start
guide in the zip walks through it, and the manual covers the rest.

The software never needs internet access, so download the zip on an office
PC and copy it across however your site normally moves files.

Any questions, just reply or give me a call.

Grant Walker
GW Automation
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build a customer install pack")
    ap.add_argument("product", help="hl or dalk")
    ap.add_argument("version", help="e.g. 1.1.0")
    ap.add_argument("--repo", help="product repo folder (default: sibling folder)")
    ap.add_argument("--msi", help="MSI path (default: found in the repo's dist folder)")
    ap.add_argument("--manual", help="manual PDF path (default: found in the repo's docs folder)")
    args = ap.parse_args(argv)

    product = product_for(args.product)
    info    = PRODUCTS[product]
    version = args.version.strip().lstrip("v")
    repo    = Path(args.repo) if args.repo else WEB_ROOT.parent / info["repo"]
    msi     = Path(args.msi) if args.msi else first_existing(repo, info["msi"](version), "MSI")
    manual  = Path(args.manual) if args.manual else first_existing(repo, info["manual"], "manual PDF")
    qs      = first_existing(repo, info["quickstart"], "Quick Start PDF")

    DL_DIR.mkdir(exist_ok=True)
    zip_name = f"{product}-{version}.zip"
    out = DL_DIR / zip_name
    msi_name = info["msi_name"](version)
    manual_name = f"{product} Installation Manual.pdf"
    qs_name = f"{product} Quick Start.pdf"
    print(f"Building {zip_name}")
    print(f"  MSI:         {msi}")
    print(f"  quick start: {qs}")
    print(f"  manual:      {manual}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(msi, msi_name)
        z.write(qs, qs_name)
        z.write(manual, manual_name)
    size = out.stat().st_size
    if size > MAX_MB * 1_000_000:
        out.unlink()
        sys.exit(f"The zip is {human_size(size)}; GitHub only takes files under 100 MB. "
                 "Use a Nuitka build or host this release elsewhere.")

    for old in DL_DIR.glob(f"{product}-*.zip"):
        if old.name != zip_name:
            old.unlink()
            print(f"  removed older {old.name}")

    releases = json.loads(RELEASES.read_text(encoding="utf-8")) if RELEASES.exists() else {}
    releases[product] = {
        "version": version, "file": zip_name, "msi": msi_name,
        "size": human_size(size), "sha256": sha256(out),
        "date": dt.date.today().strftime("%-d %B %Y") if sys.platform != "win32"
                else dt.date.today().strftime("%#d %B %Y"),
    }
    write_outputs(releases)
    r = releases[product]
    print(f"  {zip_name}: {r['size']}, SHA-256 {r['sha256']}")
    print("\nNext:")
    print(f'  git add downloads && git commit -m "Release {product} {version}" && git push')
    print(f"\nDownload page: {SITE}/downloads/")
    print("\n" + "-" * 72 + "\nEmail to send (attach the site's .lic file):\n" + "-" * 72)
    print(email_text(product, r))


if __name__ == "__main__":
    main()
