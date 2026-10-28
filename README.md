# BMad Board Server

A live, read-only kanban board for a BMad project's epics and stories, served on `http://127.0.0.1:8765`.

- **One file:** `scripts/board_server.py`, Python 3.11+, standard library only.
- **Read-only:** it runs Sofia's `tickets.py status` / `next` and draws what they print. It never changes a ticket.
- **Live:** the page refreshes itself every 30 seconds without losing what you have open.

Want to change how it works? See [GUIDE.md](GUIDE.md).

## Requirements

- A BMad project whose tickets are tracked with Sofia's `tickets.py` (`.agents/skills/bmad-agent-po/scripts/tickets.py`) and an `_bmad-output/initiative-*` folder.
- [`uv`](https://docs.astral.sh/uv/) on your PATH.

## Install with Claude Code

Open Claude Code in your BMad project and paste this:

```text
Install the BMad live kanban board in this project.

1. Check this is a BMad project: .agents/skills/bmad-agent-po/scripts/tickets.py exists (search for tickets.py under .agents, .claude or _bmad if it is elsewhere) and there is an initiative-* folder under _bmad-output/. If either is missing, stop and tell me.
2. Check uv is installed. If not, stop and tell me how to install it.
3. Download https://raw.githubusercontent.com/jheyworth/bmad-board-server/main/scripts/board_server.py to scripts/board_server.py in this repo's root (create scripts/ if needed). Do not put it inside _bmad/: the BMad installer replaces that folder. If scripts/board_server.py already exists, ask me before replacing it. Do not change the file.
4. Test it: run `uv run scripts/board_server.py --no-open --port 8799`, fetch http://127.0.0.1:8799/ with curl, confirm the page shows the initiative name and the column counts, then stop the server.
5. Tell me the command to start it and the address to open. Do not set it to start at login.
```

## Install by hand

From your project root:

```sh
mkdir -p scripts
curl -fsSL https://raw.githubusercontent.com/jheyworth/bmad-board-server/main/scripts/board_server.py -o scripts/board_server.py
```

## Run it

Paste this into Claude Code in your project:

```text
Start the BMad live kanban board: from the project root, run uv run scripts/board_server.py in the background. If port 8765 is in use, add --port 8766. Once it prints its address, give me the link and leave it running.
```

It opens your browser at `http://127.0.0.1:8765/`. To stop it, ask Claude Code to stop the board.

To run it yourself instead: `uv run scripts/board_server.py` from the project root, and **Ctrl+C** to stop.

| Flag | What it does |
| --- | --- |
| `--port 8765` | Port to listen on (127.0.0.1 only) |
| `--no-open` | Don't open the browser |
| `--folder <initiative folder>` | Pick the initiative when there is more than one |
