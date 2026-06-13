# myfund-mcp

MCP server (Model Context Protocol) do odczytu danych portfela inwestycyjnego z myFund.pl.
Udostępnia Claude narzędzia do analizy portfeli, pozycji, alokacji i historii wycen.

## Cel projektu

myFund.pl to polska platforma do śledzenia inwestycji (fundusze, IKE, IKZE, akcje itp.).
Serwer podłącza Claude do API myFund i pozwala na rozmowę o portfelu: aktualna wartość,
stopy zwrotu, alokacja geograficzna/sektorowa, porównania między portfelami, trendy czasowe.

Połączony ze skillem `skills/myfund-portfolio-analysis/` który uczy Claude budowania
wizualnych raportów i dashboardów z danych portfela.

## Stack techniczny

- Python 3.11+, `mcp[cli]`, `httpx`
- FastMCP, jeden plik `src/server.py` (cały serwer)
- API myFund.pl v1 (beta): REST, read-only, GET `/getPortfel.php`
- Autoryzacja: `?apiKey=...` jako parametr URL (klucz z ustawień konta)
- Cache po stronie serwera API: 5 minut — nie ma sensu odpytywać częściej
- Liczby w API zwracane są jako stringi (czasem z prefixem '+', spacjami) — parser `to_number()`

## Narzędzia MCP

| Narzędzie | Co robi |
|---|---|
| `get_portfolio` | Podsumowanie portfela: wartość, zysk, stopy zwrotu |
| `get_positions` | Lista pozycji w portfelu (fundusze/aktywa) z wartościami |
| `get_allocation` | Rozkład alokacji (geograficzna, sektorowa, walutowa) |
| `get_portfolio_timeseries` | Historia wyceny portfela w czasie |
| `show_dashboard` | Zbiorczy widok wielu portfeli naraz |

## Struktura

```
src/
  server.py       — cały serwer: konfiguracja, helpers, wszystkie @mcp.tool()
skills/
  myfund-portfolio-analysis/
    SKILL.md      — skill Claude Code do analizy i wizualizacji portfela
pyproject.toml
.env.example
```

## Konfiguracja środowiska

```bash
MYFUND_API_KEY=twoj_klucz_api          # Menu → Konto → Ustawienia konta → Klucz API
MYFUND_BASE_URL=https://myfund.pl/API/v1   # opcjonalne, to jest domyślne
MYFUND_PORTFELE=Inwestycje,Emerytalny Rafal,Emerytalny Paulina   # portfele do dashboardu
```

Klucz API znajdziesz w myFund.pl: Menu → Konto → Ustawienia konta → Klucz API.

## Uruchomienie

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
MYFUND_API_KEY=xxx python src/server.py
```

## MCP config (do .mcp.json lub Claude Desktop)

```json
{
  "mcpServers": {
    "myfund": {
      "command": "/Users/rafal/claude code/myfund-mcp/.venv/bin/python",
      "args": ["/Users/rafal/claude code/myfund-mcp/src/server.py"],
      "env": {
        "MYFUND_API_KEY": "twoj_klucz"
      }
    }
  }
}
```

## Ważne szczegóły API

- Endpoint: `GET /getPortfel.php?apiKey=...&portfel=...&format=json`
- Nazwy portfeli mogą zawierać spacje (httpx koduje automatycznie)
- API jest wolne (bywa 10-20s) — timeout ustawiony na 30s
- Wartości liczbowe wymagają defensywnego parsowania (`to_number()`)
- Plik `.bak` w oryginalnej lokalizacji (`~/mcp-servers/`) to stara kopia — można usunąć

## Powiązane projekty

- `myfund-dashboard/` — Streamlit dashboard (wizualizacja tych samych danych, inne UI)
