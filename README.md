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
5. Tell me the commands to start and stop it (uv run scripts/board_server.py --start and --stop) and the address to open. Do not set it to start at login.
```

## Install by hand

From your project root:

```sh
mkdir -p scripts
curl -fsSL https://raw.githubusercontent.com/jheyworth/bmad-board-server/main/scripts/board_server.py -o scripts/board_server.py
```

## Run it

**Start:** paste this into Claude Code in your project:

```text
Start the BMad board: run uv run scripts/board_server.py --start from the project root and give me the link.
```

**Stop:** paste this:

```text
Stop the BMad board: run uv run scripts/board_server.py --stop from the project root.
```

Or run the same two commands yourself in a terminal, from the project root:

```sh
uv run scripts/board_server.py --start   # opens http://127.0.0.1:8765/ and returns
uv run scripts/board_server.py --stop
```

A board started with `--start` runs on its own: it keeps going after you close the terminal or the Claude Code session that started it, until you run `--stop`. If the board is already running, `--start` just opens it. If you use another port, give `--stop` the same `--port`.

Plain `uv run scripts/board_server.py` (without `--start`) runs the board inside that terminal instead: **Ctrl+C** stops it, and closing the terminal or Claude Code session stops it too.

| Flag | What it does |
| --- | --- |
| `--start` | Run the board on its own and return |
| `--stop` | Stop the board on `--port` |
| `--port 8765` | Port to listen on (127.0.0.1 only) |
| `--no-open` | Don't open the browser |
| `--folder <initiative folder>` | Pick the initiative when there is more than one |
