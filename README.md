# DIN Mercado · Ligue 1 2026/27

Interactive mobile dashboard for Ligue 1 McDonald's only. GitHub Actions keeps this repository's existing Pages URL updated in place.

## Official refresh and safety checks

- Official full-season calendar: LFP `championship-calendar/1?season=2026`; it must expose all 34 rounds and 306 unique official match IDs.
- Official match sheets: LFP `championship-match/{id}`; only `period=fullTime` contributes a score. Unknown, live, postponed, cancelled or otherwise nonfinal statuses never receive inferred scores.
- Official table: current LFP general standings API. Final-only played, W-D-L, goals and points must match all 18 clubs.
- Independent cross-check: each official final must match an ESPN `STATUS_FULL_TIME` event, and the table recomputed from ESPN's own scores must also match all 18 clubs.
- A missing fixture, score mismatch, incomplete calendar or standings discrepancy stops the run before the dashboard is rebuilt/committed.
- Known official venue discrepancy: the current LFP API/match sheet lists Rennes as home for both Rennes–PSG fixtures; the completed R1 2–2 at Roazhon Park is independently confirmed by ESPN, while the LFP season-calendar PDF lists PSG home for R1. The dashboard preserves the current match-sheet orientation, displays this note and fails closed if the affected home/away pattern changes.

## Automatic refresh

GitHub Actions runs daily at **06:10 America/Sao_Paulo (09:10 UTC)** and supports manual dispatch. It fetches the full calendar and all match sheets, validates the current official table, cross-checks final scores and the ESPN-derived table, then rebuilds the JSON/HTML and commits only after every check passes. When a check fails, the existing public page is left unchanged. The workflow writes to the same repository and root `index.html`, preserving the current URL.

The exact cutoff and counts are regenerated in `validation.json`, `validation.txt`, `sources.json`, `data.json` and the page on each validated refresh.

## Local equivalent

```sh
python3 refresh_ligue1.py
python3 rebuild.py
python3 validate_data.py
```

- Repository: `wildsonfranciscosilva1986-coder/din-mercado-ligue1-2026-27`
- Branch/path: `main` / repository root `index.html`
- Existing site: https://wildsonfranciscosilva1986-coder.github.io/din-mercado-ligue1-2026-27/

The 1-X-2/goal projections are small-sample descriptive estimates, not calibrated forecasts or betting advice.
