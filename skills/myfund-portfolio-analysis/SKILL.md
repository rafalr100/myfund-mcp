---
name: myfund-portfolio-analysis
description: Analyzes myFund.pl investment portfolio data fetched via the myfund MCP server. Use when the user asks about their investment portfolio value, returns, holdings, allocation, sector or account breakdown, benchmark comparison, or performance over time — and the myfund MCP tools (get_portfolio, get_positions, get_allocation, get_portfolio_timeseries) are available.
---

# myFund Portfolio Analysis

This skill guides how to fetch and analyze investment portfolio data from
myFund.pl using the `myfund` MCP server. It is **read-only** and focused on
analysis — it never executes trades, rebalances, or modifies any account.

## Available tools

The `myfund` MCP server exposes four tools. Pick the smallest set that answers
the question:

| Tool | Use it for |
|---|---|
| `get_portfolio` | Total value, profit, currency, daily change, and period returns (1W / 1M / 3M / 6M / 1Y / 3Y / 5Y, plus month-to-date and year-to-date) |
| `get_positions` | Individual holdings — ticker, name, type, sector, account, units, value, weight, profit, return |
| `get_allocation` | Breakdown by asset type and by security (with display colours) |
| `get_portfolio_timeseries` | Daily series: value, profit, contribution, benchmark, return, or daily change |

## Core workflow

1. **Identify the portfolio name.** Every tool needs the `portfel` argument —
   the exact portfolio name as shown on the user's myFund account. If the user
   hasn't given it and you don't know it from context, ask once before calling
   any tool. Do not guess.
2. **Check status before analyzing.** If a tool raises an error mentioning
   `status 7`, the portfolio name is wrong — report it plainly and ask for the
   exact name rather than retrying with variations.
3. **Fetch only what you need.** A question about total value needs only
   `get_portfolio`; don't pull positions or time series unless the question
   requires them.
4. **Analyze, then answer.** Lead with the direct answer to the question, then
   supporting detail. Keep it concise.

## Handling the data correctly

- **Numbers may arrive as strings**, sometimes with a `+` prefix or spaces as
  thousands separators (e.g. `"+25,43%"`, `"1 234,56"`). The MCP server already
  parses these into native numbers in its structured output — use those parsed
  fields, and treat any `null` as "not available" rather than zero.
- **Returns are percentages.** The `stopy_zwrotu` block in `get_portfolio` holds
  period returns (`1T`=1 week, `1M`, `3M`, `6M`, `1R`=1 year, `3R`, `5R`,
  `1M_do_dzis`=month-to-date, `1R_do_dzis`=year-to-date). State the period
  explicitly when quoting a return.
- **The `data` field may be `&nbsp;`** when a date is unavailable — treat it as
  missing, don't display the raw entity.
- **Time series are large.** `get_portfolio_timeseries` returns a summary by
  default (point count, date range, first/last value). Only request
  `pelne_dane=True` when the user genuinely needs every daily point, e.g. to
  find a peak or plot a full curve.

## What this skill supports

- Portfolio overview: total value, profit/loss, currency, daily change, returns
- Holdings analysis: ranking by value, weight, profit, or return; filtering or
  grouping by sector, investment account, or asset type
- Allocation analysis: concentration, diversification, largest positions
- Performance over time: value/return trajectory, peak/trough, month- or
  year-to-date progression
- Benchmark comparison: portfolio return vs. the configured benchmark, when
  benchmark series data is present

## What this skill does NOT do

- **No trading or account actions** — no buy/sell, rebalancing, deposits, or
  withdrawals. The API is read-only.
- **No financial advice.** Present data and neutral analysis. Do not tell the
  user what to buy or sell, or whether an investment is "good." If asked for a
  recommendation, share the relevant figures and note that the decision is
  theirs.
- **No transaction history analysis** unless that data is actually present in
  the response — the portfolio endpoint does not return individual transactions.
- **No fabricated figures.** If a value is missing or `null`, say so. Never
  estimate or fill gaps with plausible-looking numbers.

## Caching note

myFund.pl caches API responses for 5 minutes. If the user just made a change in
their portfolio and the numbers look stale, mention that data may be up to
5 minutes behind rather than re-fetching repeatedly.

## Example questions and which tool answers them

- "What's my portfolio worth?" → `get_portfolio`
- "What's my year-to-date return?" → `get_portfolio` (`stopy_zwrotu.1R_do_dzis`)
- "Which 5 holdings made the most profit?" → `get_positions`, sort by profit
- "How am I split across asset types?" → `get_allocation`
- "Show all positions in my IKE account" → `get_positions`, filter by `konto`
- "How did my portfolio value move over the last 6 months?" →
  `get_portfolio_timeseries` (series `wartoscWCzasie`)
- "Did I beat my benchmark this year?" → `get_portfolio_timeseries`
  (series `stopaZwrotuWCzasie` and `benchWCzasie`)
