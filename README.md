# Ligue 1 2026/27 dashboard — DIN Mercado

Standalone, mobile-responsive static dashboard for the French Ligue 1 McDonald's 2026/27 season. This is a distinct league project: no Brazilian Série A or other-league results are included.

## Data cut and coverage

- Cutoff: **2026-10-18 10:54 America/Sao_Paulo (UTC−03:00)**.
- Official LFP schedule contains 18 clubs, 9 fixtures per round, and labels rounds 1–8.
- The published record set contains **58 confirmed finals**: 9 fixtures each from rounds 1–6 (54), plus 4 final scores in round 7.
- It contains **14 fixtures without a confirmed final score** at the cutoff: the 5 still scheduled for round 7 and 9 round-8 fixtures. They are excluded from standings, recent form, rankings and the projection sample.
- Actual played totals: PSG, LOSC, RC Lens, Brest, Toulouse FC, Strasbourg, LE Mans FC and Troyes have 7; the other 10 clubs have 6.
- `validation.json` records the checks. Scores feed a fresh recomputation of Pld, W-D-L, GF, GA, GD and points; all 18 record lines match the current LFP table. The official order is retained only for tied numerical rows. The 18-row independent WorldFootball table after round 6 matches the recomputed pre-round-7 line for every club; the 4 new round-7 scores were corroborated by independent reports.

## Important schedule caveat

The LFP calendar view and independent WorldFootball schedule disagree on some date/time labels (one-day and/or one-hour shifts; the LFP page extract does not identify its display timezone). The page does **not** normalize those entries or guess a kickoff. It shows the 18 October date only for the remaining round-7 games, where both listings agree, and withholds disputed kickoff times; for round 8 it shows the verified fixture and matchday while withholding the disputed calendar date/time. Match cards link to the official LFP match sheet. Re-check the official card for any live planning.

## Competition format and zones

- The official LFP table lists 18 clubs. The LFP 2026/27 calendar announcement identifies the 34th/final matchday.
- The European stripes are explicitly **provisional**. LFP confirms the French 2026/27 allocation: 1–3 UCL direct, 4 UCL qualifying, 5–6 Europa League, 7 Conference League qualifying play-off. This is a reference only, not an official 2027/28 allocation. The UEFA access-list page showed no data when checked, so the panel does not extrapolate next season's places. See `source_snapshots/official_competition_rules_2026-10-18.md`.
- Relegation stripes are explicitly **provisional**: the LFP confirms a 16th-place two-leg play-off in its 2025/26 explainer, but the specific 2026/27 competition-regulation PDF was not located. The 17th–18th direct-drop display follows the 18-club format description but is not presented as an independently verified 2026/27 regulation.

## Files

- `index.html` — ready-to-host single-page app; all JS, CSS and the data snapshot are embedded.
- `data.json` — match list plus standings recomputed from final scores.
- `ligue1_2026_27_matches.csv` — same fixture list in CSV form, including official match IDs.
- `validation.json` — counts and cross-check result.
- `index.template.html`, `build_site.py` — source template and rebuild of the embedded-data HTML from `data.json`.
- `rebuild.py` — regenerate the JSON and page from the included CSV without accessing another league's files.
- `validate_data.py` — repeatable local provenance/cross-check script. It reads the included `source_snapshots/worldfootball_round6_2026-10-18.md`; current LFP table figures and round-7 corroborations are explicitly recorded in the validator and source log.

## Refresh / deployment path

From the root of `din-mercado-ligue1-2026-27`, after verifying the latest LFP results and fixture edits:

```bash
python3 rebuild.py
```

This reads only `ligue1_2026_27_matches.csv`, deterministically rewrites `data.json`, and regenerates `index.html`. Review the diff, run `python3 validate_data.py` (which refreshes `validation.json`), then commit/push to the repository's `main` branch; GitHub Pages is configured from `/` on `main`. Keep the included dated source snapshot and update `sources.json` / validation evidence whenever source data is refreshed. Do not mark a game final without an official final score. This task did not create a scheduled job or cron.

## Methods

- Only official LFP rows that include an actual score are marked final. Scheduled cards without a final score remain blank.
- The league table and home/away splits are independently recomputed from those scores; there is no imported table, inferred score, odds or projection embedded as a result. Overview KPIs are computed from the 58 finals: total goals and average, BTTS and Over 2.5 numerator/denominator/rate, and home/draw/away outcomes. `validate_data.py` asserts the aggregate values.
- Last-five form is ordered by competition round, not by disputed calendar labels.
- The projection uses a deliberately simple equal-weight average of the relevant home attack/away concession and away attack/home concession rates, then independent Poisson probabilities (0–9 goals). It is shown only when both side-specific samples include at least two games. It is explanatory, small-sample and not betting advice.
- BTTS and Over 2.5 rankings show successes divided by matches; home and away views use only games at that venue.

## Sources

**Primary (Ligue 1 / LFP / France):**

- [Official LFP calendar and results](https://ligue1.com/fr/calendar/ligue1) — round filter 1–8.
- [Official LFP 2026/27 standings](https://ligue1.com/fr/competitions/ligue1mcdonalds/standings).
- [LFP season calendar announcement](https://www.lfp.fr/article/ligue-1-mc-donald-s-le-calendrier-de-la-saison-2026-2027) — season ends on round 34.
- [Ligue 1: French clubs in 2026/27 European competitions](https://ligue1.com/en/articles/l1_article_5609-2026-27-everything-you-need-to-know-about-european-competitions).
- [LFP 2025/26 playoff dates and format](https://ligue1.com/fr/articles/l1_article_4680-barrages-25-26-toutes-les-dates).

**Independent checks:**

- [WorldFootball: Ligue 1 results and standings](https://www.worldfootball.net/competition/co71/france-ligue-1/results-and-standings/) — independent 18-team table after round 6 and matchday results/schedule.
- [Reuters: PSG win at Strasbourg, 17 October 2026](https://www.reuters.com/sports/soccer/dembele-atones-penalty-miss-psg-win-strasbourg-2026-10-17/).
- [Le Parisien: Lille–Brest and Troyes–Lens, 17 October 2026](https://www.leparisien.fr/sports/football/ligue-1/ligue-1-lille-bute-sur-brest-et-ne-repasse-pas-devant-le-psg-thauvin-brille-avec-lens-17-10-2026-LMZTCLZKWVC4XHRVGQX3VWTM2Y.php).
- [Maxifoot: Ligue 1 2026/27 results and standings](https://www.maxifoot.fr/resultat-ligue-1-france.htm) — includes Le Mans–Toulouse.
- [MatchEnDirect format explainer](https://www.matchendirect.com/competition/ligue-1-mcdonalds/) — 18-club promotion/relegation format.
