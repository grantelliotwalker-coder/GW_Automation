#!/usr/bin/env python3
"""Build the one-page product datasheets in assets/docs/.

    pip install playwright && playwright install chromium
    python tools/make_datasheets.py

Edit the SHEETS data below (version, date, features, facts), then run it and
commit the two PDFs. The page is laid out for A4 and must stay on one page;
the script fails if either sheet spills onto a second.
"""
import base64, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "docs"
DATE = "November 2026"
ABN = "81 848 968 209"
MAIL = "gwautomation@gwstudio.com.au"
SITE = "opctools.gwstudio.com.au"

SHEETS = [
    dict(
        file="HistorianLink-Datasheet.pdf", name="Historian", version="1.1", shot="hl-analyser.png",
        tagline="OPC UA history, reports, dashboards and alarms",
        intro="HistorianLink connects as an OPC UA client to any plant historian that serves history over OPC "
              "UA, whatever the vendor, and turns its archive into data you can work with. Engineers and viewers use it from "
              "their own browsers, so there is no client software to roll out.",
        features=[
            ("History export", "Raw or resampled history to .xlsx or .csv, with millisecond timestamps, a plain-English quality column and UTC or local time."),
            ("Scheduled reports", "Repeatable report definitions run daily, weekly or monthly. The last five runs of each are kept."),
            ("Live dashboards", "Tiles with the current value and a sparkline, polled only while someone is watching."),
            ("Trend analyser", "Multi-tag chart with severity colouring, presets and a scrubbing ruler."),
            ("Alarms", "Current alarms over OPC UA, with an optional add-on for WinCC alarm history."),
            ("Access control", "Administrator, engineer and viewer roles, optional device trust and an audit trail."),
        ],
        facts=[
            ("Role", "OPC UA client, read-only"),
            ("Works with", "Any server that provides history over OPC UA"),
            ("Data out", ".xlsx, .csv, scheduled reports, live dashboards"),
            ("OPC UA security", "Basic256Sha256, Sign or SignAndEncrypt"),
            ("Network users", "HTTPS, TLS 1.2 minimum"),
            ("Platform", "Windows Server 2016+ or Windows 10+, 64-bit"),
            ("Footprint", "Self-contained MSI. No database, no runtime, no internet"),
        ],
        boxes=[
            ("Safe on a live historian", "HistorianLink only browses tags and reads values and history. It never writes values or changes the historian's configuration."),
            ("Licensing", "One perpetual licence per site, not tied to a machine. Signed licence file, checked offline. No per-tag pricing."),
            ("Free 90-day trial", "Full feature set, no tag limit. Installer, manual and trial licence sent by email. Most trials are running the same day."),
        ],
    ),
    dict(
        file="OpcDaLink-Datasheet.pdf", name="OpcDa", version="1.2", shot="da-dashboard.png",
        tagline="OPC DA to OPC UA bridge",
        intro="OpcDaLink sits in front of a legacy OPC DA server, connects to it as a client over DCOM, and republishes the "
              "whole address space as a modern OPC UA server, with history from OPC HDA and alarms from OPC AE alongside "
              "it. The original server is left exactly as it is.",
        features=[
            ("Full address-space mirror", "Branches become folders, leaves become variables, item IDs carry through as string NodeIds."),
            ("Faithful type mapping", "VARIANT types to UA types, DA quality to UA status codes, item timestamps as source timestamps."),
            ("Read and write", "Writes pass back to the DA server, only for the UA users you allow."),
            ("History over OPC UA", "Standard HistoryRead translated on demand into OPC HDA reads. No history is stored locally."),
            ("Alarms", "OPC AE or OPC UA alarms and conditions, republished as UA nodes. Optional agent for OLE DB alarm archives."),
            ("Big-server mode", "Feed it a tag list file and skip browsing on servers with tens of thousands of items."),
        ],
        facts=[
            ("Role", "OPC DA client and OPC UA server"),
            ("Works with", "OPC DA 2.0 servers, 32-bit or 64-bit, plus optional OPC HDA and AE"),
            ("UA endpoint", "opc.tcp, on a port you choose"),
            ("OPC UA security", "Basic256Sha256, Sign or Sign and Encrypt"),
            ("Administration", "Web interface on the local machine only"),
            ("Platform", "Windows Server 2016+ or Windows 10+, 64-bit"),
            ("Footprint", "Self-contained MSI. No Automation Wrapper, no database, no internet"),
        ],
        boxes=[
            ("Leaves the DA server alone", "OpcDaLink needs only the access any DA client has. Installed on the DA server machine, it keeps DCOM off the network entirely."),
            ("Licensing", "One perpetual licence per site, covering every OpcDaLink machine there. Signed licence file, checked offline. No per-tag pricing."),
            ("Free 90-day trial", "Full feature set, no tag limit. Installer, manual and trial licence sent by email. Most trials are running the same day."),
        ],
    ),
]

CSS = """
@page{size:A4;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,'Segoe UI',Arial,sans-serif;color:#22343f;font-size:9.6pt;line-height:1.45;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.sheet{width:210mm;height:297mm;padding:13mm 14mm 11mm;display:flex;flex-direction:column;overflow:hidden}
.top{display:flex;align-items:center;justify-content:space-between;padding-bottom:4mm;border-bottom:.3mm solid #cfdbe3}
.brand{display:flex;align-items:center;gap:3mm;font-weight:700;letter-spacing:.6mm;font-size:10pt;color:#0b1a22}
.brand em{font-style:normal;color:#0072a3}
.brand .logo{width:8mm;height:8mm;border:.3mm solid #0072a3;border-radius:1.2mm;display:grid;place-items:center}
.brand svg{width:5mm;height:5mm}
.kicker{font-family:'DejaVu Sans Mono',Consolas,monospace;font-size:6.6pt;letter-spacing:.35mm;color:#5a6f7d;text-transform:uppercase}
h1{font-size:27pt;line-height:1.1;color:#0b1a22;letter-spacing:-.2mm;margin-top:7mm}
h1 em{font-style:normal;color:#0072a3}
.tag{font-family:'DejaVu Sans Mono',Consolas,monospace;font-size:7.6pt;letter-spacing:.3mm;text-transform:uppercase;color:#0072a3;margin-top:1.5mm}
.intro{margin-top:4mm;font-size:10.4pt;max-width:172mm}
.shot{margin-top:5.5mm;height:78mm;border-radius:1.6mm;overflow:hidden;background:#080c10;border:.3mm solid #1a2a35}
.shot img{width:100%;height:100%;object-fit:cover;object-position:top left;display:block}
.cols{display:grid;grid-template-columns:1.12fr .88fr;gap:8mm;margin-top:6mm}
h2{font-family:'DejaVu Sans Mono',Consolas,monospace;font-size:7pt;letter-spacing:.4mm;text-transform:uppercase;color:#0072a3;margin-bottom:2.2mm}
.feat li{list-style:none;padding-left:3.6mm;position:relative;margin-bottom:1.7mm;font-size:9pt}
.feat li::before{content:'';position:absolute;left:0;top:1.75mm;width:1.5mm;height:1.5mm;background:#0072a3;border-radius:.3mm}
.feat b{color:#0b1a22}
table{width:100%;border-collapse:collapse;font-size:8.6pt}
td{padding:1.45mm 0;border-bottom:.2mm solid #dbe5ec;vertical-align:top}
td:first-child{width:34%;color:#0b1a22;font-weight:600;padding-right:2mm}
tr:last-child td{border-bottom:none}
.boxes{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:auto;padding-top:5mm}
.box{background:#f1f6f9;border:.25mm solid #cfdbe3;border-radius:1.4mm;padding:3.4mm 3.6mm}
.box h3{font-size:9.2pt;color:#0b1a22;margin-bottom:1.2mm}
.box p{font-size:8.3pt;line-height:1.42}
.foot{margin-top:5mm;padding-top:3.4mm;border-top:.3mm solid #cfdbe3;display:flex;justify-content:space-between;align-items:center}
.foot .cta{font-size:9.6pt;color:#0b1a22;font-weight:600;white-space:nowrap}
.foot .kicker{text-align:right}
.foot .cta span{color:#0072a3}
"""
LOGO = ('<svg viewBox="0 0 24 24" fill="none" stroke="#0072a3" stroke-width="2" stroke-linecap="round"><path d="M2 17l5-6 4 4 4-8 5 5"/>'
        '<circle cx="7" cy="11" r="1.4" fill="#0072a3" stroke="none"/><circle cx="11" cy="15" r="1.4" fill="#0072a3" stroke="none"/>'
        '<circle cx="15" cy="7" r="1.4" fill="#08875a" stroke="none"/></svg>')


def html(s):
    img = base64.b64encode((ROOT / "assets" / s["shot"]).read_bytes()).decode()
    product = s["name"] + "Link"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{product} datasheet</title><style>{CSS}</style></head><body>
<div class="sheet">
  <div class="top"><div class="brand"><div class="logo">{LOGO}</div><span>GW <em>AUTOMATION</em></span></div>
    <div class="kicker">Product datasheet · {product} {s['version']} · {DATE}</div></div>
  <h1>{s['name']}<em>Link</em></h1>
  <div class="tag">{s['tagline']}</div>
  <p class="intro">{s['intro']}</p>
  <div class="shot"><img src="data:image/png;base64,{img}" alt=""></div>
  <div class="cols">
    <div><h2>Key features</h2><ul class="feat">{''.join(f'<li><b>{a}.</b> {b}</li>' for a, b in s['features'])}</ul></div>
    <div><h2>At a glance</h2><table>{''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in s['facts'])}</table></div>
  </div>
  <div class="boxes">{''.join(f'<div class="box"><h3>{a}</h3><p>{b}</p></div>' for a, b in s['boxes'])}</div>
  <div class="foot"><div class="cta">Request a trial or a quote: <span>{MAIL}</span></div>
    <div class="kicker">GW Automation · ABN {ABN} · {SITE}</div></div>
</div></body></html>"""


def main():
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        for s in SHEETS:
            page.set_content(html(s), wait_until="load")
            spill = page.evaluate("(()=>{const e=document.querySelector('.sheet');return e.scrollHeight-e.clientHeight})()")
            if spill > 1:
                sys.exit(f"{s['file']}: content is {spill}px too tall for one A4 page; shorten the text.")
            data = page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
            pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
            if pages != 1:
                sys.exit(f"{s['file']}: produced {pages} pages, expected 1.")
            (OUT / s["file"]).write_bytes(data)
            print("wrote", OUT / s["file"], len(data) // 1024, "KB")
        b.close()


if __name__ == "__main__":
    main()
