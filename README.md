# myfund-mcp

> MCP server for [myFund.pl](https://myfund.pl) — expose your investment portfolio data to Claude.

A [Model Context Protocol](https://modelcontextprotocol.io) server that connects Claude to the myFund.pl API, giving you a conversational interface to your investment portfolios.

## What you can ask Claude

- *"What is the total value of my portfolios?"*
- *"Show me the asset allocation of my retirement account"*
- *"How has my Inwestycje portfolio performed over the last 6 months?"*
- *"Compare the returns across all my portfolios"*
- *"Which positions have the highest gains right now?"*

## Tools

| Tool | Description |
|------|-------------|
| `get_portfolio` | Portfolio summary: total value, profit/loss, returns |
| `get_positions` | List of positions (funds/assets) with current values |
| `get_allocation` | Allocation breakdown (geographic, sector, currency) |
| `get_portfolio_timeseries` | Historical portfolio valuation |
| `show_dashboard` | Combined view across multiple portfolios |

## Setup

### 1. Get your API key

Log in to [myFund.pl](https://myfund.pl) → Menu → Konto → Ustawienia konta → Klucz API

### 2. Install

```bash
git clone https://github.com/rafalr100/myfund-mcp-server.git
cd myfund-mcp-server
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and set MYFUND_API_KEY
```

### 4. Add to Claude

**Claude Code** — create `.mcp.json` in the project directory:
```json
{
  "mcpServers": {
    "myfund": {
      "command": "/path/to/myfund-mcp-server/.venv/bin/python",
      "args": ["/path/to/myfund-mcp-server/src/server.py"]
    }
  }
}
```

**Claude Desktop** — add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "myfund": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/myfund-mcp-server/src/server.py"],
      "env": {
        "MYFUND_API_KEY": "your_api_key"
      }
    }
  }
}
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MYFUND_API_KEY` | ✅ | — | API key from myFund.pl settings |
| `MYFUND_BASE_URL` | ❌ | `https://myfund.pl/API/v1` | API base URL |
| `MYFUND_PORTFELE` | ❌ | — | Comma-separated portfolio names for dashboard |

## Notes

- The myFund.pl API is **read-only** — no trades or modifications are possible
- API responses are cached server-side for ~5 minutes
- Numeric values from the API are returned as strings with Polish formatting — the server normalises them automatically

## License

MIT
