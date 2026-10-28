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
- **Paste into Claude Code** in your project:
```
Install the BMad live kanban board in this project.
1. Check .agents/skills/bmad-agent-po/scripts/tickets.py and an _bmad-output/initiative-* folder exist. If not, stop and tell me.
2. Download https://raw.githubusercontent.com/jheyworth/bmad-board-server/main/scripts/board_server.py to scripts/board_server.py (not inside _bmad/).
3. Run it with: uv run scripts/board_server.py --no-open --port 8799, curl the page to check it works, then stop it.
4. Tell me the start command and address.
```

## Run it
- **Start**: `uv run scripts/board_server.py`
- **Open**: http://127.0.0.1:8765
- **Stop**: Ctrl+C

🔗 **Repo + docs:** https://github.com/jheyworth/bmad-board-server
