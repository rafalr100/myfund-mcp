#!/usr/bin/env python3
"""
myFund.pl MCP Server
====================

Serwer MCP (Model Context Protocol) udostępniający dane portfela
inwestycyjnego z myFund.pl jako narzędzia dla Claude.

API myFund.pl (v1, beta):
  - REST, read-only
  - Autoryzacja: klucz API jako parametr zapytania (?apiKey=...)
  - Cache po stronie serwera: 5 minut
  - Wiele wartości liczbowych zwracanych jako stringi (czasem z prefiksem '+')

Konfiguracja (zmienne środowiskowe):
  MYFUND_API_KEY   - wymagany, klucz z Menu > Konto > Ustawienia konta > Klucz API
  MYFUND_BASE_URL  - opcjonalny, domyślnie https://myfund.pl

Uruchomienie lokalne:
  pip install "mcp[cli]" httpx
  MYFUND_API_KEY=twoj_klucz python myfund_mcp_server.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# httpx logs the full request URL (which includes ?apiKey=) at INFO level —
# keep it quiet so the API key never lands in stderr.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# --------------------------------------------------------------------------- #
# Konfiguracja
# --------------------------------------------------------------------------- #

BASE_URL = os.environ.get("MYFUND_BASE_URL", "https://myfund.pl/API/v1").rstrip("/")
API_KEY = os.environ.get("MYFUND_API_KEY", "")

# Lista nazw portfeli do widoku zbiorczego (dashboard). Rozdzielona przecinkami.
# Spacje w nazwach są OK (httpx koduje je automatycznie). Przykład:
#   MYFUND_PORTFELE="Emerytalny Rafal,Inwestycje,IKE,Dzieci"
# Jeśli pusta, dashboard poprosi o podanie nazw.
PORTFELE = [p.strip() for p in os.environ.get("MYFUND_PORTFELE", "").split(",") if p.strip()]

# Endpoint API (potwierdzony w dokumentacji OpenAPI): GET /getPortfel.php
# Parametr 'format=json' wymuszany jest dla każdego żądania.
API_PATH = "/getPortfel.php"

# Timeout celowo z zapasem — to API bywa wolne, a odpowiedzi są cache'owane 5 min.
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

mcp = FastMCP("myfund")


# --------------------------------------------------------------------------- #
# Pomocnicy: defensywne parsowanie + wywołanie HTTP
# --------------------------------------------------------------------------- #

_NUM_RE = re.compile(r"^[+\-]?[\d\s.,]+%?$")


def to_number(value: Any) -> float | None:
    """Defensywnie zamienia wartość API na float.

    API zwraca liczby raz jako natywne JSON numbers, raz jako stringi,
    czasem z prefiksem '+', spacjami jako separatorem tysięcy, przecinkiem
    dziesiętnym lub znakiem '%'. Zwraca None, gdy nie da się sparsować.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s or not _NUM_RE.match(s):
        return None

    s = s.replace("%", "").replace(" ", "").replace("\u00a0", "")
    # Jeśli są oba separatory, przyjmij że kropka = tysiące, przecinek = dziesiętny
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


_client: httpx.AsyncClient | None = None

# Short client-side cache: getPortfel.php returns the FULL portfolio payload,
# and several tools hit the same endpoint for the same portfolio. Caching by
# request params for a few seconds avoids re-downloading it on every tool call.
_CACHE_TTL = 60.0
_cache: dict[tuple, tuple[float, dict]] = {}


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
    return _client


async def _call_api(params: dict[str, str]) -> dict[str, Any]:
    """Wykonuje żądanie do API myFund.pl i zwraca sparsowany JSON.

    Podnosi RuntimeError z czytelnym komunikatem przy problemach
    sieciowych, błędach HTTP lub niepoprawnym JSON-ie.
    """
    if not API_KEY:
        raise RuntimeError(
            "Brak klucza API. Ustaw zmienną środowiskową MYFUND_API_KEY "
            "(klucz znajdziesz w Menu > Konto > Ustawienia konta > Klucz API)."
        )

    query = {"apiKey": API_KEY, "format": "json", **params}

    cache_key = tuple(sorted(params.items()))
    hit = _cache.get(cache_key)
    if hit and time.monotonic() - hit[0] < _CACHE_TTL:
        return hit[1]

    try:
        resp = await _get_client().get(f"{BASE_URL}{API_PATH}", params=query)
    except httpx.RequestError as exc:
        raise RuntimeError(f"Błąd połączenia z myFund.pl: {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(
            f"myFund.pl zwrócił HTTP {resp.status_code}. "
            f"Sprawdź klucz API i nazwę portfela."
        )

    try:
        data = resp.json()
    except ValueError as exc:
        # Częsty przypadek: API w becie zwraca stronę HTML zamiast JSON,
        # gdy klucz jest niepoprawny lub dostęp nie został przyznany.
        raise RuntimeError(
            "Odpowiedź nie jest poprawnym JSON-em. Najczęstsze przyczyny: "
            "niepoprawny klucz API, brak dostępu do bety API, lub błędna "
            "nazwa portfela."
        ) from exc

    # API sygnalizuje błędy logiczne w polu status.code mimo HTTP 200.
    # Wg dokumentacji: "0" = sukces, "1" = błąd, "7" = portfel nie znaleziony.
    status = data.get("status") or {}
    code = str(status.get("code", "")).strip()
    if code not in ("", "0"):
        msg = status.get("text") or "brak szczegółów"
        if code == "7":
            raise RuntimeError(
                f"Portfel nie znaleziony (status 7). Sprawdź, czy nazwa portfela "
                f"jest dokładnie taka jak na koncie. Komunikat API: {msg}"
            )
        raise RuntimeError(f"myFund.pl status.code={code}: {msg}")

    _cache[cache_key] = (time.monotonic(), data)
    return data


def _series_summary(series: dict[str, Any] | None) -> dict[str, Any]:
    """Skraca szereg czasowy do zwięzłego podsumowania.

    Szeregi (np. wartoscWCzasie) potrafią mieć setki punktów dziennych.
    Zwracanie ich w całości zalewa kontekst, więc domyślnie redukujemy
    je do: liczby punktów, pierwszego i ostatniego punktu oraz zakresu dat.
    """
    if not isinstance(series, dict) or not series:
        return {"punkty": 0}

    keys = sorted(series.keys())
    first_k, last_k = keys[0], keys[-1]
    return {
        "punkty": len(keys),
        "od": first_k,
        "do": last_k,
        "pierwsza_wartosc": to_number(series[first_k]),
        "ostatnia_wartosc": to_number(series[last_k]),
    }


# --------------------------------------------------------------------------- #
# Narzędzia MCP
# --------------------------------------------------------------------------- #


@mcp.tool()
async def get_portfolio(portfel: str) -> dict[str, Any]:
    """Pobiera podsumowanie portfela inwestycyjnego z myFund.pl.

    Zwraca zagregowane metryki (wiersz "Cały portfel" z dashboardu):
    wartość bieżącą, wkład własny, zysk/stratę i stopy zwrotu za okresy.
    Liczby są sparsowane do typów natywnych. Szeregi czasowe są tutaj
    pominięte — użyj get_portfolio_timeseries, jeśli ich potrzebujesz.

    Args:
        portfel: Nazwa portfela dokładnie tak, jak wyświetla się na koncie
                 (np. "Mój Portfel").
    """
    data = await _call_api({"portfel": portfel})
    summary = data.get("portfel") or {}

    return {
        "nazwa": summary.get("nazwa") or portfel,
        "waluta": summary.get("waluta"),
        "data": summary.get("data"),
        "wartosc": to_number(summary.get("wartosc")),
        "zysk": to_number(summary.get("zysk")),
        "udzial": to_number(summary.get("udzial")),
        "zmiana_dzienna": to_number(summary.get("zmianaDzienna")),
        "zysk_dzienny": to_number(summary.get("zyskDzienny")),
        "liczba_walorow": summary.get("tickersCount"),
        # Okresowe stopy zwrotu — w schemacie to stringi (mogą mieć prefiks '+').
        "stopy_zwrotu": {
            "1T": to_number(summary.get("zmianaW")),
            "2T": to_number(summary.get("zmiana2W")),
            "1M": to_number(summary.get("zmianaM")),
            "3M": to_number(summary.get("zmiana3M")),
            "6M": to_number(summary.get("zmiana6M")),
            "1R": to_number(summary.get("zmianaR")),
            "3R": to_number(summary.get("zmiana3R")),
            "5R": to_number(summary.get("zmiana5R")),
            "1M_do_dzis": to_number(summary.get("zmianaMdD")),
            "1R_do_dzis": to_number(summary.get("zmianaRdD")),
        },
    }


@mcp.tool()
async def get_positions(portfel: str) -> dict[str, Any]:
    """Pobiera listę pozycji (walorów) w portfelu myFund.pl.

    Zwraca poszczególne pozycje z polem tickers, z liczbami sparsowanymi
    defensywnie.

    Args:
        portfel: Nazwa portfela tak jak na koncie użytkownika.
    """
    data = await _call_api({"portfel": portfel})
    tickers = data.get("tickers") or {}

    positions: list[dict[str, Any]] = []
    for pid, t in tickers.items():
        if not isinstance(t, dict):
            continue
        positions.append(
            {
                "id": pid,
                "nazwa": t.get("nazwa"),
                "ticker": t.get("tickerClear"),
                "typ": t.get("typ"),
                "sektor": t.get("sektor"),
                "konto": t.get("kontoInvName"),
                "liczba_jednostek": to_number(t.get("liczbaJednostek")),
                "cena_zakupu": to_number(t.get("cenaZakupu")),
                "close": to_number(t.get("close")),
                "wartosc": to_number(t.get("wartosc")),
                "udzial_proc": to_number(t.get("udzial")),
                "zysk": to_number(t.get("zysk")),
                "stopa_zwrotu": to_number(t.get("zmiana")),
                "zmiana_dzienna": to_number(t.get("zmianaDzienna")),
            }
        )

    positions.sort(key=lambda p: (p["wartosc"] or 0), reverse=True)
    return {"nazwa": portfel, "liczba_pozycji": len(positions), "pozycje": positions}


@mcp.tool()
async def get_allocation(portfel: str) -> dict[str, Any]:
    """Pobiera alokację portfela myFund.pl wg typu aktywów i wg walorów.

    Łączy pola struktura (podział wg kategorii aktywów, np. "ETFs - international")
    oraz strukturaWalory (udział procentowy per walor) wraz z odpowiadającymi
    im kolorami. Kwoty i udziały są sparsowane do liczb.

    Args:
        portfel: Nazwa portfela tak jak na koncie użytkownika.
    """
    data = await _call_api({"portfel": portfel})

    struktura = data.get("struktura") or {}
    struktura_kolor = data.get("strukturaKolor") or {}
    walory = data.get("strukturaWalory") or {}
    walory_kolor = data.get("strukturaWaloryKolor") or {}

    wg_typu = [
        {
            "kategoria": k,
            "kwota": to_number(v),
            "kolor": struktura_kolor.get(k),
        }
        for k, v in struktura.items()
    ]
    wg_typu.sort(key=lambda x: (x["kwota"] or 0), reverse=True)

    wg_waloru = [
        {
            "walor": k,
            "udzial_proc": to_number(v),
            "kolor": walory_kolor.get(k),
        }
        for k, v in walory.items()
    ]
    wg_waloru.sort(key=lambda x: (x["udzial_proc"] or 0), reverse=True)

    return {"nazwa": portfel, "wg_typu_aktywow": wg_typu, "wg_waloru": wg_waloru}


@mcp.tool()
async def get_portfolio_timeseries(
    portfel: str,
    seria: str = "wartoscWCzasie",
    pelne_dane: bool = False,
) -> dict[str, Any]:
    """Pobiera szereg czasowy portfela myFund.pl.

    Domyślnie zwraca zwięzłe podsumowanie (liczba punktów, zakres dat,
    pierwsza i ostatnia wartość), żeby nie zalewać kontekstu setkami punktów
    dziennych. Ustaw pelne_dane=True, aby otrzymać wszystkie punkty.

    Args:
        portfel: Nazwa portfela tak jak na koncie użytkownika.
        seria: Która seria. Dozwolone: "zyskWCzasie", "wartoscWCzasie",
               "wkladWCzasie", "benchWCzasie", "stopaZwrotuWCzasie",
               "zmianaDzienna".
        pelne_dane: Gdy True, zwraca pełny szereg zamiast podsumowania.
    """
    dozwolone = {
        "zyskWCzasie",
        "wartoscWCzasie",
        "wkladWCzasie",
        "benchWCzasie",
        "stopaZwrotuWCzasie",
        "zmianaDzienna",
    }
    if seria not in dozwolone:
        raise RuntimeError(
            f"Nieznana seria '{seria}'. Dozwolone: {', '.join(sorted(dozwolone))}."
        )

    data = await _call_api({"portfel": portfel})
    series = data.get(seria) or {}

    if pelne_dane:
        parsed = {k: to_number(v) for k, v in series.items()}
        return {"nazwa": portfel, "seria": seria, "dane": parsed}

    return {"nazwa": portfel, "seria": seria, **_series_summary(series)}


# --------------------------------------------------------------------------- #
# Dashboard wielu portfeli (MCP App)
# --------------------------------------------------------------------------- #


async def _collect_portfolios(names: list[str]) -> dict[str, Any]:
    """Pobiera wiele portfeli i buduje strukturę dla dashboardu.

    Dla każdej nazwy wykonuje osobne wywołanie getPortfel.php (API nie ma
    endpointu listującego), normalizuje dane i liczy widok zbiorczy.
    Portfele, których nie udało się pobrać, trafiają do listy 'errors'
    zamiast przerywać całość.
    """
    # Fetch all portfolios concurrently — the beta API is slow and has no
    # list endpoint, so parallel per-portfolio calls cut dashboard latency.
    results = await asyncio.gather(
        *[_call_api({"portfel": n}) for n in names],
        return_exceptions=True,
    )
    portfolios: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for name, data in zip(names, results):
        if isinstance(data, Exception):
            errors.append({"nazwa": name, "blad": str(data)})
            continue

        summary = data.get("portfel") or {}
        tickers = data.get("tickers") or {}

        holdings = []
        for t in tickers.values():
            if not isinstance(t, dict):
                continue
            holdings.append({
                "nazwa": t.get("nazwa"),
                "ticker": t.get("tickerClear"),
                "typ": t.get("typ"),
                "wartosc": to_number(t.get("wartosc")),
                "udzial": to_number(t.get("udzial")),
                "zysk": to_number(t.get("zysk")),
                "zmiana": to_number(t.get("zmiana")),
            })
        holdings.sort(key=lambda h: (h["wartosc"] or 0), reverse=True)

        wartosc_w_czasie = {k: to_number(v) for k, v in (data.get("wartoscWCzasie") or {}).items()}

        portfolios.append({
            "nazwa": summary.get("nazwa") or name,
            "wartosc": to_number(summary.get("wartosc")),
            "zysk": to_number(summary.get("zysk")),
            "zmiana_dzienna": to_number(summary.get("zmianaDzienna")),
            "zysk_dzienny": to_number(summary.get("zyskDzienny")),
            "stopa_zwrotu_1r": to_number(summary.get("zmianaR")),
            "liczba_pozycji": summary.get("tickersCount") or len(holdings),
            "waluta": summary.get("waluta"),
            "pozycje": holdings,
            "wartosc_w_czasie": wartosc_w_czasie,
        })

    # Widok zbiorczy
    total_value = sum((p["wartosc"] or 0) for p in portfolios)
    total_profit = sum((p["zysk"] or 0) for p in portfolios)
    total_pos = sum((p["liczba_pozycji"] or 0) for p in portfolios)
    total_daily = sum((p["zysk_dzienny"] or 0) for p in portfolios)
    # Stopa zwrotu zbiorcza: średnia ważona wartością (nie zwykła średnia!)
    if total_value > 0:
        agg_return = sum((p["stopa_zwrotu_1r"] or 0) * (p["wartosc"] or 0) for p in portfolios) / total_value
    else:
        agg_return = None

    return {
        "portfele": portfolios,
        "errors": errors,
        "zbiorczo": {
            "wartosc": total_value,
            "zysk": total_profit,
            "zysk_dzienny": total_daily,
            "liczba_pozycji": total_pos,
            "liczba_portfeli": len(portfolios),
            "stopa_zwrotu_1r_wazona": agg_return,
            "waluta": portfolios[0]["waluta"] if portfolios else "PLN",
        },
    }


@mcp.tool()
async def show_dashboard(portfele: str = "") -> dict[str, Any]:
    """Pobiera dane wszystkich portfeli i zwraca je w formie gotowej do
    zbudowania dashboardu jako artefakt HTML.

    Zwraca dane zbiorcze (suma wartości, zysku, średnia ważona stopa zwrotu)
    oraz pełną listę portfeli z pozycjami i szeregami czasowymi. Po wywołaniu
    tego narzędzia zbuduj z tych danych interaktywny dashboard jako artefakt
    HTML (widok zbiorczy + zakładki na poszczególne portfele).

    Args:
        portfele: Opcjonalnie — nazwy portfeli rozdzielone przecinkami.
                  Jeśli pominięte, używa listy z MYFUND_PORTFELE.
    """
    names = [p.strip() for p in portfele.split(",") if p.strip()] or PORTFELE
    if not names:
        raise RuntimeError(
            "Nie podano portfeli. Ustaw MYFUND_PORTFELE w konfiguracji "
            "(np. \"Emerytalny Rafal,Inwestycje,IKE\") lub przekaż argument "
            "portfele=\"nazwa1,nazwa2\"."
        )

    return await _collect_portfolios(names)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
