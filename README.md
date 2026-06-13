![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet?logo=anthropic)
![License](https://img.shields.io/badge/license-MIT-green)
![API](https://img.shields.io/badge/myFund.pl-API%20beta-orange)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

# myFund.pl MCP Server

## Spis treści

- [Narzędzia](#narzędzia)
- [Przykłady użycia](#przykłady-użycia)
- [Wymagania](#wymagania)
- [Instalacja](#instalacja)
- [Dashboard portfeli](#dashboard-portfeli)
- [Skill analityczny](#skill-analityczny-opcjonalnie)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)
- [Zmienne środowiskowe](#zmienne-środowiskowe)
- [Uwagi techniczne](#uwagi-techniczne)
- [Licencja](#licencja)


Serwer [MCP (Model Context Protocol)](https://modelcontextprotocol.io) udostępniający dane portfela inwestycyjnego z [myFund.pl](https://myfund.pl) jako narzędzia dla Claude Desktop.

## Narzędzia

| Narzędzie | Co zwraca |
|---|---|
| `get_portfolio` | Podsumowanie portfela: wartość, zysk, stopy zwrotu za okresy (1T / 1M / 3M / 1R / 5R…) |
| `get_positions` | Lista pozycji posortowana wg wartości (ticker, typ, sektor, konto, zysk) |
| `get_allocation` | Alokacja wg typu aktywów i wg walorów z kolorami |
| `get_portfolio_timeseries` | Szereg czasowy: wartość / zysk / wkład / benchmark / stopa zwrotu |

## Przykłady użycia

Po podpięciu serwera możesz zadawać Claude pytania w naturalnym języku:

**Podsumowanie i wyniki:**
> „Pokaż podsumowanie portfela Inwestycje"
> „Jaki jest mój całkowity zysk i stopa zwrotu od początku roku?"
> „Jak zmieniała się wartość portfela przez ostatnie 12 miesięcy?"

**Pozycje i selekcja:**
> „Które 5 pozycji przyniosło największy zysk?"
> „Pokaż wszystkie pozycje na koncie IKE"
> „Jakie ETF-y mam w portfelu i ile każdy z nich waży?"

**Alokacja:**
> „Jak wygląda podział portfela wg typu aktywów?"
> „Które walory mają największy udział w portfelu?"
> „Czy jestem zdywersyfikowany sektorowo?"

**Analiza w czasie:**
> „Porównaj stopę zwrotu portfela z benchmarkiem WIG w tym roku"
> „Kiedy portfel osiągnął najwyższą wartość?"
> „Pokaż dzienny zysk/stratę za ostatni miesiąc"

## Wymagania

- macOS, Windows lub Linux
- Python 3.10 lub nowszy
- Claude Desktop

## Instalacja

### 1. Pobierz skrypt

Pobierz plik [`myfund_mcp_server.py`](myfund_mcp_server.py) i przenieś go do wybranego folderu, np.:

```bash
mkdir -p ~/mcp-servers
mv ~/Downloads/myfund_mcp_server.py ~/mcp-servers/
```

### 2. Zainstaluj Pythona 3.12 (jeśli nie masz)

**macOS:**
```bash
brew install python@3.12
```

**Windows:** pobierz instalator z [python.org](https://python.org).

### 3. Utwórz środowisko wirtualne i zainstaluj zależności

**macOS / Linux:**
```bash
/opt/homebrew/bin/python3.12 -m venv ~/mcp-servers/venv
~/mcp-servers/venv/bin/python -m pip install "mcp" httpx
```

**Windows:**
```cmd
python -m venv %USERPROFILE%\mcp-servers\venv
%USERPROFILE%\mcp-servers\venv\Scripts\python -m pip install "mcp" httpx
```

### 4. Pobierz klucz API z myFund.pl

Zaloguj się → **Menu → Konto → Ustawienia konta → Klucz API** → wygeneruj i skopiuj.

> ⚠️ Wygenerowanie nowego klucza natychmiast unieważnia poprzedni.

### 5. Skonfiguruj Claude Desktop

Otwórz: **Settings → Developer → Edit Config**

Lokalizacja pliku konfiguracyjnego:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Wklej do sekcji `"mcpServers"`:

```json
{
  "mcpServers": {
    "myfund": {
      "command": "/Users/TWOJA_NAZWA/mcp-servers/venv/bin/python",
      "args": ["/Users/TWOJA_NAZWA/mcp-servers/myfund_mcp_server.py"],
      "env": {
        "MYFUND_API_KEY": "TWOJ_KLUCZ_API",
        "MYFUND_PORTFELE": "Nazwa portfela 1,Nazwa portfela 2,Nazwa portfela 3"
      }
    }
  }
}
```

Podmień:
- `TWOJA_NAZWA` → nazwa użytkownika systemowego (na macOS: wynik `whoami` w Terminalu)
- `TWOJ_KLUCZ_API` → klucz z kroku 4
- `MYFUND_PORTFELE` → nazwy Twoich portfeli **dokładnie jak na koncie myFund**, rozdzielone przecinkami (spacje w nazwach są OK). Dowolna liczba portfeli. Ta zmienna jest potrzebna tylko do dashboardu — pojedyncze narzędzia (`get_portfolio` itd.) działają bez niej.

> **Ważne:** `command` musi wskazywać na Pythona z venv — tego, do którego zainstalowano `mcp`.

### 6. Zrestartuj Claude Desktop

Cmd+Q (macOS) lub całkowite zamknięcie, potem uruchom ponownie.

### 7. Test

W nowym czacie napisz:

> Pokaż podsumowanie portfela „Nazwa Twojego Portfela"

---

## Dashboard portfeli

Serwer udostępnia narzędzie `show_dashboard`, które pobiera **wszystkie** Twoje portfele naraz (z listy `MYFUND_PORTFELE`) i zwraca dane gotowe do wizualizacji. Po jego wywołaniu Claude buduje **interaktywny dashboard jako artefakt HTML**, otwierany obok rozmowy.

Wystarczy poprosić:

> Pokaż mój dashboard portfeli

Dashboard pokazuje:
- **widok zbiorczy** — łączna wartość wszystkich portfeli, suma zysku, średnia ważona stopa zwrotu, wykres wartości w czasie, udział każdego portfela w całości
- **zakładki** — wejście w każdy portfel osobno: jego wykres, pozycje i stopy zwrotu

Liczba portfeli jest dowolna — zależy od tego, ile nazw wpiszesz w `MYFUND_PORTFELE`. Stopa zwrotu w widoku zbiorczym to średnia ważona wartością portfeli (nie zwykła średnia procentów).

> **Uwaga:** dashboard powstaje jako artefakt (renderowany przez Claude), nie jako osadzony panel MCP — działa to niezależnie od wersji Claude Desktop.

## Skill analityczny (opcjonalnie)

Oprócz serwera MCP repozytorium zawiera **Agent Skill** — `myfund-portfolio-analysis`. To osobna warstwa, która uczy Claude *jak analizować* dane z portfela: które z czterech narzędzi wybrać do danego pytania, jak interpretować stopy zwrotu, jak traktować brakujące wartości i gdzie są granice (analiza tak, porady inwestycyjne nie).

**Serwer MCP dostarcza dane — skill mówi, jak o nich myśleć.** Działają razem, ale są niezależne: serwer konfigurujesz w `claude_desktop_config.json`, skill wgrywasz w ustawieniach Claude.

### Co daje skill

- Wybiera właściwe narzędzie do pytania (podsumowanie / pozycje / alokacja / szereg czasowy)
- Poprawnie nazywa okresy stóp zwrotu (1T, 1M, 3M, 6M, 1R, 3R, 5R, MtD, YtD)
- Traktuje brakujące dane jako „brak", nie zmyśla liczb
- Pilnuje granic: read-only, bez porad inwestycyjnych, bez analizy transakcji, których nie ma w danych

### Jak wgrać w Claude

1. Pobierz [`skills/myfund-portfolio-analysis.zip`](skills/myfund-portfolio-analysis.zip)
2. W Claude: **Settings → Capabilities** — upewnij się, że **Code execution and file creation** jest włączone (bez tego sekcja Skills się nie pojawi)
3. Przejdź do **Capabilities → Skills** (na niektórych planach: **Customize → Skills**)
4. Kliknij **„+"** → **Upload skill** i wskaż pobrany ZIP
5. Claude pokaże nazwę i opis — **włącz przełącznik**, aby skill był aktywny
6. Otwórz **nowy czat** i zadaj pytanie o portfel — skill załaduje się automatycznie

> **Uwaga:** skill wymaga działającego serwera MCP `myfund` (sekcja Instalacja powyżej). Sam skill bez serwera nie ma skąd pobrać danych.

## Rozwiązywanie problemów

### ❌ `No module named 'mcp'`
**Przyczyna:** Claude uruchamia Pythona systemowego zamiast tego z venv.
**Rozwiązanie:** Upewnij się, że `command` w configu wskazuje na `~/mcp-servers/venv/bin/python`, a nie na systemowy `python3`.

### ❌ `Odpowiedź nie jest poprawnym JSON-em`
**Przyczyna:** Niepoprawny klucz API lub brak dostępu do bety myFund.pl.
**Rozwiązanie:** Sprawdź klucz w **Menu → Konto → Ustawienia konta → Klucz API**. Jeśli klucz jest świeży a błąd pozostaje — API myFund.pl jest w fazie beta i dostęp może być ograniczony do wybranych kont.

### ❌ `Portfel nie znaleziony (status 7)`
**Przyczyna:** Nazwa portfela nie zgadza się dokładnie z nazwą na koncie.
**Rozwiązanie:** Sprawdź dokładną nazwę portfela na myFund.pl (wielkość liter, spacje). Nazwa musi być identyczna co do znaku.

### ❌ Narzędzia nie pojawiają się w Claude Desktop
**Przyczyna:** Błąd przy starcie serwera lub niepoprawna składnia JSON w configu.
**Rozwiązanie:** Wejdź w **Settings → Developer** — tam widoczny jest status każdego serwera i log błędów. Najczęściej: literówka w ścieżce lub brakujący przecinek w JSON.

### ❌ Dane są nieaktualne
**Przyczyna:** API myFund.pl cache'uje odpowiedzi przez 5 minut.
**Rozwiązanie:** Odczekaj 5 minut od ostatniej zmiany w portfelu i zapytaj ponownie.

---

## Zmienne środowiskowe

| Zmienna | Wymagana | Opis |
|---|---|---|
| `MYFUND_API_KEY` | ✅ tak | Klucz API z ustawień konta myFund.pl |
| `MYFUND_BASE_URL` | ❌ nie | Nadpisuje base URL (domyślnie `https://myfund.pl/API/v1`) |

## Uwagi techniczne

- API myFund.pl jest w **fazie beta** — dostęp może być ograniczony do wybranych kont
- Odpowiedzi cache'owane **5 minut** po stronie serwera
- Wiele wartości zwracanych jako stringi z prefiksem `+` — serwer parsuje defensywnie
- Błędy logiczne sygnalizowane w `status.code` mimo HTTP 200 (`"0"` = sukces, `"1"` = błąd, `"7"` = portfel nie znaleziony)

## Licencja

MIT

---

---

# 🇬🇧 English version

## Table of contents

- [Tools](#tools)
- [Usage examples](#usage-examples)
- [Requirements](#requirements)
- [Installation](#installation)
- [Portfolio dashboard](#portfolio-dashboard)
- [Analysis skill](#analysis-skill-optional)
- [Troubleshooting](#troubleshooting)
- [Environment variables](#environment-variables)
- [Technical notes](#technical-notes)
- [License](#license)


![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet?logo=anthropic)
![License](https://img.shields.io/badge/license-MIT-green)
![API](https://img.shields.io/badge/myFund.pl-API%20beta-orange)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that exposes your [myFund.pl](https://myfund.pl) investment portfolio data as tools for Claude Desktop.

## Tools

| Tool | Returns |
|---|---|
| `get_portfolio` | Portfolio summary: value, profit, returns for periods (1W / 1M / 3M / 1Y / 5Y…) |
| `get_positions` | List of holdings sorted by value (ticker, type, sector, account, profit) |
| `get_allocation` | Allocation by asset type and by security, with hex colours |
| `get_portfolio_timeseries` | Time series: value / profit / contribution / benchmark / return |

## Usage examples

Once connected, you can ask Claude questions in plain language:

**Summary & performance:**
> "Show me a summary of my Investments portfolio"
> "What is my total profit and year-to-date return?"
> "How has my portfolio value changed over the last 12 months?"

**Holdings & selection:**
> "Which 5 positions have generated the most profit?"
> "Show all positions held in my IKE account"
> "What ETFs do I hold and what is each one's weight in the portfolio?"

**Allocation:**
> "How is my portfolio split by asset type?"
> "Which securities have the largest share of the portfolio?"
> "Am I well diversified across sectors?"

**Time series analysis:**
> "Compare my portfolio return against the WIG benchmark this year"
> "When did my portfolio reach its peak value?"
> "Show daily profit/loss for the last month"

## Requirements

- macOS, Windows or Linux
- Python 3.10 or newer
- Claude Desktop

## Installation

### 1. Download the script

Download [`myfund_mcp_server.py`](myfund_mcp_server.py) and move it to a permanent location, e.g.:

```bash
mkdir -p ~/mcp-servers
mv ~/Downloads/myfund_mcp_server.py ~/mcp-servers/
```

### 2. Install Python 3.12 (if you don't have it)

**macOS:**
```bash
brew install python@3.12
```

**Windows:** download the installer from [python.org](https://python.org).

### 3. Create a virtual environment and install dependencies

**macOS / Linux:**
```bash
/opt/homebrew/bin/python3.12 -m venv ~/mcp-servers/venv
~/mcp-servers/venv/bin/python -m pip install "mcp" httpx
```

**Windows:**
```cmd
python -m venv %USERPROFILE%\mcp-servers\venv
%USERPROFILE%\mcp-servers\venv\Scripts\python -m pip install "mcp" httpx
```

### 4. Get your API key from myFund.pl

Log in → **Menu → Account → Account Settings → API Key** → generate and copy.

> ⚠️ Generating a new key immediately invalidates the previous one.

### 5. Configure Claude Desktop

Open: **Settings → Developer → Edit Config**

Config file location:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add the following block inside `"mcpServers"`:

```json
{
  "mcpServers": {
    "myfund": {
      "command": "/Users/YOUR_USERNAME/mcp-servers/venv/bin/python",
      "args": ["/Users/YOUR_USERNAME/mcp-servers/myfund_mcp_server.py"],
      "env": {
        "MYFUND_API_KEY": "YOUR_API_KEY",
        "MYFUND_PORTFELE": "Portfolio name 1,Portfolio name 2,Portfolio name 3"
      }
    }
  }
}
```

Replace:
- `YOUR_USERNAME` → your system username (on macOS: run `whoami` in Terminal)
- `YOUR_API_KEY` → the key from step 4
- `MYFUND_PORTFELE` → your portfolio names **exactly as shown in your myFund account**, comma-separated (spaces in names are fine). Any number of portfolios. This variable is only needed for the dashboard — individual tools (`get_portfolio` etc.) work without it.

> **Important:** `command` must point to the Python binary **inside the venv** — the one where `mcp` was installed.

### 6. Restart Claude Desktop

Cmd+Q (macOS) or fully close the app, then relaunch.

### 7. Test

In a new chat, type:

> Show me a summary of my portfolio "Your Portfolio Name"

---

## Portfolio dashboard

The server exposes a `show_dashboard` tool that fetches **all** your portfolios at once (from the `MYFUND_PORTFELE` list) and returns visualization-ready data. Claude then builds an **interactive HTML dashboard as an artifact**, opened beside the conversation.

Just ask:

> Show me my portfolio dashboard

The dashboard shows:
- **aggregate view** — total value across all portfolios, combined profit, weighted average return, value-over-time chart, each portfolio's share of the total
- **tabs** — drill into each portfolio: its chart, holdings, and returns

The number of portfolios is arbitrary — it depends on how many names you put in `MYFUND_PORTFELE`. The aggregate return is weighted by portfolio value (not a plain average of percentages).

> **Note:** the dashboard is rendered as an artifact (built by Claude), not an embedded MCP panel — this works regardless of your Claude Desktop version.

## Analysis skill (optional)

Beyond the MCP server, this repository includes an **Agent Skill** — `myfund-portfolio-analysis`. It is a separate layer that teaches Claude *how to analyze* portfolio data: which of the four tools to pick for a given question, how to interpret returns, how to treat missing values, and where the boundaries are (analysis yes, investment advice no).

**The MCP server provides the data — the skill tells Claude how to think about it.** They work together but are independent: the server is configured in `claude_desktop_config.json`, the skill is uploaded in Claude's settings.

### What the skill adds

- Picks the right tool for the question (summary / positions / allocation / time series)
- Names return periods correctly (1W, 1M, 3M, 6M, 1Y, 3Y, 5Y, MtD, YtD)
- Treats missing data as "not available" instead of inventing numbers
- Enforces boundaries: read-only, no investment advice, no transaction analysis that isn't in the data

### How to upload it in Claude

1. Download [`skills/myfund-portfolio-analysis.zip`](skills/myfund-portfolio-analysis.zip)
2. In Claude: **Settings → Capabilities** — make sure **Code execution and file creation** is enabled (the Skills section won't appear otherwise)
3. Go to **Capabilities → Skills** (on some plans: **Customize → Skills**)
4. Click **"+"** → **Upload skill** and select the downloaded ZIP
5. Claude shows the name and description — **toggle it on** to activate
6. Open a **new chat** and ask about your portfolio — the skill loads automatically

> **Note:** the skill requires a working `myfund` MCP server (Installation section above). Without the server, the skill has no data source.

## Troubleshooting

### ❌ `No module named 'mcp'`
**Cause:** Claude is launching the system Python instead of the venv one.
**Fix:** Make sure `command` in the config points to `~/mcp-servers/venv/bin/python`, not the system `python3`.

### ❌ `Response is not valid JSON`
**Cause:** Invalid API key or no access to the myFund.pl beta.
**Fix:** Check your key at **Menu → Account → Account Settings → API Key**. If the key is fresh and the error persists, the myFund.pl API is in beta and access may be restricted to selected accounts.

### ❌ `Portfolio not found (status 7)`
**Cause:** Portfolio name doesn't exactly match the name on your account.
**Fix:** Check the exact portfolio name on myFund.pl (case-sensitive, watch for trailing spaces). The name must match character for character.

### ❌ Tools don't appear in Claude Desktop
**Cause:** Server failed to start, or invalid JSON syntax in the config file.
**Fix:** Go to **Settings → Developer** — each server's status and error log is shown there. Most common causes: typo in a file path, or a missing comma in the JSON.

### ❌ Data appears stale
**Cause:** myFund.pl API caches responses for 5 minutes.
**Fix:** Wait 5 minutes after making changes to your portfolio, then ask again.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `MYFUND_API_KEY` | ✅ yes | API key from myFund.pl account settings |
| `MYFUND_BASE_URL` | ❌ no | Overrides base URL (default: `https://myfund.pl/API/v1`) |

## Technical notes

- myFund.pl API is in **beta** — access may be limited to selected accounts
- Responses are **cached for 5 minutes** server-side
- Many values are returned as strings with a `+` prefix — the server parses them defensively
- Logical errors are signalled in `status.code` despite HTTP 200 (`"0"` = success, `"1"` = error, `"7"` = portfolio not found)

## License

MIT
