# Using and editing the board

This repo has two files that describe the same board:

| File | What it is | When to touch it |
| --- | --- | --- |
| [`board_server-prompt.md`](board_server-prompt.md) | The **spec**: a prompt you paste into Claude Code, which builds the board from it | When you want the board to *behave* differently |
| [`scripts/board_server.py`](scripts/board_server.py) | The **result**: the script Claude Code built from that prompt | When you want a small fix without rebuilding |

The prompt is the source of truth. If you edit the `.py` by hand, the next rebuild from the prompt will undo your change unless you put it in the prompt too.

## Using it

Start and stop it with one command each, from the project root. Run them in a terminal, or ask Claude Code to run them:

```sh
uv run scripts/board_server.py --start    # opens http://127.0.0.1:8765/ and returns
uv run scripts/board_server.py --stop
uv run scripts/board_server.py --start --port 9000 --no-open
uv run scripts/board_server.py --stop --port 9000
uv run scripts/board_server.py --start --folder initiative-my-project
```

A board started with `--start` keeps running until `--stop`, even after the terminal or Claude Code session that started it ends. Without `--start`, the board runs inside that terminal and Ctrl+C stops it.

What's on the page:

- **Header:** initiative name, today's date, ticket counts per column, and when the status was read.
- **Next Up:** the same answer to "what's next?" that Sofia gives.
  - **Start next** and **Then**: tickets ready to build, in build order.
  - **Needs refining first**, **In Progress**, **Blocked** (collapsed), **Backlog Folder** (collapsed).
- **Board:** one row per epic, five columns: Planned, Backlog, In Progress, Review, Done.
  - Click the **Done** heading to show or hide finished cards.
  - Finished epics start collapsed; click the band to open.
- **Cards:** click one (or press Enter) to open a **details panel** on the right. Hover for a **Copy** button that copies "ref title" ready to paste into Sofia or a build.
- **Footer:** a key for the columns, badges and risk colours, plus the longest chain of stories still to build.

Your open/closed toggles and the open details panel are remembered in the browser, so the 30-second refresh never resets them.

### Where the data comes from

The board only reads. On every page load it runs:

```sh
uv run <tickets.py> --project-root <repo root> status <initiative folder>
uv run <tickets.py> --project-root <repo root> next <initiative folder>
uv run <tickets.py> --project-root <repo root> next backlog
```

Epic titles come from `tickets/tickets.toml` in the initiative folder. The details panel reads the story, plan, epic and walkthrough files for the one item you clicked. If any command fails, the page says so in plain words instead of crashing.

## Editing the prompt (recommended)

1. Open `board_server-prompt.md` and change the part you care about. Its sections:
   - **What I want** / **Where the status comes from**: the overall behaviour and data sources.
   - **Header**, **Next Up**, **The board**, **Details panel**: what each part of the page shows, in plain English.
   - **Template**: the exact CSS, JavaScript and HTML. Claude Code copies these verbatim, so change the look here.
   - **How to build it**: technical rules (one file, standard library, `--port` / `--no-open`).
   - **Check it before you tell me it is done**: the tests Claude Code runs before handing it back.
2. Paste everything below the `---` line into Claude Code in your BMad project.
3. Claude Code writes `scripts/board_server.py` and runs the checks.
4. If you changed behaviour, add a matching line to the **Check it** list so the next build tests it too.

Tips:

- Keep the wording exact for anything that must match Sofia (column names, "READY" badges, state names).
- The prompt says "Never work it out yourself" about ticket state and order on purpose: the board must agree with `tickets.py`. Keep that rule.

## Editing the script directly

Good for quick fixes. Where things live in `scripts/board_server.py`:

| Part | Where |
| --- | --- |
| Colours, layout, fonts | `CSS` constant near the top |
| Toggles, refresh, Copy, details panel behaviour | `SCRIPT` constant |
| Column names and second lines | `COLUMNS` |
| Finding `tickets.py` and the initiative folder | `find_tickets_py()`, `find_folder()` |
| Running `tickets.py` | `run_tickets()` |
| The main page (header, Next Up, board, footer) | `render()` |
| One ticket card | `card()` |
| Details panel answers | `detail_story()`, `detail_epic()`, `detail_backlog()` |
| Server, flags, port handling | `make_handler()`, `main()` |

After editing:

```sh
uv run scripts/board_server.py --no-open --port 8799
curl -s http://127.0.0.1:8799/ | head -40
```

Then copy the change back into the prompt's matching section so it survives the next rebuild.
