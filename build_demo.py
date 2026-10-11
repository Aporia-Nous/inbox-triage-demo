#!/usr/bin/env python3
"""Builds demo.html (one self-contained file) from results.json."""
import json, os, html
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "results.json")))
E = html.escape

CAT = {"URGENT": ("urgent", "Urgent"), "NOT SURE": ("unsure", "Not sure"), "NORMAL": ("normal", "Normal")}
mode_public = "Rules + AI double-check" if d["mode"].startswith("rules + AI") else "Rules only (AI double-check off for this demo)"

def sender(e): return e["from"].split("<")[0].strip()
def addr(e): return e["from"].split("<")[-1].rstrip(">") if "<" in e["from"] else ""

def card(r):
    e = r["email"]; cls, name = CAT[r["category"]]
    pct = int(round(r["confidence"] * 100))
    ping = ('<span class="chip ping">🔔 Slack ping <em>(preview)</em></span>'
            if r["slack"] else '<span class="chip quiet">No ping</span>')
    payload = (f'<details><summary>Slack message it would send</summary><pre>{E(json.dumps(r["slack"], indent=2, ensure_ascii=False))}</pre></details>'
               if r["slack"] else "")
    body = E(e["body"]).replace("\n", "<br>")
    return f"""
<article class="card {cls}" id="mail-{e['id']}" data-cat="{cls}">
  <div class="top"><span class="badge {cls}">{name}</span><span class="time">{E(e['received'])}</span></div>
  <h3>{E(e['subject'])}</h3>
  <div class="from">{E(sender(e))} <span>&lt;{E(addr(e))}&gt;</span></div>
  <p class="snippet">{body}</p>
  <div class="why"><b>Why:</b> {E(r['reason'])}</div>
  <div class="conf"><span>Confidence</span><div class="bar"><i style="width:{pct}%"></i></div><b>{pct}%</b></div>
  <div class="chips"><span class="chip label"><span class="full">Gmail label: </span>🏷 {E(r['gmail_label'])}</span>{ping}<span class="chip noreply full">Reply sent: none</span></div>
  {payload}
</article>"""

groups = {k: [r for r in d["results"] if r["category"] == k] for k in CAT}

def col(k):
    cls, name = CAT[k]
    sub = {"URGENT": "Phone buzzes now", "NOT SURE": "Phone buzzes: please look", "NORMAL": "Labeled, no ping"}[k]
    return f"""<section class="col col-{cls}" data-col="{cls}">
  <header><h2><span class="dot {cls}"></span>{name}<span class="count">{len(groups[k])}</span></h2><small>{sub}</small></header>
  {''.join(card(r) for r in groups[k])}
</section>"""

def ping(r):
    e = r["email"]; cls = CAT[r["category"]][0]
    head = "URGENT email" if r["category"] == "URGENT" else "Not sure: please look"
    return f"""<div class="note {cls}">
  <div class="nhead"><span class="app">#</span><b>Slack</b><span>#email-alerts · {E(e['received'].replace('Mon ', ''))}</span></div>
  <div class="ntitle">{'🚨' if cls=='urgent' else '🟡'} {head}</div>
  <div class="nsubj">{E(e['subject'])}</div>
  <div class="nfrom">From {E(sender(e))}</div>
  <div class="nwhy">{E(r['reason'])}</div>
</div>"""

pings = [r for r in d["results"] if r["slack"]]
pings.sort(key=lambda r: (0 if r["category"] == "URGENT" else 1, r["email"]["id"]))
c = d["counts"]

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inbox Triage: HVAC email sorting demo</title>
<style>
:root{{--bg:#0b0f17;--panel:#121826;--panel2:#171f30;--line:#232d42;--text:#e6ebf5;--mute:#8d98b0;
--red:#ff5a5f;--redbg:rgba(255,90,95,.12);--amber:#ffbe3d;--amberbg:rgba(255,190,61,.12);--green:#3ecf8e;--greenbg:rgba(62,207,142,.10);--blue:#6ea8ff}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}
body{{margin:0;background:radial-gradient(1200px 600px at 10% -10%,#16213a 0,transparent 60%),var(--bg);color:var(--text);
font:14px/1.45 Inter,"IBM Plex Sans",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1560px;margin:0 auto;padding:18px 28px 10px}}
.brand{{display:flex;align-items:center;justify-content:space-between;gap:20px}}
.brand h1{{margin:0;font-size:22px;letter-spacing:-.01em}}.brand h1 span{{color:var(--mute);font-weight:500}}
.logo{{display:inline-grid;place-items:center;width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#ff5a5f,#ffbe3d);margin-right:10px;vertical-align:-9px;font-size:18px}}
.mode{{color:var(--mute);font-size:12.5px;border:1px solid var(--line);border-radius:999px;padding:6px 12px;background:var(--panel)}}
.mode b{{color:var(--text);font-weight:600}}
.summary{{margin:14px 0 12px;display:grid;grid-template-columns:1.5fr repeat(4,1fr);gap:12px}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:11px 16px}}
.stat .n{{font-size:26px;font-weight:700;letter-spacing:-.02em}}.stat .l{{color:var(--mute);font-size:12.5px}}
.stat.big{{background:linear-gradient(135deg,#17213a,#121826)}}.stat.big .n{{font-size:19px;line-height:1.35;font-weight:650}}
.stat.u .n{{color:var(--red)}}.stat.s .n{{color:var(--amber)}}.stat.o .n{{color:var(--green)}}.stat.r .n{{color:var(--blue)}}
.rule{{display:flex;gap:10px;align-items:center;background:var(--amberbg);border:1px solid rgba(255,190,61,.35);color:#ffe3a6;border-radius:12px;padding:8px 14px;font-size:13.5px;margin-bottom:10px}}
.tabs{{display:flex;gap:6px;margin-bottom:12px;border-bottom:1px solid var(--line)}}
.tab{{appearance:none;border:0;background:none;color:var(--mute);font:inherit;font-weight:600;padding:10px 14px;border-bottom:2px solid transparent;cursor:pointer}}
.tab:hover{{color:var(--text)}}.tab.on{{color:var(--text);border-color:var(--blue)}}
.tab .k{{display:inline-block;min-width:22px;margin-left:6px;padding:1px 7px;border-radius:999px;background:var(--panel2);font-size:12px}}
.layout{{display:grid;grid-template-columns:1fr 360px;gap:20px;align-items:start}}
.board{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;align-items:start}}
.board.single{{grid-template-columns:1fr}}.board.single .col{{display:none}}.board.single .col.show{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;align-items:start}}
.board.single .col.show header{{grid-column:1/-1}}
.col{{background:rgba(18,24,38,.6);border:1px solid var(--line);border-radius:16px;padding:12px}}
.col header{{padding:2px 4px 10px}}.col h2{{margin:0;font-size:15px;display:flex;align-items:center;gap:8px}}.col small{{color:var(--mute)}}
.count{{margin-left:auto;background:var(--panel2);border-radius:999px;padding:1px 9px;font-size:12.5px;color:var(--mute)}}
.dot{{width:9px;height:9px;border-radius:50%}}.dot.urgent{{background:var(--red);box-shadow:0 0 10px var(--red)}}.dot.unsure{{background:var(--amber)}}.dot.normal{{background:var(--green)}}
.card{{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--line);border-radius:12px;padding:10px 12px;margin-bottom:9px}}
.board.single .card{{margin-bottom:0}}
.card.urgent{{border-left-color:var(--red);background:linear-gradient(90deg,var(--redbg),var(--panel) 40%)}}
.card.unsure{{border-left-color:var(--amber);background:linear-gradient(90deg,var(--amberbg),var(--panel) 40%)}}
.card.normal{{border-left-color:rgba(62,207,142,.55)}}
.top{{display:flex;justify-content:space-between;align-items:center}}.time{{color:var(--mute);font-size:12px}}
.badge{{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:6px}}
.badge.urgent{{color:var(--red);background:var(--redbg)}}.badge.unsure{{color:var(--amber);background:var(--amberbg)}}.badge.normal{{color:var(--green);background:var(--greenbg)}}
.card h3{{margin:7px 0 2px;font-size:14.5px;line-height:1.3}}
.from{{font-size:12.5px;color:#c3cbe0}}.from span{{color:var(--mute)}}
.snippet{{color:var(--mute);font-size:12.5px;margin:5px 0 7px;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}}
.board.single .snippet{{-webkit-line-clamp:5}}
.board:not(.single) .full,.board:not(.single) details{{display:none}}
.why{{font-size:13px;background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:8px;padding:7px 9px}}
.card.unsure .why{{border-color:rgba(255,190,61,.35);color:#ffe7b3}}.card.urgent .why{{border-color:rgba(255,90,95,.35);color:#ffd0d1}}
.conf{{display:flex;align-items:center;gap:8px;margin:7px 0 7px;font-size:12px;color:var(--mute)}}
.bar{{flex:1;height:6px;background:#0d1320;border-radius:9px;overflow:hidden}}.bar i{{display:block;height:100%;border-radius:9px}}
.urgent .bar i{{background:var(--red)}}.unsure .bar i{{background:var(--amber)}}.normal .bar i{{background:var(--green)}}.conf b{{color:var(--text);min-width:34px;text-align:right}}
.chips{{display:flex;flex-wrap:wrap;gap:5px}}.chip{{font-size:11.5px;padding:3px 8px;border-radius:6px;background:var(--panel2);color:#b8c2d9;border:1px solid var(--line)}}
.chip em{{color:var(--mute);font-style:normal}}.chip.ping{{color:#cfe0ff}}.chip.noreply{{color:var(--mute)}}
details{{margin-top:8px}}summary{{cursor:pointer;color:var(--blue);font-size:12px}}
pre{{font:11px/1.4 "JetBrains Mono","IBM Plex Mono",monospace;background:#0a0e16;border:1px solid var(--line);border-radius:8px;padding:9px;overflow:auto;max-height:240px;color:#b9c4dc}}
.phone{{position:sticky;top:16px;background:#05070b;border:1px solid #2a3348;border-radius:38px;padding:14px;box-shadow:0 30px 80px rgba(0,0,0,.55),inset 0 0 0 2px #10151f}}
.screen{{border-radius:28px;background:linear-gradient(180deg,#1b2440,#0e1322 55%);padding:14px 12px 16px;min-height:600px}}
.notch{{width:110px;height:24px;background:#05070b;border-radius:0 0 16px 16px;margin:-14px auto 8px}}
.clock{{text-align:center;font-size:44px;font-weight:300;letter-spacing:-.02em;margin:4px 0 0}}.date{{text-align:center;color:#aab4cc;font-size:13px;margin-bottom:12px}}
.ptitle{{display:flex;justify-content:space-between;font-size:12px;color:#aab4cc;margin:0 4px 8px}}
.note{{background:rgba(255,255,255,.09);backdrop-filter:blur(10px);border-radius:16px;padding:10px 12px;margin-bottom:8px;border-left:3px solid transparent}}
.note.urgent{{border-left-color:var(--red)}}.note.unsure{{border-left-color:var(--amber)}}
.nhead{{display:flex;gap:7px;align-items:center;font-size:11.5px;color:#c9d1e4}}.nhead span:last-child{{margin-left:auto;color:#9aa5bf}}
.app{{display:inline-grid;place-items:center;width:18px;height:18px;border-radius:5px;background:#4a154b;color:#fff;font-weight:800;font-size:12px}}
.ntitle{{font-weight:700;font-size:13px;margin-top:5px}}.nsubj{{font-size:13px;margin-top:1px}}.nfrom{{font-size:12px;color:#aab4cc}}
.nwhy{{font-size:11.5px;color:#9aa5bf;margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.pfoot{{text-align:center;font-size:11.5px;color:#7f8aa3;margin-top:10px}}
footer{{max-width:1560px;margin:20px auto 0;padding:16px 28px 28px;color:var(--mute);font-size:13px;border-top:1px solid var(--line);display:flex;justify-content:space-between}}
</style></head>
<body>
<div class="wrap">
  <div class="brand">
    <h1><span class="logo">✉</span>Inbox Triage <span>· HVAC shop email sorting</span></h1>
    <div class="mode">Mode: <b>{E(mode_public)}</b> · No real Gmail or Slack calls</div>
  </div>
  <div class="summary" id="summary">
    <div class="stat big"><div class="n">{d['total']} emails: {c['URGENT']} urgent, {c['NOT SURE']} not sure, {c['NORMAL']} normal; {d['replies_sent']} replies sent.</div><div class="l">One morning's inbox (sample emails)</div></div>
    <div class="stat u"><div class="n">{c['URGENT']}</div><div class="l">Urgent: phone buzzes now</div></div>
    <div class="stat s"><div class="n">{c['NOT SURE']}</div><div class="l">Not sure: flagged for a person</div></div>
    <div class="stat o"><div class="n">{c['NORMAL']}</div><div class="l">Normal: labeled, no ping</div></div>
    <div class="stat r"><div class="n">{d['replies_sent']}</div><div class="l">Replies sent (it never replies)</div></div>
  </div>
  <div class="rule">🟡 <span><b>The "tell me when it doesn't know" rule:</b> weak, mixed, or missing signals go to <b>Not sure</b> and still ping your phone. They never get quietly filed as Normal.</span></div>
  <nav class="tabs">
    <button class="tab on" data-tab="all">All three<span class="k">{d['total']}</span></button>
    <button class="tab" data-tab="urgent">Urgent<span class="k">{c['URGENT']}</span></button>
    <button class="tab" data-tab="unsure">Not sure<span class="k">{c['NOT SURE']}</span></button>
    <button class="tab" data-tab="normal">Normal<span class="k">{c['NORMAL']}</span></button>
  </nav>
  <div class="layout">
    <main class="board" id="board">{col('URGENT')}{col('NOT SURE')}{col('NORMAL')}</main>
    <aside class="phone" id="alerts"><div class="screen"><div class="notch"></div>
      <div class="clock">10:31</div><div class="date">Monday · {len(pings)} Slack alerts</div>
      <div class="ptitle"><span>Notifications</span><span>{c['URGENT']} urgent · {c['NOT SURE']} not sure</span></div>
      {''.join(ping(r) for r in pings)}
      <div class="pfoot">Preview only. Nothing was sent to Slack.</div>
    </div></aside>
  </div>
</div>
<footer><span>Demo with sample emails. Sorts only, never replies.</span><span>Names, addresses and numbers are made up.</span></footer>
<script>
const board=document.getElementById('board');
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{{
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===t));
  const k=t.dataset.tab;board.classList.toggle('single',k!=='all');
  document.querySelectorAll('.col').forEach(c=>c.classList.toggle('show',c.dataset.col===k));
}}));
</script>
</body></html>"""
open(os.path.join(HERE, "demo.html"), "w").write(page)
print("wrote demo.html", len(page), "bytes")
