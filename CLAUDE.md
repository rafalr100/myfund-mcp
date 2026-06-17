# myfund-mcp

MCP server (Model Context Protocol) do odczytu danych portfela inwestycyjnego z myFund.pl.
Udostępnia Claude narzędzia do analizy portfeli, pozycji, alokacji i historii wycen.

## Cel projektu

myFund.pl to polska platforma do śledzenia inwestycji (fundusze, IKE, IKZE, akcje itp.).
Serwer podłącza Claude do API myFund i pozwala na rozmowę o portfelu: aktualna wartość,
stopy zwrotu, alokacja wg typu aktywów i walorów, porównania między portfelami, trendy czasowe.

Połączony ze skillem `skills/myfund-portfolio-analysis/` który uczy Claude *jak* analizować
te dane (wybór narzędzia, interpretacja stóp zwrotu, traktowanie braków) i budować wizualne
raporty/dashboardy.

## Stack techniczny

- Python 3.11+, `mcp[cli]>=1.0.0`, `httpx>=0.27.0`
- FastMCP, jeden plik `src/server.py` (cały serwer, ~540 linii)
- Build: `hatchling`; pakiet `src` z entry pointem `myfund-mcp = "src.server:main"`
- API myFund.pl v1 (beta): REST, read-only, jedyny endpoint `GET /getPortfel.php`
- Autoryzacja: `?apiKey=...` jako parametr URL (klucz z ustawień konta)
- Liczby w API zwracane bywają jako stringi (czasem z prefiksem `+`, spacjami jako
  separatorem tysięcy, przecinkiem dziesiętnym lub `%`) — parser `to_number()`

## Narzędzia MCP

Wszystkie narzędzia przyjmują argument `portfel` (nazwa dokładnie jak na koncie) i pod
spodem wołają ten sam endpoint `getPortfel.php` — różnią się tym, którą część odpowiedzi
normalizują i zwracają.

| Narzędzie | Co robi | Kluczowe pola odpowiedzi API |
|---|---|---|
| `get_portfolio` | Podsumowanie portfela: wartość, zysk, udział, stopy zwrotu za okresy | `portfel` |
| `get_positions` | Lista pozycji posortowana malejąco wg wartości (ticker, typ, sektor, konto, zysk) | `tickers` |
| `get_allocation` | Alokacja **wg typu aktywów** (`struktura`) i **wg walorów** (`strukturaWalory`) z kolorami | `struktura`, `strukturaWalory` + `*Kolor` |
| `get_portfolio_timeseries` | Szereg czasowy (domyślnie podsumowanie, `pelne_dane=True` = pełny) | `wartoscWCzasie`, `zyskWCzasie`, `wkladWCzasie`, `benchWCzasie`, `stopaZwrotuWCzasie`, `zmianaDzienna` |
| `show_dashboard` | Zbiorczy widok wielu portfeli naraz — dane gotowe do zbudowania artefaktu HTML | wiele wywołań równolegle |

Uwagi do narzędzi:
- `get_portfolio` celowo **pomija szeregi czasowe** — od tego jest `get_portfolio_timeseries`.
- `get_portfolio_timeseries` waliduje argument `seria` względem białej listy i domyślnie
  zwraca tylko podsumowanie (liczba punktów, zakres dat, pierwsza/ostatnia wartość), żeby
  nie zalewać kontekstu setkami punktów dziennych.
- `show_dashboard` bierze nazwy z argumentu `portfele="a,b,c"` lub — gdy pusty — z
  `MYFUND_PORTFELE`. Pobiera wszystkie portfele równolegle (`asyncio.gather`), a portfele,
  których nie udało się pobrać, trafiają do listy `errors` zamiast przerywać całość.

## Struktura

```
src/
  __init__.py     — pusty, czyni z src/ pakiet importowalny
  server.py       — cały serwer: konfiguracja, helpers, wszystkie @mcp.tool(), main()
skills/
  myfund-portfolio-analysis/
    SKILL.md      — skill Claude Code: jak analizować i wizualizować dane portfela
pyproject.toml    — hatchling, zależności, entry point
.env.example      — szablon zmiennych środowiskowych
README.md         — dwujęzyczny (PL + EN): instalacja, konfiguracja Claude, troubleshooting
LICENSE           — MIT
```

## Architektura `src/server.py`

Plik dzieli się na cztery sekcje (oznaczone komentarzami-separatorami):

1. **Konfiguracja** — `BASE_URL`, `API_KEY`, `PORTFELE`, `API_PATH`, `HTTP_TIMEOUT` (30s,
   bo API bywa wolne), instancja `mcp = FastMCP("myfund")`. Logi `httpx`/`httpcore` są
   wyciszane do `WARNING`, żeby klucz API (w URL-u) nigdy nie trafił do stderr.
2. **Helpers** — defensywne parsowanie i warstwa HTTP:
   - `to_number()` — string/number → `float | None`, obsługa `+`, spacji/` `,
     przecinka dziesiętnego, `%` i mieszanych separatorów (kropka=tysiące, przecinek=dziesiętny).
   - `_call_api()` — wspólne wywołanie endpointu z cache, mapowaniem błędów HTTP/JSON i
     interpretacją `status.code` (`"0"`/`""` = sukces, `"7"` = portfel nie znaleziony, inne = błąd).
   - `_date_sort_key()` — chronologiczne sortowanie kluczy szeregów: rozpoznaje
     `YYYY-MM-DD`, `DD-MM-YYYY`/`DD.MM.YYYY` i uniksowe timestampy; nierozpoznane formaty
     lądują w osobnym „koszyku" sortowanym leksykalnie.
   - `_series_summary()` — skraca szereg czasowy do liczby punktów + zakresu + krańcowych wartości.
3. **Narzędzia MCP** — cztery `@mcp.tool()`: `get_portfolio`, `get_positions`,
   `get_allocation`, `get_portfolio_timeseries`.
4. **Dashboard + entry point** — `_collect_portfolios()` (logika agregacji),
   `show_dashboard()` (`@mcp.tool()`) oraz `main()` → `mcp.run()`.

### Cache (dwie warstwy!)

- **Po stronie API myFund**: ~5 minut — nie ma sensu odpytywać częściej.
- **Po stronie serwera (klient)**: krótki cache w pamięci, `_CACHE_TTL = 60s`, kluczowany po
  parametrach żądania (`_cache`). `getPortfel.php` zwraca **cały** payload portfela, a kilka
  narzędzi uderza w ten sam endpoint dla tego samego portfela — cache unika ponownego
  pobierania. `_prune_cache()` wymiata przeterminowane wpisy przy każdym zapisie, żeby cache
  nie rósł w nieskończoność w długo żyjącym procesie.

### Agregacja w dashboardzie

- Stopa zwrotu zbiorcza to **średnia ważona wartością** portfeli (`stopa_zwrotu_1r_wazona`),
  nie zwykła średnia procentów.
- Sumowanie wartości ma sens tylko w jednej walucie. Gdy portfele są w różnych walutach,
  `_collect_portfolios` ustawia flagę `waluty_niespojne=True` i listę `waluty`, żeby dashboard
  mógł ostrzec zamiast cicho zsumować różne waluty.

## Konwencje

- **Nazewnictwo**: API i klucze odpowiedzi są po polsku (`portfel`, `wartosc`, `zysk`,
  `wartoscWCzasie`), kod i komentarze techniczne mieszają polski i angielski — trzymaj się
  stylu sąsiadującego kodu.
- **Parsuj defensywnie**: każdą liczbę z API przepuszczaj przez `to_number()`. `null`/`None`
  traktuj jako „brak", nigdy jako 0 i nigdy nie zmyślaj wartości.
- **Read-only**: serwer i skill nigdy nie wykonują transakcji ani nie modyfikują konta.
- **Oszczędzaj kontekst**: domyślnie zwracaj podsumowania szeregów, pełne dane tylko na żądanie.
- **Nowy endpoint?** Cała komunikacja idzie przez `_call_api()` — dodawaj nowe narzędzia tym
  samym wzorcem (walidacja argumentów → `_call_api` → normalizacja przez `to_number`).

## Konfiguracja środowiska

```bash
MYFUND_API_KEY=twoj_klucz_api          # wymagany; Menu → Konto → Ustawienia konta → Klucz API
MYFUND_BASE_URL=https://myfund.pl/API/v1   # opcjonalne, to jest domyślne
MYFUND_PORTFELE=Inwestycje,Emerytalny Rafal,Emerytalny Paulina   # tylko dla show_dashboard
```

`MYFUND_PORTFELE` jest potrzebne wyłącznie do `show_dashboard` — pozostałe narzędzia działają
bez niej. Skopiuj `.env.example` do `.env` i uzupełnij. Wygenerowanie nowego klucza API
natychmiast unieważnia poprzedni.

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
      "command": "/ścieżka/do/myfund-mcp-server/.venv/bin/python",
      "args": ["/ścieżka/do/myfund-mcp-server/src/server.py"],
      "env": {
        "MYFUND_API_KEY": "twoj_klucz",
        "MYFUND_PORTFELE": "Inwestycje,Emerytalny Rafal"
      }
    }
  }
}
```

`command` musi wskazywać Pythona z `.venv` (tego, do którego zainstalowano zależności), inaczej
serwer nie znajdzie modułu `mcp`. Pełna instrukcja (macOS/Windows/Linux, ścieżki configów,
troubleshooting) jest w `README.md`.

## Ważne szczegóły API

- Endpoint: `GET /getPortfel.php?apiKey=...&portfel=...&format=json` — `format=json` wymuszany
  jest dla każdego żądania.
- To **jedyny** endpoint — API nie ma listy portfeli, dlatego dashboard woła go raz na portfel.
- Nazwy portfeli mogą zawierać spacje (httpx koduje automatycznie); muszą zgadzać się co do
  znaku z nazwą na koncie (inaczej `status.code == "7"`).
- API jest w fazie **beta**, bywa wolne (10-20s) — timeout ustawiony na 30s.
- Błędy logiczne sygnalizowane są w `status.code` mimo HTTP 200. Niepoprawny klucz / brak
  dostępu do bety często objawia się odpowiedzią HTML zamiast JSON — `_call_api` mapuje to na
  czytelny komunikat.
- Pole `data` (data wyceny) bywa `&nbsp;` gdy niedostępne — traktuj jako brak.

## Powiązane projekty

- `myfund-dashboard/` — Streamlit dashboard (wizualizacja tych samych danych, inne UI)
