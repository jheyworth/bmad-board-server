## 📋 BMad Live Kanban Board

**What:** a live board of your BMad epics and stories, in your browser.
- **Read-only**: never changes a ticket
- **Live**: refreshes every 30s, keeps what you have open
- **Same "what's next?"** as Sofia

## Why use it
- **See it all**: every epic and story on one page
- **Next Up**: what to build next, in order
  - Ready, in progress, blocked
- **Click a card** for its details
- **Copy button** to paste a ticket into Sofia

## Install
- **Needs**: a BMad project with Sofia's tickets, plus `uv`
- **Step 1**: save the attached **board_server.py** to the root of your project folder
- **Step 2**: paste this into Claude Code in your project:
```
Install the BMad live kanban board in this project.
1. Check board_server.py is in the project root. If not, stop and tell me.
2. Check .agents/skills/bmad-agent-po/scripts/tickets.py and an _bmad-output/initiative-* folder exist. If not, stop and tell me.
3. Create a scripts/ folder in the project root if there isn't one (not inside _bmad/). If scripts/board_server.py already exists, ask me before replacing it.
4. Move board_server.py into scripts/. Don't change the file.
5. Run it with: uv run scripts/board_server.py --no-open --port 8799, curl the page to check it works, then stop it.
6. Tell me the start and stop commands (--start and --stop) and the address.
```

## Run it
- **Start**: paste this into Claude Code in your project:
```
Start the BMad board: run uv run scripts/board_server.py --start from the project root and give me the link.
```
- **Stop**: paste this:
```
Stop the BMad board: run uv run scripts/board_server.py --stop from the project root.
```
- **Or in a terminal**: the same two commands, `--start` and `--stop`
- **Keeps running** until you stop it, even after Claude Code closes
- **Port busy?** It picks the next free one and tells you; stop still finds it


