# Live kanban board — prompt

Paste everything below the line into Claude Code in any BMad project whose tickets are tracked with Sofia's `tickets.py`. It will be saved as `scripts/board_server.py`.

---

Build me a live kanban board of this project's epics and stories, served on localhost.

## What I want

- One command starts it: `uv run scripts/board_server.py` (put the script in this repo's own scripts folder, not inside _bmad/, which the BMad installer replaces).
- `--start` and `--stop` let me start and stop it with one command each, from a terminal or by asking Claude Code. A board started with `--start` keeps running after the terminal or Claude Code session that started it ends.
- It opens my browser at `http://127.0.0.1:<port>`. Every page load reads the current ticket status. Every 30 seconds the template's script fetches the page again and swaps in the new content without reloading, so nothing I have open or selected is lost.
- It only reads. It never changes a ticket.
- The top of the page answers "what's next?" with the same answer Sofia gives, because both read the same command.
- The page looks exactly like the Template section below. The prose says what goes in it; the template says how it looks.

## Where the status comes from

- Find the BMad ticket tool: `.agents/skills/bmad-agent-po/scripts/tickets.py` (search for it if it is elsewhere).
- Find the initiative folder: the `initiative-*` folder under `_bmad-output/` (if there is more than one, use the active one from the BMad config, or take a `--folder` flag).
- Get the status by running: `uv run <tickets.py> --project-root <repo root> status <initiative folder>`. It prints JSON with `tickets`, `epics`, `counts` and `longest_remaining_chain`.
- Get what's next by running: `uv run <tickets.py> --project-root <repo root> next <initiative folder>`. It prints JSON with `ready_to_refine`, `ready_to_start`, `in_progress` and `blocked`, each a list already in build order. A `blocked` row has `waiting_on` (the prerequisites not yet met), `blocked_reason`, or `unknown` (a question to settle first). The loose tickets outside the epics come from `next backlog` (same four lists): `next <initiative folder>` leaves them out, and only a bare `next` with no folder adds them under a `backlog` key.
- `status` gives no epic titles. Read each one from the `[[epic]]` title in `tickets/tickets.toml` inside the initiative folder; if that file cannot be read, use the epic's slug. This is a plain file read, not a tickets.py call.
- The initiative name is the folder name without `initiative-`, with dashes as spaces, in title case: `initiative-cutter-workflow-redesign` → "Cutter Workflow Redesign". It is also the browser tab title.
- Use each ticket's `state` exactly as given. Never work it out yourself.
- Never work out readiness or order yourself either. Take them from `next` exactly as given. (`next` counts a prerequisite as met when it is done or in review.)

## Header

- The INITIATIVE tag and the initiative name, then one line: today's date (for example "Tuesday 27 October 2026"), the column counts in column order ("12 Planned · 2 Backlog · 0 In Progress · 0 Review · 26 Done"), and "status read at HH:MM:SS". The counts equal the `counts` from `status`.

## Next Up (top of the page, above the board)

- "Start next": the first row of `ready_to_start`, as a card with "READY · 1". When `ready_to_start` is empty, the card says "Nothing can start now" and Blocked starts open.
- "Then": the rest of `ready_to_start`, in the order given, as cards with "READY · 2", "READY · 3"…, across all epics.
- "Needs refining first": `ready_to_refine`, in order, as cards with "READY · refine 1", "READY · refine 2"…, when not empty.
- "In Progress": `in_progress`, when not empty, as cards with the assignee (if any) on the `why` line.
- "Blocked", second line "(Can't Start Yet)": `blocked`, in order, as cards with what each waits on on the `why` line, in plain words: "waits on 2.19" from `waiting_on` (an entry without a dot is in the same epic, so show it with the epic's number, e.g. 19 in epic 2 → 2.19; an entry that names a whole epic by slug, e.g. `epic-batch-review`, shows as "epic 2" followed by the epic's title in brackets), or the `blocked_reason`, or "question to settle: …" from `unknown`; several are joined with " · ". This is BMad's word for these tickets. Shown only when not empty. Collapsed by default, with a count.
- "Backlog Folder", second line "(Parking Lot · No Epic Yet)": `ready_to_start` then `ready_to_refine` from `next backlog`, as cards without a ref (these tickets have none), when not empty. This is BMad's `backlog/` folder of tickets that belong to no epic; it is never the Backlog column. Collapsed by default, with a count. If `next backlog` fails, show the one-line message from the template.
- If `next` reports a non-empty `unpinned_after`, `undeclared_after`, `order_conflict` or `problems`, show the warning line "The ticket tree needs fixing; ask Sofia." The board still draws.
- If `next` fails, show the error line in place of Start next to Blocked; the Backlog Folder still shows.

## The board

- Columns are BMad's own ticket states, so a word on the board means exactly what it means to Sofia. Each heading has a count and, where given, a second line in brackets:

  | Column | Second line | Holds tickets whose `state` is | Footer key |
  | --- | --- | --- | --- |
  | Planned | (Epic List Only) | `planned`: only a line in the epic's `tickets.toml`; no story file and no build plan | Listed in the epic, not written up yet |
  | Backlog | (Story or Build Plan Written) | `backlog`: has a story file or a build plan, not started | Written up (story or build plan), not started |
  | In Progress | (Building) | `in-progress` | Being built |
  | Review | (Diff · Triage · Fix · Sign-off) | `review`: review agents read the diff (every change the build made, whatever kind of file), findings are triaged, fixed and re-checked, then it is built and waits for the owner's sign-off | Diff reviewed, findings triaged and fixed, waiting for your sign-off |
  | Done | none | `done` | Finished |

  - Write the headings, second lines and key text exactly as given here. A ticket's column is its `state` from `status`, unchanged. Never work it out yourself.
  - Whether a ticket can start is a separate thing, shown only by the READY badge and Next Up, both from `next`. A READY card can sit in Planned or Backlog.
- The Done heading is a toggle. Done cards start hidden; each epic's Done cell then shows only "n done" (nothing when n is 0). Clicking the heading shows the Done cards in every epic at once; clicking again hides them.
- One row per epic, in the order of `epics`. Its band shows "Epic n" (the epic's `id`), the epic's title, "n/m done" (or DONE when the epic's own `status` is `done`) and the progress bar (full on a DONE epic).
- A DONE epic starts collapsed: its band is a toggle and its cards are hidden. Epics that are not DONE are always open and their band is not a toggle.
- The browser remembers every toggle (DONE epics, the Done heading, Blocked, Backlog Folder) through the template's script, so the 30-second refresh never undoes what you opened or closed.
- Dropped tickets get no column: leave them off the board, add "· n dropped" to the epic label, and leave them out of m. Any other state not in the five columns goes on the "Other states" line under its epic, so no ticket silently disappears.
- One card per ticket: its `ref` (for example 2.9), its title, the risk class from its `risk` (high, medium or low; none if missing), "spike" for spikes, and ★ when `hitl` is true. Cards show no state text: the column says it.
- Every ticket card, on the board and in Next Up, has a Copy button that puts the ref and title on the clipboard ("2.14 The opening read is checked by a program"), ready to paste into Sofia or a build. A Backlog Folder card copies its title alone. The "Nothing can start now" card has no Copy button. The button shows when the pointer is over the card or the card has keyboard focus, and always on touch screens.
- Mark a card READY when its ref is in `next`'s `ready_to_start` or `ready_to_refine`, with the same badge text as in Next Up ("READY · 1", "READY · refine 1"…).
- Within each column, order the cards as `next` lists them: `ready_to_start`, then `ready_to_refine`, then `in_progress`, then `blocked`, each in the order given. READY cards therefore sit at the top, matching Next Up. `next` leaves out finished tickets, so the Done column keeps build order (the order `status` gives them, which is the order the stories are listed in the epic's plan). Build order is a dependency sequence, not a priority ranking. Any card `next` does not list goes after the listed ones, in build order.
- Every epic has a Details button at the right of its band (see Details panel).
- Footer: the key (the five column lines from the table, then "READY · n: Can start now; n is its place in Next Up", "★: Needs you", and the risk colour swatches), then "Longest chain still to build: 2.19 → … → 3.6 (9 stories)" from `longest_remaining_chain`, or "none".

## Details panel

Clicking a ticket card (on the board, in Next Up, in the Backlog Folder) or an epic's Details button opens a panel down the right-hand side with what that item is, in plain words. The board stays where it is.

- Opening and closing: click a card or Details to open it; click another to switch; click the same one again, press Esc, click the ×, or click empty page space to close. Cards open from the keyboard with Enter or Space. The open item is marked on the board. The browser remembers which item is open, so a reload reopens it. The 30-second refresh leaves the panel open and refreshes its content.
- The page asks the server for one item at a time: `GET /detail?kind=story&id=2.14`, `kind=epic&id=<epic slug>`, or `kind=backlog&id=<file name>`. The server answers with an HTML fragment from the Details template, reading only that item's files. An unknown kind or id, or a backlog id that is not a plain file name in the `backlog/` folder, gets the not-found fragment (status 404). If tickets.py fails, the fragment is the one error line.
- Never show a file's frontmatter, raw state words or plan fields. Only the parts listed here, under the plain-English headings in the template. Show text with HTML escaped; then `**x**` becomes bold and `` `x` `` becomes code; `[text](link)` shows as its text.

What goes in each kind (a section appears only when it has text):

| Section | Story (ticket on the board) | Epic | Backlog Folder ticket |
| --- | --- | --- | --- |
| Kind line | Type and ref: "Story 2.14", "Spike 3.2", "Bug 1.4" | "Epic n" | "Backlog Folder · Story" (or Bug, Spike…) |
| Title | `title` from `status` | the epic's title | `title` from the file's frontmatter |
| Meta line | "Risk: high", "Needs you" when `hitl`, "Assignee: x" when set, joined with " · " | "Risk: x" from the epic file's frontmatter | "Risk: x", "Needs you" when `hitl` |
| What it is | the story file's `## Description` section; when there is no story file, the entry's `description` in the epic's `tickets/tickets.toml` | the epic file's `## Description` section | the file's `## Description` section |
| How we'll know it's done | the text after `Verify:` in the story file; else the entry's `verify` | none | the text after `Verify:` in the file |
| What it gives you | none | the epic file's `## Outcome` section | none |
| Progress | none | "n of m done", counted as on the band, plus "· n dropped" when any | none |
| Waits on | `after` as "2.14 Title", one per line (a bare number is in the same epic; an epic slug shows as "Epic 2 (Title)") | none | none |
| Blocked because | `blocked_reason` | none | none |
| Question to settle | `unknown` | none | none |
| Build plan | from the plan file's `## Intent`, the paragraphs that start `**Problem:**` and `**Approach:**` | none | none |
| Files (open in VS Code) | "Story file", "Build plan", "Walkthrough" when each exists; "Epic's ticket list" when there is no story file | "Epic file", "Retrospective" when it exists | "Ticket file" |

Where the files are (the epic folder is `<initiative>/tickets/<epic folder from status>/`; its leaves sit in its `tickets/` subfolder):

- Story file: the row's `file` in the epic's `tickets/` subfolder. Epic's ticket list: that subfolder's `tickets.toml`, whose `[[entry]]` with the same `id` gives `description` and `verify`.
- Build plan: the `*-plan.md` in the same subfolder whose frontmatter `ticket:` is the entry's `id` or the story file's name without `.md`. `status` does not give it, so look for it.
- Walkthrough: `<initiative>/walkthrough-<epic id>-<n>-<words>/walkthrough-<epic id>-<n>-<words>.md` (2.1 matches `walkthrough-2-1-…`, never `walkthrough-2-11-…`).
- Epic file: `<epic folder>/<slug>.md`. Retrospective: `<epic folder>/<slug>-retrospective.md`.
- Backlog Folder ticket: `_bmad-output/backlog/<file name>`.
- A section heading's text runs to the next heading; split it into paragraphs at blank lines. Frontmatter is the block between the first two `---` lines; read `title`, `type`, `risk` and `hitl` from it with a simple line match, not a YAML library.
- Each file link is `vscode://file/<absolute path>`, the path URL-quoted with `/` kept.

## Template

Use this template exactly. Copy the CSS and the script verbatim. Build the HTML with exactly this markup: `{{…}}` is a value to fill in (escape every one), and `<!-- … -->` comments say when a block appears or repeats; leave the comments out of the page. Add no other markup, classes, styles or design choices of your own.

### CSS (goes in the `<style>` tag)

```css
:root {
  --page: #0d1117; --area: #161b22; --card: #1c2128; --line: #30363d; --band: #21262d;
  --text: #e6edf3; --muted: #8b949e;
  --high: #f85149; --medium: #d29922; --low: #6e7681; --ready: #3fb950; --accent: #58a6ff;
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
.colhead { text-align: center; padding: 12px 8px; }
.colhead + .colhead { border-left: 1px solid var(--line); }
.colhead .label { margin: 0; font-size: 15px; font-weight: 600; color: var(--text); }
.colhead .sub { min-height: 1.4em; font-size: 13px; margin-top: 2px; }
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
}
```

### Script (goes in the `<script>` tag at the end of `<body>`)

```js
(function () {
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
})();
```

### Card (used everywhere a ticket appears)

```html
<div class="card risk-{{high|medium|low}} ready" data-detail="story:{{ref}}" tabindex="0">
  <div class="head"><span class="ref">{{ref}}</span> <span class="tag">spike</span> <span class="star" title="hitl">★</span><span class="pill">{{READY badge}}</span></div>
  <div class="ttl">{{title}}</div>
  <div class="why">{{why}}</div>
  <button type="button" class="copy" data-copy="{{ref}} {{title}}" aria-label="Copy {{ref}} {{title}}">Copy</button>
</div>
<!-- Drop the risk-… class when there is no risk, and "ready" when there is no badge.
     Drop the ref span in the Backlog Folder, the spike and ★ spans when they do not apply,
     the pill when there is no badge, and the why line when there is nothing to say.
     In the Backlog Folder, data-copy and aria-label hold the title alone ("Copy {{title}}"),
     and data-detail is "backlog:{{file name}}".
     The "Nothing can start now" card has no Copy button, no data-detail and no tabindex. -->
```

### Toggle row (Blocked and Backlog Folder in Next Up)

```html
<div class="trow">
  <button type="button" class="toggle" data-toggle="{{blocked|backlog-folder}}" aria-controls="tg-{{same key}}" aria-expanded="false">
    <span class="caret" aria-hidden="true"></span><span class="label">{{Blocked|Backlog Folder}} · {{count}}</span><span class="sub">{{(Can't Start Yet)|(Parking Lot · No Epic Yet)}}</span>
  </button>
  <div id="tg-{{same key}}" hidden><div class="cardgrid">{{cards}}</div></div>
</div>
<!-- Starts open (aria-expanded="true", no hidden) only for Blocked when nothing can start. -->
```

### Page

```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{initiative name}}</title><style>{{CSS}}</style></head>
<body>
<header class="top">
  <h1><span class="kicker">Initiative</span>{{initiative name}}</h1>
  <div class="meta">{{date}} · {{counts line}} · status read at {{HH:MM:SS}}</div>
</header>

<section class="nextup">
  <h2>Next Up</h2>
  <!-- only when next failed, replacing everything from the warning to Blocked: -->
  <div class="err">What's next could not be read. {{error}}</div>
  <!-- only when the tree needs fixing: -->
  <div class="warn">The ticket tree needs fixing; ask Sofia.</div>
  <div class="start"><p class="label">Start next</p><div class="cardgrid">{{card}}</div></div>
  <!-- each group only when its list is not empty: -->
  <div class="group"><p class="label">Then</p><div class="cardgrid">{{cards}}</div></div>
  <div class="group"><p class="label">Needs refining first</p><div class="cardgrid">{{cards}}</div></div>
  <div class="group"><p class="label">In Progress</p><div class="cardgrid">{{cards}}</div></div>
  {{toggle row: Blocked}}
  {{toggle row: Backlog Folder}}
  <!-- only when next backlog failed, in place of the Backlog Folder toggle row: -->
  <div class="trow"><span class="label">Backlog Folder</span><span class="sub">(Parking Lot · No Epic Yet)</span><p class="sub">The Backlog Folder could not be read. {{error}}</p></div>
</section>

<section class="board" id="board">
  <div class="cols">
    <div class="colhead"><p class="label">Planned · {{n}}</p><div class="sub">(Epic List Only)</div></div>
    <div class="colhead"><p class="label">Backlog · {{n}}</p><div class="sub">(Story or Build Plan Written)</div></div>
    <div class="colhead"><p class="label">In Progress · {{n}}</p><div class="sub">(Building)</div></div>
    <div class="colhead"><p class="label">Review · {{n}}</p><div class="sub">(Diff · Triage · Fix · Sign-off)</div></div>
    <button type="button" class="colhead toggle" data-toggle="done-column" data-class-target="board" data-class="done-open" aria-expanded="false"><p class="label"><span class="caret" aria-hidden="true"></span>Done · {{n}}</p><div class="sub"></div></button>
  </div>

  <!-- one per epic, in the order of epics -->
  <div class="epic" data-epic="{{slug}}" data-num="{{id}}">
    <!-- an epic that is not DONE: -->
    <div class="band"><span class="caret-space"></span><span class="ekicker">Epic {{id}}</span><span class="etitle">{{title}}</span><span class="done">{{n/m done}}</span><span class="bar"><span style="width:{{percent done}}%"></span></span></div>
    <!-- a DONE epic, instead of the band above: -->
    <button type="button" class="band toggle" data-toggle="epic-{{slug}}" aria-controls="tg-epic-{{slug}}" aria-expanded="false"><span class="caret" aria-hidden="true"></span><span class="ekicker">Epic {{id}}</span><span class="etitle">{{title}}</span><span class="done">DONE</span><span class="bar"><span style="width:100%"></span></span></button>
    <!-- every epic, right after its band: -->
    <button type="button" class="edetail" data-detail="epic:{{slug}}">Details</button>
    <div id="tg-epic-{{slug}}" class="ebody"><!-- add the hidden attribute on a DONE epic -->
      <div class="cells">
        <div class="cell" data-state="planned"><p class="label">Planned<br><span class="sub">(Epic List Only)</span></p>{{cards}}</div>
        <div class="cell" data-state="backlog"><p class="label">Backlog<br><span class="sub">(Story or Build Plan Written)</span></p>{{cards}}</div>
        <div class="cell" data-state="in-progress"><p class="label">In Progress<br><span class="sub">(Building)</span></p>{{cards}}</div>
        <div class="cell" data-state="review"><p class="label">Review<br><span class="sub">(Diff · Triage · Fix · Sign-off)</span></p>{{cards}}</div>
        <div class="cell" data-state="done"><p class="label">Done</p><div class="done-summary">{{k}} done</div>{{cards}}</div><!-- no done-summary when k is 0 -->
      </div>
      <!-- only when the epic has a ticket in a state outside the five columns: -->
      <div class="other">Other states: {{ref}} {{title}} ({{state}}), …</div>
    </div>
  </div>
</section>

<footer>
  <div class="key">
    <span><b>Planned</b>Listed in the epic, not written up yet</span>
    <span><b>Backlog</b>Written up (story or build plan), not started</span>
    <span><b>In Progress</b>Being built</span>
    <span><b>Review</b>Diff reviewed, findings triaged and fixed, waiting for your sign-off</span>
    <span><b>Done</b>Finished</span>
    <span><b>READY · n</b>Can start now; n is its place in Next Up</span>
    <span><b>★</b>Needs you</span>
    <span><b>Risk</b><i class="sw risk-high"></i>High<i class="sw risk-medium"></i>Medium<i class="sw risk-low"></i>Low</span>
  </div>
  <p>Longest chain still to build: {{chain}}</p>
</footer>
<aside class="panel" id="panel" data-keep hidden aria-label="Details">
  <button type="button" class="pclose" data-close aria-label="Close">×</button>
  <div id="panel-body"></div>
</aside>
<script>{{script}}</script>
</body></html>
```

### Details fragment (the body of a `/detail` answer)

```html
<p class="pkind">{{kind line}}</p>
<h2 class="ptitle">{{title}}</h2>
<p class="pmeta"><i class="sw risk-{{high|medium|low}}"></i>{{meta line}}</p>
<!-- each section only when it has text, in this order: -->
<section class="psec"><h3>What it is</h3><p>{{paragraph}}</p></section>
<section class="psec"><h3>How we'll know it's done</h3><p>{{text}}</p></section>
<section class="psec"><h3>What it gives you</h3><p>{{paragraph}}</p></section>
<section class="psec"><h3>Progress</h3><p>{{n of m done}}</p></section>
<section class="psec"><h3>Waits on</h3><ul><li>{{2.14 Title}}</li></ul></section>
<section class="psec"><h3>Blocked because</h3><p>{{blocked_reason}}</p></section>
<section class="psec"><h3>Question to settle</h3><p>{{unknown}}</p></section>
<section class="psec"><h3>Build plan</h3><p><b>Problem:</b> {{text}}</p><p><b>Approach:</b> {{text}}</p></section>
<section class="psec"><h3>Files (open in VS Code)</h3><ul><li><a href="vscode://file/{{absolute path}}">{{Story file}}</a></li></ul></section>
<!-- One <p> per paragraph. Drop the swatch when there is no risk, and the meta line when it is empty. -->
```

Not found: `<p class="pmeta">That item is not on the board now.</p>`. Error: `<p class="pmeta">The details could not be read. {{error}}</p>`.

If `status` itself fails, the page is the header (initiative name, date, "read at HH:MM:SS") followed by `<div class="err">{{error in plain words}}</div>`, the panel and the script, with nothing else. The script stays so the page recovers by itself once `status` works again. The page has no meta refresh tag: the script does the refreshing.

## How to build it

- One Python file with PEP 723 inline metadata, Python 3.11 or newer, standard library only (http.server, subprocess, json, html, webbrowser, tomllib).
- Listen on 127.0.0.1 only. Take a `--port` flag (default 8765), and if that port is taken, say so clearly instead of crashing. Take a `--no-open` flag that skips opening the browser.
- Escape every ticket text before it goes into the page.
- If tickets.py fails or prints something that is not JSON, show the error on the page in plain words. Do not crash the server.
- Ctrl+C stops it cleanly.
- `--start` runs the board as its own process and returns once the page answers: on Mac and Linux a new session (`start_new_session=True`), on Windows a detached new process group, with stdin closed and its output in `bmad-board-<port>.log` in the system temp folder. It passes on `--port` and `--folder` and the child always gets `--no-open`; `--start` itself opens the browser unless `--no-open` is given. It prints "Board for <initiative name> running at <address>" and, on the next line, "Stop it with: uv run scripts/board_server.py --stop" (with `--port <port>` added when not 8765).
  - Before starting, it checks the port. If a board already answers there, it prints "A board is already running at <address>" and the stop line, and exits 0. If something else answers, it says the port is in use by something else and exits 1.
  - If the child exits before the page answers, print the child's output and exit 1. If the page does not answer within 10 seconds, say so with the log's path and exit 1.
- Every response carries the header `X-Board-Server: 1`, so `--start` can tell the board from anything else on the port.
- `--stop` sends `POST /__stop` with the header `X-Board-Stop: 1` to 127.0.0.1 on `--port`. The board answers that request, and only that request, with the body `board stopping`, then shuts down cleanly. Anything else sent to `/__stop` gets 404. A web page cannot send this request, because the custom header needs a CORS preflight and the board refuses it.
  - `--stop` then waits up to 5 seconds for the port to stop answering and prints "Board on port <port> stopped." With nothing on the port, it prints "No board running on port <port>." and exits 0. If something else answers, it prints that the port is in use by something that is not the board, leaves it alone, and exits 1.
  - `--stop` never reads the tickets or the initiative folder. `--start` and `--stop` cannot be given together.

## Check it before you tell me it is done

- Start it with `--no-open` on a spare port, fetch the page with curl, and confirm the header counts equal the column counts, and that each equals the `counts` from tickets.py for that state (Planned = `planned`, Backlog = `backlog`, In Progress = `in-progress`, Review = `review`, Done = `done`).
- Confirm the "Start next" ticket is the first row of `ready_to_start` from `tickets.py next`, and that the "Then" list has the same refs in the same order.
- Confirm every READY card's ref is in `ready_to_start` or `ready_to_refine`, and no other card is marked READY.
- Confirm every card sits in the column of its own `state` from `status`, and that the Backlog Folder lists what `next backlog` gives.
- Confirm the cards in each column (except Done) appear in the same order as `next` lists them.
- Confirm on first load: every DONE epic's cards are hidden and every other epic's are shown; the Done column shows "n done" per epic; Blocked and Backlog Folder are closed (unless nothing can start).
- Confirm the page's `<style>` and `<script>` are byte-for-byte the template's CSS and script.
- Confirm every ticket card has exactly one Copy button whose `data-copy` is its ref and title (title alone in the Backlog Folder), and that the "Nothing can start now" card has none.
- In a headless browser: open the Done column and Blocked, wait past one 30-second refresh (or call the refresh by changing the page's visibility), and confirm both are still open, the toggles still work, and the content was swapped in rather than the page reloaded (a value set on `window` before the refresh is still there after it).
- Fetch `/detail` with curl for: a done story that has a build plan and a story file, a planned story with no file, an epic, and a Backlog Folder ticket. Confirm each section comes from the right file, the Waits on names are right, the file links point at files that exist, and no frontmatter key or state word appears (for example `baseline_revision`, `route:`, `status:`, `ready-for-dev`). Confirm an unknown id and a backlog id containing `/` or `..` get the not-found fragment with status 404.
- In the headless browser: click a card and confirm the panel opens with its title and the card is marked; trigger a refresh and confirm the panel is still open, with the same content; press Esc and confirm it closes; click an epic's Details and confirm the epic opens; reload and confirm it reopens.
- Take a screenshot at 1600px wide (for example headless Chrome) and look at it. With the pointer away from the cards and the panel closed, it should look the same as before the Copy button was added, apart from the Details buttons on the bands. Take a second screenshot with a story's panel open and look at it.
- Tell me which parts today's data could not test (for example an empty column or an empty list), so I know what has only been checked with a count of 0.
- Run `--start` on a spare port and confirm the page answers and the board's process is in its own session (on Mac or Linux, `ps -o pgid` differs from your shell's). Run `--start` again and confirm it says a board is already running and no second one starts. Run `--stop` and confirm the port stops answering, then `--stop` again and confirm "No board running". Start a plain `python3 -m http.server` on another spare port and confirm `--stop` leaves it running and `--start` refuses it. Confirm `POST /__stop` without the header gets 404. Run the board in the foreground and confirm `--stop` ends it too.
- Stop every server you started. Tell me the command to start it and the address to open. Do not set it to start at login unless I ask.
