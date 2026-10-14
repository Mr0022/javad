# Event-set study (session archive)

Scripts and summary results behind the choice of news calendar for HAR-X / FiLM-TCN.
They were run from a scratch directory, so some carry absolute paths; the layout
here mirrors that directory so relative paths between them still resolve.

| Path | What it is |
|---|---|
| `inventory.csv` | every raw calendar series per currency in the RV sample: release days, first/last date |
| `used.csv` | the series that pass the event loader's `min_days=24` filter, per pair |
| `classify.py`, `classified.csv` | each used series assigned to one of Plihal's sectors (+ CB communication, auctions, political, CFTC) |
| `harx_sets/run_sets*.py` | HAR+DOW / HAR-NEWS / N-HAR on three subsets: HEADLINE (34 USD), PLIHAL (sectors 1-12, 118 USD), ALL (179 USD) |
| `harx_sets/run_agg.py` | HAR-X-agg (pooled release counts, OLS; the model removed in ac9b329) on the same subsets |
| `harx_sets/run_nodow.py` | the same models with a plain HAR core (no weekday terms) |
| `harx_sets/analyse*.py` | MSE tables and Diebold-Mariano tests (HLN-corrected, Newey-West lag h-1) |
| `harx_sets/results2_*.csv`, `results_agg.csv`, `nodow_*.csv` | test-period MSE per pair, horizon, set and model |
| `core/families.py` | the CORE release map (source of `data/event_sets/core_release_map.csv`) |
| `core/build_calendars.py`, `run_core.py` | build the CORE calendars and evaluate them like the other sets |
| `core/eval/core_*.csv` | CORE test-period MSE; `core_merged_*` lists releases merged by the 0.9-correlation dedup |
| `core/times_draft.py`, `times_final.json` | scheduled local release times used in Table 1 |
| `core/make_tables.py`, `table1.md`, `table2.md` | the two Table 1-style tables in `data/event_sets/CORE_EVENT_SET.md` |
| `ext/families_ext.py` | the EXT set: the releases it adds to CORE and the rules for what stays out (speech-like, no macro news, rare) |
| `ext/make_ext.py` | writes `data/event_sets/ext_release_map.csv`, `ext_excluded.csv`, `data/<PAIR>_EVENTS_EXT.csv` and `data/event_sets/EXT_EVENT_SET.md` / `.tex`, checking that every raw series is accounted for |

Test period 2024-01 .. 2025-06 (~385 days per pair); train <= 2023.
