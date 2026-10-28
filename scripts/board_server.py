# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Live kanban board of this project's BMad initiative, served on localhost. Read-only.

    uv run scripts/board_server.py [--port 8765] [--no-open] [--folder <initiative folder>]
    uv run scripts/board_server.py --start [--port 8765] [--no-open] [--folder <initiative folder>]
    uv run scripts/board_server.py --stop [--port 8765]

The first form runs in the foreground until Ctrl+C. --start runs the board as its own process, apart from
the terminal or Claude Code session that started it, and returns. Without --port it takes the first free
port from 8765 to 8775, or opens this project's board if one is already running there. --stop stops this
project's board, searching the same ports unless --port is given. Another project's board is never touched.
Every page load runs `tickets.py status`, `tickets.py next` and `tickets.py next backlog` and draws
what they print. `GET /detail?kind=story|epic|backlog&id=...` answers one item's details panel. It never
changes a ticket.
"""

from __future__ import annotations

import argparse
import errno
import html
import json
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import urllib.error
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKETS_REL = Path(".agents/skills/bmad-agent-po/scripts/tickets.py")

CSS = r""":root {
  --page: #0d1117; --area: #161b22; --card: #1c2128; --line: #30363d; --band: #21262d;
  --text: #e6edf3; --muted: #8b949e;
  --high: #f85149; --medium: #d29922; --low: #6e7681; --ready: #3fb950; --accent: #58a6ff; --done: #a371f7;
  color-scheme: dark;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html, body { margin: 0; background: var(--page); color: var(--text); }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       font-size: 14px; line-height: 1.4; padding: 24px 24px 40px; }
header.top { margin-bottom: 24px; }
h1 { font-size: 20px; font-weight: 600; margin: 0 0 8px; }
h1 { display: flex; align-items: center; gap: 12px; }
.kicker, .band .ekicker { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
                          color: var(--text); background: var(--line); border: 1px solid #484f58;
                          border-radius: 4px; padding: 2px 8px; }
.meta { color: var(--muted); }
h2 { font-size: 17px; font-weight: 600; margin: 0 0 16px; }
.err { border: 1px solid var(--line); border-radius: 6px; padding: 12px; margin: 0 0 16px; }
.warn { border: 1px solid var(--line); border-radius: 6px; padding: 12px; margin: 0 0 16px; }
.label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted);
         margin: 0 0 8px; }
.sub { font-size: 11px; color: var(--muted); text-transform: none; letter-spacing: normal; }

/* Next Up */
section.nextup { background: var(--area); border: 1px solid var(--line); border-radius: 6px;
                 padding: 16px; margin-bottom: 32px; }
.nextup h2 { font-size: 20px; margin-bottom: 16px; }
.nextup .label { font-size: 15px; font-weight: 600; color: var(--text); }
.nextup .sub { font-size: 13px; }
.nextup .group { margin-top: 16px; }
.cardgrid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
.card .why { color: var(--muted); font-size: 12px; margin-top: 4px; }
.toggle { cursor: pointer; user-select: none; background: none; border: 0; padding: 0;
          font: inherit; line-height: inherit; color: inherit; text-align: left; display: block;
          width: 100%; }
.trow { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 16px; }
.trow .label { display: inline; margin: 0; }
.caret { display: inline-block; width: 9px; height: 9px; margin: 0 12px 2px 2px;
         border-right: 2.5px solid var(--accent); border-bottom: 2.5px solid var(--accent);
         transform: rotate(-45deg); transition: transform 0.15s; flex: none; }
.caret-space { display: inline-block; width: 20px; flex: none; }
[aria-expanded="true"] .caret { transform: rotate(45deg); margin-bottom: 4px; }
.toggle:hover .label, .band.toggle:hover .etitle { color: var(--text); }
.trow .sub { margin-left: 8px; }
.trow .toggle + div { margin-top: 12px; }

/* cards */
.card { background: var(--card); border: 1px solid var(--line); border-left: 3px solid var(--line);
        border-radius: 6px; padding: 12px; }
.card.risk-high { border-left-color: var(--high); }
.card.risk-medium { border-left-color: var(--medium); }
.card.risk-low { border-left-color: var(--low); }
.card.ready { border-top-color: var(--ready); border-right-color: var(--ready);
              border-bottom-color: var(--ready); }
.card .ref { font-size: 12px; color: var(--muted); }
.card .ttl { font-size: 14px; line-height: 1.4; }
.tag { font-size: 12px; color: var(--muted); }
.pill { display: inline-block; background: var(--ready); color: var(--page); font-size: 11px;
        border-radius: 999px; padding: 0 8px; margin-left: 8px; }
.card { position: relative; }
.card .head { padding-right: 52px; }
.copy { position: absolute; top: 8px; right: 8px; font: inherit; font-size: 11px; line-height: 1.6;
        color: var(--muted); background: var(--band); border: 1px solid var(--line); border-radius: 4px;
        padding: 0 6px; cursor: pointer; opacity: 0; transition: opacity 0.15s; }
.card:hover .copy, .card:focus-within .copy { opacity: 1; }
.copy:hover, .copy:focus-visible { color: var(--text); border-color: var(--accent); }
@media (hover: none) { .copy { opacity: 1; } }
.card[data-detail] { cursor: pointer; }
.card[data-detail]:not(.ready):hover { border-top-color: #484f58; border-right-color: #484f58;
                                        border-bottom-color: #484f58; }
.card[data-detail]:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.card.selected { outline: 2px solid var(--accent); outline-offset: 1px; }

/* details panel */
.epic { position: relative; }
.band { padding-right: 96px; }
.edetail { position: absolute; top: 10px; right: 16px; font: inherit; font-size: 12px; line-height: 1.6;
           color: var(--muted); background: var(--card); border: 1px solid var(--line); border-radius: 4px;
           padding: 0 8px; cursor: pointer; }
.edetail:hover, .edetail:focus-visible, .edetail.selected { color: var(--text); border-color: var(--accent); }
.panel { position: fixed; top: 0; right: 0; bottom: 0; width: 400px; max-width: 100%; z-index: 10;
         background: var(--area); border-left: 1px solid var(--line); box-shadow: -8px 0 24px rgba(0, 0, 0, 0.45);
         overflow-y: auto; padding: 20px 20px 32px; }
.pclose { position: absolute; top: 14px; right: 14px; width: 28px; height: 28px; font: inherit; font-size: 18px;
          line-height: 1; color: var(--muted); background: none; border: 1px solid var(--line);
          border-radius: 4px; cursor: pointer; }
.pclose:hover, .pclose:focus-visible { color: var(--text); border-color: var(--accent); }
.pkind { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
         color: var(--muted); margin: 0 44px 6px 0; }
.ptitle { font-size: 18px; font-weight: 600; margin: 0 44px 8px 0; }
.pmeta { color: var(--muted); font-size: 13px; margin: 0 0 8px; }
.pmeta .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px;
             vertical-align: -1px; }
.pmeta .sw.risk-high { background: var(--high); }
.pmeta .sw.risk-medium { background: var(--medium); }
.pmeta .sw.risk-low { background: var(--low); }
.psec { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 12px; }
.psec h3 { font-size: 13px; font-weight: 600; color: var(--muted); margin: 0 0 6px; }
.psec p { margin: 0 0 8px; }
.psec ul { margin: 0 0 8px; padding-left: 18px; }
.psec code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
             background: var(--band); border-radius: 4px; padding: 0 4px; }
.panel a { color: var(--accent); text-decoration: none; }
.panel a:hover { text-decoration: underline; }

/* board */
.cols, .cells { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); }
.cols { position: sticky; top: 0; z-index: 2; background: var(--area);
        border-bottom: 1px solid var(--line); }
.colhead { text-align: center; padding: 14px 8px 12px; }
.colhead + .colhead { border-left: 1px solid var(--line); }
.colhead .label { margin: 0; font-size: 15px; font-weight: 600; color: var(--text); }
.colhead .sub { display: inline-block; text-align: left; min-height: 1.4em; font-size: 12px; margin-top: 10px; }
.stage { display: block; color: var(--text); font-weight: 400; line-height: 1.6; }
.stage b { display: inline-block; min-width: 3.2em; font-weight: 500; }
.stage b.done { color: var(--done); }
.stage b.now { color: var(--accent); }
.stage b.next { color: var(--medium); }
.colhead.toggle { text-align: center; padding: 12px 8px; width: auto; }
.colhead.toggle .caret { margin-right: 10px; }
.colhead.toggle:hover .label { color: var(--muted); }
.board:not(.done-open) .cell[data-state="done"] .card { display: none; }
.board.done-open .done-summary { display: none; }
.done-summary { color: var(--muted); font-size: 13px; padding: 4px 4px; }
section.board { background: var(--area); border: 1px solid var(--line); border-radius: 6px;
                overflow: clip; }
.epic { border-top: 1px solid var(--line); }
.cells { padding-bottom: 24px; }
.band { background: var(--band); display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
        padding: 8px 16px; }
.band .etitle { font-size: 17px; font-weight: 600; }
.band .done { color: var(--muted); }
.band.toggle { display: flex; width: 100%; }
.bar { width: 160px; height: 4px; background: var(--line); border-radius: 2px; overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--ready); }
.cells { background: var(--area); }
.cell { padding: 8px; display: flex; flex-direction: column; gap: 8px; min-height: 48px; }
.cell + .cell { border-left: 1px solid var(--line); }
.cell .label { display: none; }
.other { background: var(--area); color: var(--muted); padding: 8px 16px;
         border-top: 1px solid var(--line); }
footer { margin-top: 32px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--line);
         padding-top: 16px; }
footer .key { display: flex; flex-wrap: wrap; gap: 8px 24px; margin: 0 0 12px; }
footer .key b { color: var(--text); font-weight: 600; margin-right: 6px; }
footer .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin: 0 4px 0 8px;
             vertical-align: -1px; }
footer .sw.risk-high { background: var(--high); }
footer .sw.risk-medium { background: var(--medium); }
footer .sw.risk-low { background: var(--low); }
footer p { margin: 0; }

@media (max-width: 720px) {
  .cols { display: none; }
  .cells, .cardgrid { grid-template-columns: 1fr; }
  .cell + .cell { border-left: 0; border-top: 1px solid var(--line); }
  .cell .label { display: block; }
}"""

SCRIPT = r"""(function () {
  var PREFIX = 'board-open:';
  var DETAIL = 'board-detail';
  var current = null;
  var shown = '';
  function load(key) { try { return window.localStorage.getItem(PREFIX + key); } catch (e) { return null; } }
  function save(key, open) { try { window.localStorage.setItem(PREFIX + key, open ? '1' : '0'); } catch (e) {} }
  function apply(el, open) {
    el.setAttribute('aria-expanded', open ? 'true' : 'false');
    var target = document.getElementById(el.getAttribute('aria-controls'));
    if (target) { target.hidden = !open; }
    var holder = document.getElementById(el.getAttribute('data-class-target'));
    if (holder) { holder.classList.toggle(el.getAttribute('data-class'), open); }
  }
  function restore() {
    var toggles = document.querySelectorAll('[data-toggle]');
    for (var i = 0; i < toggles.length; i++) {
      var stored = load(toggles[i].getAttribute('data-toggle'));
      if (stored === '1' || stored === '0') { apply(toggles[i], stored === '1'); }
    }
  }
  function copied(btn, text) {
    btn.textContent = text;
    setTimeout(function () { btn.textContent = 'Copy'; }, 1500);
  }
  function mark() {
    var items = document.querySelectorAll('[data-detail]');
    for (var i = 0; i < items.length; i++) {
      items[i].classList.toggle('selected', items[i].getAttribute('data-detail') === current);
    }
  }
  function fill(key) {
    var body = document.getElementById('panel-body');
    var cut = key.indexOf(':');
    var url = '/detail?kind=' + encodeURIComponent(key.slice(0, cut)) + '&id=' + encodeURIComponent(key.slice(cut + 1));
    fetch(url, { cache: 'no-store' }).then(function (r) { return r.text(); }).then(
      function (html) { if (current === key && body && html !== shown) { body.innerHTML = html; shown = html; } },
      function () { if (current === key && body) { body.innerHTML = '<p class="pmeta">The details could not be read.</p>'; shown = ''; } });
  }
  function openDetail(key) {
    var panel = document.getElementById('panel');
    if (!panel) { return; }
    if (current !== key) { document.getElementById('panel-body').innerHTML = '<p class="pmeta">Loading…</p>'; shown = ''; }
    current = key;
    panel.hidden = false;
    mark();
    fill(key);
    try { window.localStorage.setItem(DETAIL, key); } catch (e) {}
  }
  function closeDetail() {
    var panel = document.getElementById('panel');
    current = null;
    if (panel) { panel.hidden = true; }
    mark();
    try { window.localStorage.removeItem(DETAIL); } catch (e) {}
  }
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-copy]');
    if (btn) {
      if (!navigator.clipboard) { copied(btn, 'Copy failed'); return; }
      navigator.clipboard.writeText(btn.getAttribute('data-copy')).then(
        function () { copied(btn, 'Copied'); },
        function () { copied(btn, 'Copy failed'); });
      return;
    }
    if (ev.target.closest('[data-close]')) { closeDetail(); return; }
    var item = ev.target.closest('[data-detail]');
    if (item) {
      var key = item.getAttribute('data-detail');
      if (key === current) { closeDetail(); } else { openDetail(key); }
      return;
    }
    var el = ev.target.closest('[data-toggle]');
    if (el) {
      var open = el.getAttribute('aria-expanded') !== 'true';
      apply(el, open);
      save(el.getAttribute('data-toggle'), open);
      return;
    }
    if (current && !ev.target.closest('#panel, a, button')) { closeDetail(); }
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && current) { closeDetail(); return; }
    var item = ev.target.closest ? ev.target.closest('.card[data-detail]') : null;
    if (item && item === ev.target && (ev.key === 'Enter' || ev.key === ' ')) {
      ev.preventDefault();
      item.click();
    }
  });
  function refresh() {
    if (document.hidden) { return; }
    fetch(window.location.href, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) { throw new Error('HTTP ' + r.status); }
      return r.text();
    }).then(function (text) {
      var doc = new DOMParser().parseFromString(text, 'text/html');
      var script = document.body.querySelector(':scope > script');
      var olds = document.body.querySelectorAll(':scope > :not(script):not([data-keep])');
      for (var i = 0; i < olds.length; i++) { olds[i].remove(); }
      var news = doc.body.querySelectorAll(':scope > :not(script):not([data-keep])');
      for (var j = 0; j < news.length; j++) { document.body.insertBefore(document.importNode(news[j], true), script); }
      document.title = doc.title;
      restore();
      mark();
      if (current) { fill(current); }
    }).catch(function () {});
  }
  restore();
  var stored = null;
  try { stored = window.localStorage.getItem(DETAIL); } catch (e) {}
  if (stored) { openDetail(stored); }
  setInterval(refresh, 30000);
  document.addEventListener('visibilitychange', refresh);
})();"""

COLUMNS = [
    ("planned", "Planned", '<span class="stage"><b class="done">Done:</b> Story Planned</span><span class="stage"><b class="next">Next:</b> Story / Plan Written</span>'),
    ("backlog", "Backlog", '<span class="stage"><b class="done">Done:</b> Story / Plan Written</span><span class="stage"><b class="next">Next:</b> Plan Approval / Build</span>'),
    ("in-progress", "In Progress", '<span class="stage"><b class="now">Now:</b> Build Writing Code</span><span class="stage"><b class="next">Next:</b> Code Review</span>'),
    ("review", "Review", '<span class="stage"><b class="now">Now:</b> Code Review</span><span class="stage"><b class="next">Next:</b> Sign-off</span>'),
    ("done", "Done", '<span class="stage"><b class="done">Done:</b> Signed Off</span><span class="stage"><b class="next">Next:</b> Optional PR / Walkthrough</span>'),
]
SUB = {state: sub for state, _, sub in COLUMNS}
STATES = [c[0] for c in COLUMNS]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------- finding things


def find_tickets_py() -> Path | None:
    direct = REPO_ROOT / TICKETS_REL
    if direct.is_file():
        return direct
    for base in (REPO_ROOT / ".agents", REPO_ROOT / ".claude", REPO_ROOT / "_bmad"):
        if base.is_dir():
            for hit in sorted(base.rglob("tickets.py")):
                if "bmad-agent-po" in hit.parts:
                    return hit
    return None


def active_initiative_name() -> str | None:
    """core.active_initiative from the BMad config files, the user's own file winning."""
    name = None
    for path in (REPO_ROOT / "_bmad/config.toml", REPO_ROOT / "_bmad/custom/config.user.toml"):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        core = data.get("core")
        if isinstance(core, dict) and isinstance(core.get("active_initiative"), str) and core["active_initiative"].strip():
            name = core["active_initiative"].strip()
    return name


def find_folder(flag: str | None) -> Path:
    if flag:
        folder = Path(flag)
        if not folder.is_absolute():
            folder = (Path.cwd() / folder) if (Path.cwd() / folder).is_dir() else (REPO_ROOT / "_bmad-output" / flag)
        if not folder.is_dir():
            sys.exit(f"Initiative folder not found: {flag}")
        return folder.resolve()
    found = sorted(p for p in (REPO_ROOT / "_bmad-output").glob("initiative-*") if p.is_dir())
    if len(found) == 1:
        return found[0].resolve()
    if not found:
        sys.exit("No initiative-* folder under _bmad-output/. Pass --folder <initiative folder>.")
    active = active_initiative_name()
    for p in found:
        if p.name == active:
            return p.resolve()
    sys.exit("More than one initiative-* folder under _bmad-output/ and no active one set. Pass --folder <initiative folder>.")


def initiative_name(folder: Path) -> str:
    stem = folder.name.removeprefix("initiative-")
    return " ".join(w.capitalize() for w in stem.replace("-", " ").split())


def epic_titles(folder: Path) -> dict[str, str]:
    try:
        data = tomllib.loads((folder / "tickets" / "tickets.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    out = {}
    for e in data.get("epic", []) or []:
        if isinstance(e, dict) and e.get("slug") and e.get("title"):
            out[str(e["slug"])] = str(e["title"])
    return out


# ---------------------------------------------------------------- reading tickets.py


def run_tickets(tickets: Path | None, args: list[str]) -> tuple[dict | None, str | None]:
    """(json, None) or (None, plain-words error). Never raises."""
    label = "tickets.py " + " ".join(a if not a.startswith("/") else Path(a).name for a in args)
    if tickets is None:
        return None, "The BMad ticket tool (tickets.py) was not found in this repo."
    try:
        proc = subprocess.run(
            ["uv", "run", "--quiet", str(tickets), "--project-root", str(REPO_ROOT), *args],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        return None, "uv is not installed or not on the PATH, so tickets.py could not run."
    except subprocess.TimeoutExpired:
        return None, f"{label} took longer than 60 seconds and was stopped."
    except OSError as e:
        return None, f"{label} could not run: {e}"
    if proc.returncode != 0:
        lines = [l for l in (proc.stderr or proc.stdout or "").strip().splitlines() if l.strip()]
        detail = lines[-1] if lines else f"exit code {proc.returncode}"
        return None, f"{label} failed: {detail}"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, f"{label} did not print JSON."
    if not isinstance(data, dict):
        return None, f"{label} printed JSON that is not an object."
    return data, None


# ---------------------------------------------------------------- drawing


def card(t: dict, *, badge: str = "", why: str = "", show_ref: bool = True, copy: bool = True) -> str:
    """A ticket card. show_ref=False is a Backlog Folder card (no ref, title-only copy, backlog: detail)."""
    classes = ["card"]
    if t.get("risk") in ("high", "medium", "low"):
        classes.append(f"risk-{t['risk']}")
    if badge:
        classes.append("ready")
    ref = str(t.get("ref", ""))
    title = str(t.get("title", ""))
    detail = f"story:{ref}" if show_ref else f"backlog:{t.get('file') or ''}"
    head = ""
    if show_ref:
        head += f'<span class="ref">{esc(ref)}</span>'
    if t.get("type") == "spike":
        head += ' <span class="tag">spike</span>'
    if t.get("hitl") is True:
        head += ' <span class="star" title="hitl">★</span>'
    if badge:
        head += f'<span class="pill">{esc(badge)}</span>'
    if not show_ref:
        head = head.lstrip(" ")
    lines = [f'<div class="{" ".join(classes)}" data-detail="{esc(detail)}" tabindex="0">', f'  <div class="head">{head}</div>', f'  <div class="ttl">{esc(title)}</div>']
    if why:
        lines.append(f'  <div class="why">{esc(why)}</div>')
    if copy:
        text = f"{ref} {title}" if show_ref else title
        lines.append(f'  <button type="button" class="copy" data-copy="{esc(text)}" aria-label="{esc("Copy " + text)}">Copy</button>')
    lines.append("</div>")
    return "\n".join(lines)


def toggle_row(key: str, label: str, sub: str, cards: list[str], start_open: bool) -> str:
    expanded = "true" if start_open else "false"
    hidden = "" if start_open else " hidden"
    return (
        '<div class="trow">\n'
        f'  <button type="button" class="toggle" data-toggle="{key}" aria-controls="tg-{key}" aria-expanded="{expanded}">\n'
        f'    <span class="caret" aria-hidden="true"></span><span class="label">{label} · {len(cards)}</span><span class="sub">{sub}</span>\n'
        "  </button>\n"
        f'  <div id="tg-{key}"{hidden}><div class="cardgrid">{"".join(cards)}</div></div>\n'
        "</div>"
    )


def page_head(name: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(name)}</title><style>{CSS}</style></head>\n"
        "<body>\n"
    )


PANEL = (
    '<aside class="panel" id="panel" data-keep hidden aria-label="Details">\n'
    '  <button type="button" class="pclose" data-close aria-label="Close">×</button>\n'
    '  <div id="panel-body"></div>\n'
    "</aside>\n"
)


def page_tail() -> str:
    return PANEL + f"<script>{SCRIPT}</script>\n</body></html>\n"


def header(name: str, meta: str) -> str:
    return (
        '<header class="top">\n'
        f'  <h1><span class="kicker">Initiative</span>{esc(name)}</h1>\n'
        f'  <div class="meta">{meta}</div>\n'
        "</header>\n"
    )


def why_blocked(t: dict, epic_num: dict[str, object], epic_title: dict[str, str]) -> str:
    pieces = []
    waits = []
    own = epic_num.get(t.get("epic", ""), "?")
    for w in t.get("waiting_on") or []:
        w = str(w)
        if w in epic_num:
            waits.append(f"epic {epic_num[w]} ({epic_title.get(w, w)})")
        elif "." not in w:
            waits.append(f"{own}.{w}")
        else:
            waits.append(w)
    if waits:
        pieces.append("waits on " + " · ".join(waits))
    if t.get("blocked_reason"):
        pieces.append(str(t["blocked_reason"]))
    if t.get("unknown"):
        pieces.append(f"question to settle: {t['unknown']}")
    return " · ".join(pieces)


def render(folder: Path, tickets: Path | None) -> str:
    name = initiative_name(folder)
    now = datetime.now()
    date = f"{now:%A} {now.day} {now:%B %Y}"
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_status = pool.submit(run_tickets, tickets, ["status", str(folder)])
        f_next = pool.submit(run_tickets, tickets, ["next", str(folder)])
        f_back = pool.submit(run_tickets, tickets, ["next", "backlog"])
        status, status_err = f_status.result()
        nxt, next_err = f_next.result()
        back, back_err = f_back.result()

    if status is None:
        meta = f"{esc(date)} · status read at {now:%H:%M:%S}"
        return page_head(name) + header(name, meta) + f'<div class="err">{esc(status_err)}</div>\n' + page_tail()

    all_tickets = [t for t in status.get("tickets", []) if isinstance(t, dict)]
    epics = [e for e in status.get("epics", []) if isinstance(e, dict)]
    titles = epic_titles(folder)
    epic_num = {str(e.get("slug")): e.get("id") for e in epics}
    epic_title = {slug: titles.get(slug, slug) for slug in epic_num}
    counts = status.get("counts") or {}
    counts_line = " · ".join(f"{int(counts.get(s, 0) or 0)} {label}" for s, label, _ in COLUMNS)
    meta = f"{esc(date)} · {esc(counts_line)} · status read at {now:%H:%M:%S}"

    # badges and order, all from next
    badges: dict[str, str] = {}
    rank: dict[str, int] = {}
    if nxt is not None:
        for i, t in enumerate(nxt.get("ready_to_start") or [], 1):
            badges.setdefault(str(t.get("ref")), f"READY · {i}")
        for i, t in enumerate(nxt.get("ready_to_refine") or [], 1):
            badges.setdefault(str(t.get("ref")), f"READY · refine {i}")
        for group in ("ready_to_start", "ready_to_refine", "in_progress", "blocked"):
            for t in nxt.get(group) or []:
                rank.setdefault(str(t.get("ref")), len(rank))

    # Next Up
    nu = ['<section class="nextup">', "  <h2>Next Up</h2>"]
    nothing_can_start = False
    if nxt is None:
        nu.append(f'  <div class="err">What\'s next could not be read. {esc(next_err)}</div>')
    else:
        if any(nxt.get(k) for k in ("unpinned_after", "undeclared_after", "order_conflict", "problems")):
            nu.append('  <div class="warn">The ticket tree needs fixing; ask Sofia.</div>')
        start = nxt.get("ready_to_start") or []
        if start:
            first = card(start[0], badge=badges.get(str(start[0].get("ref")), ""))
        else:
            nothing_can_start = True
            first = '<div class="card">\n  <div class="head"></div>\n  <div class="ttl">Nothing can start now</div>\n</div>'
        nu.append(f'  <div class="start"><p class="label">Start next</p><div class="cardgrid">{first}</div></div>')
        if start[1:]:
            cards = "".join(card(t, badge=badges.get(str(t.get("ref")), "")) for t in start[1:])
            nu.append(f'  <div class="group"><p class="label">Then</p><div class="cardgrid">{cards}</div></div>')
        refine = nxt.get("ready_to_refine") or []
        if refine:
            cards = "".join(card(t, badge=badges.get(str(t.get("ref")), "")) for t in refine)
            nu.append(f'  <div class="group"><p class="label">Needs refining first</p><div class="cardgrid">{cards}</div></div>')
        prog = nxt.get("in_progress") or []
        if prog:
            cards = "".join(card(t, why=str(t.get("assignee") or "")) for t in prog)
            nu.append(f'  <div class="group"><p class="label">In Progress</p><div class="cardgrid">{cards}</div></div>')
        blocked = nxt.get("blocked") or []
        if blocked:
            cards = [card(t, why=why_blocked(t, epic_num, epic_title)) for t in blocked]
            nu.append("  " + toggle_row("blocked", "Blocked", "(Can't Start Yet)", cards, nothing_can_start).replace("\n", "\n  "))
    if back is None:
        nu.append(f'  <div class="trow"><span class="label">Backlog Folder</span><span class="sub">(Parking Lot · No Epic Yet)</span><p class="sub">The Backlog Folder could not be read. {esc(back_err)}</p></div>')
    else:
        rows = (back.get("ready_to_start") or []) + (back.get("ready_to_refine") or [])
        if rows:
            cards = [card(t, show_ref=False) for t in rows]
            nu.append("  " + toggle_row("backlog-folder", "Backlog Folder", "(Parking Lot · No Epic Yet)", cards, False).replace("\n", "\n  "))
    nu.append("</section>")

    # board
    col_counts = {s: 0 for s in STATES}
    epic_blocks = []
    for e in epics:
        slug = str(e.get("slug", ""))
        eid = e.get("id", "")
        mine = [t for t in all_tickets if t.get("epic") == slug]
        dropped = [t for t in mine if t.get("state") == "dropped"]
        counted = [t for t in mine if t.get("state") != "dropped"]
        n_done = sum(1 for t in counted if t.get("state") == "done")
        drop_note = f" · {len(dropped)} dropped" if dropped else ""
        is_done = e.get("status") == "done"
        title = epic_title.get(slug, slug)
        if is_done:
            band = (
                f'<button type="button" class="band toggle" data-toggle="epic-{esc(slug)}" aria-controls="tg-epic-{esc(slug)}" aria-expanded="false">'
                f'<span class="caret" aria-hidden="true"></span><span class="ekicker">Epic {esc(eid)}</span><span class="etitle">{esc(title)}</span>'
                f'<span class="done">DONE{esc(drop_note)}</span><span class="bar"><span style="width:100%"></span></span></button>'
            )
        else:
            pct = round(100 * n_done / len(counted)) if counted else 0
            band = (
                f'<div class="band"><span class="caret-space"></span><span class="ekicker">Epic {esc(eid)}</span><span class="etitle">{esc(title)}</span>'
                f'<span class="done">{esc(f"{n_done}/{len(counted)} done{drop_note}")}</span><span class="bar"><span style="width:{pct}%"></span></span></div>'
            )
        cells = []
        for s, label, sub in COLUMNS:
            in_col = [t for t in counted if t.get("state") == s]
            col_counts[s] += len(in_col)
            if s != "done":
                build = {id(t): i for i, t in enumerate(in_col)}
                in_col.sort(key=lambda t: (rank.get(str(t.get("ref")), len(rank) + build[id(t)]),))
            cards = "".join(card(t, badge=badges.get(str(t.get("ref")), "")) for t in in_col)
            if s == "done":
                summary = f'<div class="done-summary">{len(in_col)} done</div>' if in_col else ""
                cells.append(f'        <div class="cell" data-state="done"><p class="label">Done<br><span class="sub">{SUB["done"]}</span></p>{summary}{cards}</div>')
            else:
                cells.append(f'        <div class="cell" data-state="{s}"><p class="label">{label}<br><span class="sub">{sub}</span></p>{cards}</div>')
        others = [t for t in counted if t.get("state") not in STATES]
        other_line = ""
        if others:
            items = ", ".join(f"{t.get('ref', '')} {t.get('title', '')} ({t.get('state', '')})" for t in others)
            other_line = f'      <div class="other">Other states: {esc(items)}</div>\n'
        hidden = " hidden" if is_done else ""
        epic_blocks.append(
            f'  <div class="epic" data-epic="{esc(slug)}" data-num="{esc(eid)}">\n'
            f"    {band}\n"
            f'    <button type="button" class="edetail" data-detail="epic:{esc(slug)}">Details</button>\n'
            f'    <div id="tg-epic-{esc(slug)}" class="ebody"{hidden}>\n'
            '      <div class="cells">\n' + "\n".join(cells) + "\n      </div>\n"
            + other_line
            + "    </div>\n"
            "  </div>"
        )

    board = (
        '<section class="board" id="board">\n'
        '  <div class="cols">\n'
        f'    <div class="colhead"><p class="label">Planned · {col_counts["planned"]}</p><div class="sub">{SUB["planned"]}</div></div>\n'
        f'    <div class="colhead"><p class="label">Backlog · {col_counts["backlog"]}</p><div class="sub">{SUB["backlog"]}</div></div>\n'
        f'    <div class="colhead"><p class="label">In Progress · {col_counts["in-progress"]}</p><div class="sub">{SUB["in-progress"]}</div></div>\n'
        f'    <div class="colhead"><p class="label">Review · {col_counts["review"]}</p><div class="sub">{SUB["review"]}</div></div>\n'
        f'    <button type="button" class="colhead toggle" data-toggle="done-column" data-class-target="board" data-class="done-open" aria-expanded="false"><p class="label"><span class="caret" aria-hidden="true"></span>Done · {col_counts["done"]}</p><div class="sub">{SUB["done"]}</div></button>\n'
        "  </div>\n"
        + "\n".join(epic_blocks)
        + "\n</section>\n"
    )

    chain = [str(c) for c in status.get("longest_remaining_chain") or []]
    chain_text = f"{' → '.join(chain)} ({len(chain)} {'story' if len(chain) == 1 else 'stories'})" if chain else "none"
    footer = (
        "<footer>\n"
        '  <div class="key">\n'
        "    <span><b>Planned</b>Story planned in the epic; no story or plan file yet</span>\n"
        "    <span><b>Backlog</b>Story or plan written; you approve the plan here, then the build writes code</span>\n"
        "    <span><b>In Progress</b>The build is writing code; its code review comes next</span>\n"
        "    <span><b>Review</b>Code review, then your sign-off</span>\n"
        "    <span><b>Done</b>Signed off; a pull request or a walkthrough (bmad-walkthrough) can follow, both optional</span>\n"
        "    <span><b>READY · n</b>Can start now; n is its place in Next Up</span>\n"
        "    <span><b>★</b>Needs you</span>\n"
        '    <span><b>Risk</b><i class="sw risk-high"></i>High<i class="sw risk-medium"></i>Medium<i class="sw risk-low"></i>Low</span>\n'
        "  </div>\n"
        f"  <p>Longest chain still to build: {esc(chain_text)}</p>\n"
        "</footer>\n"
    )

    return page_head(name) + header(name, meta) + "\n" + "\n".join(nu) + "\n\n" + board + "\n" + footer + page_tail()


# ---------------------------------------------------------------- details panel

NOT_FOUND = '<p class="pmeta">That item is not on the board now.</p>'


def error_fragment(err: str) -> str:
    return f'<p class="pmeta">The details could not be read. {esc(err)}</p>'


def read_text(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def split_frontmatter(text: str) -> tuple[list[str], list[str]]:
    """(frontmatter lines, body lines). Frontmatter is the block between the first two `---` lines,
    when the file opens with one."""
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].strip() == "---":
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == "---":
                return lines[i + 1:j], lines[j + 1:]
    return [], lines


def fm_value(fm: list[str], key: str) -> str:
    """A simple line match, not YAML: `key: value`, surrounding quotes dropped."""
    pat = re.compile(rf"^{re.escape(key)}\s*:\s*(.*?)\s*$")
    for line in fm:
        m = pat.match(line)
        if m:
            v = m.group(1)
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            return v
    return ""


def paragraphs(lines: list[str]) -> list[str]:
    out, cur = [], []
    for line in lines:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def section(body: list[str], name: str) -> list[str]:
    """Paragraphs of the `## name` section: its text runs to the next heading."""
    pat = re.compile(rf"^##\s+{re.escape(name)}\s*$")
    for i, line in enumerate(body):
        if pat.match(line.strip()):
            out = []
            for nxt in body[i + 1:]:
                if nxt.lstrip().startswith("#"):
                    break
                out.append(nxt)
            return paragraphs(out)
    return []


def verify_text(body: list[str]) -> str:
    """The text after `Verify:`, to the end of its paragraph."""
    for i, line in enumerate(body):
        s = line.strip()
        if s.startswith("Verify:"):
            parts = [s[len("Verify:"):].strip()]
            for nxt in body[i + 1:]:
                if not nxt.strip() or nxt.lstrip().startswith("#"):
                    break
                parts.append(nxt.strip())
            return " ".join(p for p in parts if p)
    return ""


_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def inline(text: str) -> str:
    """HTML-escape, then **x** -> bold, `x` -> code, [text](link) -> text. Code spans are left alone."""
    out = []
    pos = 0
    for m in _CODE.finditer(text):
        out.append(_plain(text[pos:m.start()]))
        out.append(f"<code>{esc(m.group(1))}</code>")
        pos = m.end()
    out.append(_plain(text[pos:]))
    return "".join(out)


def _plain(text: str) -> str:
    s = esc(text)
    s = _LINK.sub(lambda m: m.group(1), s)
    return _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", s)


def file_link(path: Path, label: str) -> str:
    # vscode://file/<absolute path>; the path's own leading / is the one after "file".
    url = "vscode://file/" + quote(str(path).lstrip("/"), safe="/")
    return f'<li><a href="{esc(url)}">{label}</a></li>'


def fragment(kind_line: str, title: str, risk: str, meta: list[str], sections: list[str]) -> str:
    lines = [f'<p class="pkind">{esc(kind_line)}</p>', f'<h2 class="ptitle">{esc(title)}</h2>']
    if meta or risk:
        sw = f'<i class="sw risk-{risk}"></i>' if risk else ""
        lines.append(f'<p class="pmeta">{sw}{esc(" · ".join(meta))}</p>')
    lines.extend(s for s in sections if s)
    return "\n".join(lines) + "\n"


def sec_paras(heading: str, paras: list[str]) -> str:
    if not paras:
        return ""
    return f'<section class="psec"><h3>{heading}</h3>' + "".join(f"<p>{inline(p)}</p>" for p in paras) + "</section>"


def sec_list(heading: str, items: list[str]) -> str:
    if not items:
        return ""
    return f'<section class="psec"><h3>{heading}</h3><ul>' + "".join(items) + "</ul></section>"


def risk_of(value) -> str:
    v = str(value or "").strip().lower()
    return v if v in ("high", "medium", "low") else ""


def toml_entry(path: Path, entry_id) -> dict:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
    for e in data.get("entry", []) or []:
        if isinstance(e, dict) and str(e.get("id")) == str(entry_id):
            return e
    return {}


def find_plan(leaves: Path, entry_id, story_stem: str | None) -> Path | None:
    wanted = {str(entry_id)}
    if story_stem:
        wanted.add(story_stem)
    for p in sorted(leaves.glob("*-plan.md")):
        text = read_text(p)
        if text is None:
            continue
        fm, _ = split_frontmatter(text)
        if fm_value(fm, "ticket") in wanted:
            return p
    return None


def find_walkthrough(folder: Path, epic_id, n) -> Path | None:
    for d in sorted(folder.glob(f"walkthrough-{epic_id}-{n}-*")):
        f = d / f"{d.name}.md"
        if d.is_dir() and f.is_file():
            return f
    return None


def detail_story(folder: Path, status: dict, ref: str) -> tuple[int, str]:
    tickets = [t for t in status.get("tickets", []) if isinstance(t, dict)]
    row = next((t for t in tickets if str(t.get("ref")) == ref and t.get("state") != "dropped"), None)
    epics = {str(e.get("slug")): e for e in status.get("epics", []) if isinstance(e, dict)}
    if row is None or str(row.get("epic")) not in epics:
        return 404, NOT_FOUND
    epic = epics[str(row["epic"])]
    eid = epic.get("id", "")
    titles = epic_titles(folder)
    leaves = folder / "tickets" / str(epic.get("folder") or epic.get("slug")) / "tickets"
    story = leaves / str(row["file"]) if row.get("file") else None
    if story is not None and (Path(str(row["file"])).name != str(row["file"]) or not story.is_file()):
        story = None
    entry = toml_entry(leaves / "tickets.toml", row.get("id"))

    risk = risk_of(row.get("risk"))
    meta = []
    if risk:
        meta.append(f"Risk: {risk}")
    if row.get("hitl") is True:
        meta.append("Needs you")
    if str(row.get("assignee") or "").strip():
        meta.append(f"Assignee: {row['assignee']}")

    if story is not None:
        _, body = split_frontmatter(read_text(story) or "")
        what = section(body, "Description")
        verify = verify_text(body) or str(entry.get("verify") or "").strip()
    else:
        what = paragraphs(str(entry.get("description") or "").splitlines())
        verify = str(entry.get("verify") or "").strip()

    by_ref = {str(t.get("ref")): str(t.get("title", "")) for t in tickets}
    waits = []
    for a in row.get("after") or []:
        a = str(a)
        if a in epics:
            text = f"Epic {epics[a].get('id', '?')} ({titles.get(a, a)})"
            waits.append(f"<li>{esc(text)}</li>")
            continue
        r = a if "." in a else f"{eid}.{a}"
        name = by_ref.get(r)
        waits.append(f"<li>{esc(f'{r} {name}' if name else r)}</li>")

    plan = find_plan(leaves, row.get("id"), story.stem if story is not None else None)
    plan_ps = []
    if plan is not None:
        _, pbody = split_frontmatter(read_text(plan) or "")
        for label in ("Problem", "Approach"):
            marker = f"**{label}:**"
            for p in section(pbody, "Intent"):
                if p.startswith(marker):
                    plan_ps.append(f"<p><b>{label}:</b> {inline(p[len(marker):].strip())}</p>")
                    break
    plan_sec = '<section class="psec"><h3>Build plan</h3>' + "".join(plan_ps) + "</section>" if plan_ps else ""

    files = []
    if story is not None:
        files.append(file_link(story, "Story file"))
    if plan is not None:
        files.append(file_link(plan, "Build plan"))
    walk = find_walkthrough(folder, eid, row.get("id"))
    if walk is not None:
        files.append(file_link(walk, "Walkthrough"))
    if story is None and (leaves / "tickets.toml").is_file():
        files.append(file_link(leaves / "tickets.toml", "Epic's ticket list"))

    kind = str(row.get("type") or "story").strip().capitalize() or "Story"
    sections = [
        sec_paras("What it is", what),
        sec_paras("How we'll know it's done", [verify] if verify else []),
        sec_list("Waits on", waits),
        sec_paras("Blocked because", [str(row.get("blocked_reason") or "").strip()] if str(row.get("blocked_reason") or "").strip() else []),
        sec_paras("Question to settle", [str(row.get("unknown") or "").strip()] if str(row.get("unknown") or "").strip() else []),
        plan_sec,
        sec_list("Files (open in VS Code)", files),
    ]
    return 200, fragment(f"{kind} {ref}", str(row.get("title", "")), risk, meta, sections)


def detail_epic(folder: Path, status: dict, slug: str) -> tuple[int, str]:
    epic = next((e for e in status.get("epics", []) if isinstance(e, dict) and str(e.get("slug")) == slug), None)
    if epic is None:
        return 404, NOT_FOUND
    title = epic_titles(folder).get(slug, slug)
    efolder = folder / "tickets" / str(epic.get("folder") or slug)
    efile = efolder / f"{slug}.md"
    retro = efolder / f"{slug}-retrospective.md"
    text = read_text(efile) if efile.is_file() else None
    fm, body = split_frontmatter(text or "")
    risk = risk_of(fm_value(fm, "risk"))
    mine = [t for t in status.get("tickets", []) if isinstance(t, dict) and t.get("epic") == slug]
    dropped = sum(1 for t in mine if t.get("state") == "dropped")
    counted = [t for t in mine if t.get("state") != "dropped"]
    n_done = sum(1 for t in counted if t.get("state") == "done")
    progress = f"{n_done} of {len(counted)} done" + (f" · {dropped} dropped" if dropped else "")
    files = []
    if text is not None:
        files.append(file_link(efile, "Epic file"))
    if retro.is_file():
        files.append(file_link(retro, "Retrospective"))
    sections = [
        sec_paras("What it is", section(body, "Description")),
        sec_paras("What it gives you", section(body, "Outcome")),
        sec_paras("Progress", [progress]),
        sec_list("Files (open in VS Code)", files),
    ]
    return 200, fragment(f"Epic {epic.get('id', '')}", title, risk, [f"Risk: {risk}"] if risk else [], sections)


def detail_backlog(folder: Path, name: str) -> tuple[int, str]:
    backlog = folder.parent / "backlog"
    if (not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name
            or name.startswith(".") or Path(name).name != name or not name.endswith(".md")):
        return 404, NOT_FOUND
    path = backlog / name
    if not path.is_file():
        return 404, NOT_FOUND
    text = read_text(path)
    if text is None:
        return 500, error_fragment(f"{name} could not be read.")
    fm, body = split_frontmatter(text)
    kind = (fm_value(fm, "type") or "story").capitalize()
    risk = risk_of(fm_value(fm, "risk"))
    meta = []
    if risk:
        meta.append(f"Risk: {risk}")
    if fm_value(fm, "hitl").lower() == "true":
        meta.append("Needs you")
    verify = verify_text(body)
    sections = [
        sec_paras("What it is", section(body, "Description")),
        sec_paras("How we'll know it's done", [verify] if verify else []),
        sec_list("Files (open in VS Code)", [file_link(path, "Ticket file")]),
    ]
    return 200, fragment(f"Backlog Folder · {kind}", fm_value(fm, "title"), risk, meta, sections)


def render_detail(folder: Path, tickets: Path | None, query: str) -> tuple[int, str]:
    q = parse_qs(query, keep_blank_values=True)
    kind = (q.get("kind") or [""])[0]
    ident = (q.get("id") or [""])[0]
    if kind == "backlog":
        return detail_backlog(folder, ident)
    if kind not in ("story", "epic") or not ident:
        return 404, NOT_FOUND
    status, err = run_tickets(tickets, ["status", str(folder)])
    if status is None:
        return 500, error_fragment(err or "")
    if kind == "story":
        return detail_story(folder, status, ident)
    return detail_epic(folder, status, ident)


# ---------------------------------------------------------------- serving


def make_handler(folder: Path, tickets: Path | None):
    class Handler(BaseHTTPRequestHandler):
        def send_body(self, code: int, body: bytes):
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header(BOARD_HEADER, BOARD_ID)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == BOARD_PATH:  # --start and --stop ask here which project's board this is
                self.send_body(200, b"board")
                return
            if url.path == "/detail":
                try:
                    code, frag = render_detail(folder, tickets, url.query)
                except Exception as e:  # never crash the server
                    code, frag = 500, error_fragment(str(e))
                self.send_body(code, frag.encode("utf-8"))
                return
            if url.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            try:
                body = render(folder, tickets).encode("utf-8")
                code = 200
            except Exception as e:  # never crash the server; say what went wrong on the page
                name = initiative_name(folder)
                now = datetime.now()
                meta = f"{esc(f'{now:%A} {now.day} {now:%B %Y}')} · status read at {now:%H:%M:%S}"
                body = (page_head(name) + header(name, meta)
                        + f'<div class="err">The board could not be drawn: {esc(e)}</div>\n' + page_tail()).encode("utf-8")
                code = 200
            self.send_body(code, body)

        def do_POST(self):
            # --stop sends this. A web page cannot: the custom header needs a CORS preflight, which is refused.
            if urlparse(self.path).path != STOP_PATH or self.headers.get(STOP_HEADER) != "1":
                self.send_error(404)
                return
            self.send_body(200, STOP_REPLY)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, fmt, *args):
            pass

    return Handler


STOP_PATH = "/__stop"
STOP_HEADER = "X-Board-Stop"
STOP_REPLY = b"board stopping"
BOARD_PATH = "/__board"
BOARD_HEADER = "X-Board-Server"
BOARD_ID = quote(str(REPO_ROOT))  # each response says which project's board it is
DEFAULT_PORT = 8765
PORTS = range(DEFAULT_PORT, DEFAULT_PORT + 11)  # where --start looks for a free port and --stop looks for the board


def probe(port: int) -> str | None:
    """What answers on the port: "mine" (this project's board), "board" (another project's),
    "other", or None for nothing."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{BOARD_PATH}", timeout=3) as r:
            headers = r.headers
    except urllib.error.HTTPError as e:
        headers = e.headers
    except (OSError, urllib.error.URLError):
        return None
    found = headers.get(BOARD_HEADER)
    if found == BOARD_ID:
        return "mine"
    return "board" if found else "other"


def probe_all(ports) -> dict[int, str | None]:
    with ThreadPoolExecutor(max_workers=len(ports)) as ex:
        return dict(zip(ports, ex.map(probe, ports)))


def free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # as the server does, so a just-stopped port counts as free
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def taken(port: int, found: str | None) -> str:
    if found == "board":
        return f"Port {port} has a board for another project."
    return f"Port {port} is in use by something else."


def stop_one(port: int) -> int:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{STOP_PATH}", data=b"", method="POST", headers={STOP_HEADER: "1"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            reply = r.read()
    except (OSError, urllib.error.URLError):
        reply = b""
    if reply == STOP_REPLY:
        for _ in range(50):
            if probe(port) is None:
                print(f"Board on port {port} stopped.")
                return 0
            time.sleep(0.1)
    print(f"Asked the board on port {port} to stop, but it still answers.", file=sys.stderr)
    return 1


def stop(port: int | None) -> int:
    if port is not None:
        found = probe(port)
        if found is None:
            print(f"No board running on port {port}.")
            return 0
        if found != "mine":
            print(f"{taken(port, found)} Left it alone.", file=sys.stderr)
            return 1
        return stop_one(port)
    mine = [p for p, found in probe_all(PORTS).items() if found == "mine"]
    if not mine:
        print(f"No board for this project running on ports {PORTS[0]}-{PORTS[-1]}.")
        return 0
    return max(stop_one(p) for p in mine)


def start(args: argparse.Namespace, folder: Path) -> int:
    stop_cmd = "uv run scripts/board_server.py --stop" + ("" if args.port is None else f" --port {args.port}")
    ports = PORTS if args.port is None else [args.port]
    seen = probe_all(ports)
    running = [p for p in ports if seen[p] == "mine"]
    if running:
        url = f"http://127.0.0.1:{running[0]}/"
        print(f"A board is already running at {url}\nStop it with: {stop_cmd}")
        if not args.no_open:
            webbrowser.open(url)
        return 0
    port = next((p for p in ports if seen[p] is None and free(p)), None)
    if port is None:
        if args.port is not None:
            print(f"{taken(args.port, seen[args.port])} Pick another with --port.", file=sys.stderr)
        else:
            print(f"No free port between {PORTS[0]} and {PORTS[-1]}. Pick one with --port.", file=sys.stderr)
        return 1
    skipped = [p for p in ports if p < port]
    if skipped:
        print(" ".join(taken(p, seen[p]) for p in skipped) + f" Using {port}.")
    url = f"http://127.0.0.1:{port}/"
    log = Path(tempfile.gettempdir()) / f"bmad-board-{port}.log"
    cmd = [sys.executable, str(Path(__file__).resolve()), "--port", str(port), "--no-open", "--folder", str(folder)]
    detach = ({"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
              if sys.platform == "win32" else {"start_new_session": True})
    with open(log, "w") as out:
        child = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, **detach)
    for _ in range(100):
        if child.poll() is not None:
            print(log.read_text().strip() or f"The board exited before it started (code {child.returncode}).", file=sys.stderr)
            return 1
        if probe(port) == "mine":
            break
        time.sleep(0.1)
    else:
        print(f"The board did not answer within 10 seconds. Its output is in {log}", file=sys.stderr)
        return 1
    print(f"Board for {initiative_name(folder)} running at {url}\nStop it with: {stop_cmd}")
    if not args.no_open:
        webbrowser.open(url)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Live, read-only kanban board of this project's BMad tickets.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--start", action="store_true", help="run the board as its own process and return")
    mode.add_argument("--stop", action="store_true", help="stop this project's board")
    ap.add_argument("--port", type=int, help=f"port on 127.0.0.1 (default {DEFAULT_PORT}; --start and --stop "
                                             f"search {PORTS[0]}-{PORTS[-1]} when it is not given)")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    ap.add_argument("--folder", help="initiative folder (default: the initiative-* folder under _bmad-output/)")
    args = ap.parse_args()

    if args.stop:
        return stop(args.port)
    folder = find_folder(args.folder)
    if args.start:
        return start(args, folder)
    if args.port is None:
        args.port = DEFAULT_PORT
    tickets = find_tickets_py()
    if tickets is None:
        print("Warning: tickets.py not found; the page will say so.", file=sys.stderr)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(folder, tickets))
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"Port {args.port} is already in use. Stop whatever is using it, or pick another with --port.", file=sys.stderr)
            return 1
        print(f"Could not listen on 127.0.0.1:{args.port}: {e}", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Board for {initiative_name(folder)} at {url}  (Ctrl+C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
        print("Stopped.")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
