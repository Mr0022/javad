# EXT news-announcement set

Release-level calendar of scheduled announcements for the three pairs (EUR/USD, GBP/USD,
AUD/USD): every CORE release ([CORE_EVENT_SET.md](CORE_EVENT_SET.md)), unchanged, plus 76
releases that CORE's scope, geography and continuity rules left out. Built by
`analysis/event_set_study/ext/make_ext.py` into `data/event_sets/ext_release_map.csv` and
`data/<PAIR>_EVENTS_EXT.csv`; `python scripts/build_core_events.py --set EXT` rebuilds the
calendars from the map. Every raw series that is in no EXT release is listed, with the
reason, in `data/event_sets/ext_excluded.csv`.

Indicator columns the event loader builds from each calendar (`evt_*`, at its default
`min_days=24`; the loader adds `n_events` and one `n_events_<cur>` per currency):

| Calendar | EUR/USD | GBP/USD | AUD/USD |
|---|---|---|---|
| raw, one column per published series (`<PAIR>_EVENTS.csv`) | 319 | 267 | 250 |
| CORE (`<PAIR>_EVENTS_CORE.csv`) | 89 | 71 | 69 |
| **EXT** (`<PAIR>_EVENTS_EXT.csv`) | **140** | **113** | **114** |

The gap between EXT and the raw count is speech-like and other left-out series (below) and,
mostly, series of one release published on the same days (CPI MoM, YoY and core; NFP,
unemployment rate and earnings; flash and final PMIs), which would add identical columns.

## Selection rules

- **X1 Scope.** Every scheduled release in the calendars, CFTC positioning reports, Treasury bill auctions and ECB meetings without a policy decision included, except speech-like communication: speeches, testimony and parliamentary hearings, press conferences, and the Jackson Hole symposium (the decision, statement or report they accompany stays in, so no announcement day is lost). Replaces CORE's R1.
- **X2 Geography.** No restriction: sub-national releases (regional Fed surveys, Chicago PMI, ISM-New York, German state CPIs) are in. Replaces R2.
- **X3 Training coverage.** A release enters if it is first published before 1 Jan 2022, so it occurs in the deep models' training years (2012–2021); releases that stop before 2025 stay in. Replaces R3. It drops the ABS monthly CPI indicator (from Sep-2022) and the Ai Group Industry Index (from Feb-2023).
- **X4 Release as the unit.** As R4: all series published in one statistical release form one announcement, dated on every day any of them is published.
- **X5 Frequency.** As R5: at least 24 announcements in the sample.

The 139 CORE releases enter unchanged, so each CORE indicator is also an EXT indicator with identical values. Series of a CORE release that CORE's R3 left out of its member list (ISM sub-indices, U6, Michigan inflation expectations, ...) are published on that release's days and stay covered by it.

Sample: 12 Jan 2012 – 30 Jun 2025 (the RV sample).

## What is left out

Raw calendar series in no EXT release, by reason (USD counted once; all series in the sample, rare ones included):

| Reason | USD | EUR | GBP | AUD | Total |
|---|---|---|---|---|---|
| speech-like | 66 | 34 | 35 | 10 | 145 |
| rare | 43 | 79 | 31 | 7 | 160 |
| first published after 2021 | 0 | 0 | 0 | 7 | 7 |
| **left out** | **109** | **113** | **66** | **24** | **312** |
| *covered by a CORE release (not left out)* | 24 | 4 | 4 | 1 | 33 |

- **speech-like**: every central-bank and political speech, testimony and hearing (e.g. *Fed's Williams speech*, *Fed's Chair Powell testifies*, *BoE Monetary Policy Report Hearings*), and the FOMC and ECB press conferences.
- **rare**: fewer than 24 announcements — annual and one-off events (elections, summits on a single issue, budget days, stress tests) and series that ran only briefly.
- **first published after 2021**: ABS Monthly CPI Indicator (from Sep-2022); Ai Group Industry Index (from Feb-2023).

## Table 1

**Table 1: U.S. (USD) News Announcements**

| Announcement | Obs.¹ | Dates² | Announcement Time (ET)³ |
|---|---|---|---|
| ***Quarterly Announcements*** | | | |
| 1- GDP (advance, second, third) | 161 | 01/27/12–06/26/25 | 8:30 |
| 2- Employment Cost Index | 54 | 01/31/12–04/30/25 | 8:30 |
| 3- Productivity and Unit Labor Costs | 108 | 02/02/12–06/05/25 | 8:30 |
| 4- Current Account | 54 | 03/14/12–06/24/25 | 8:30 |
| 5- Senior Loan Officer Survey | 52 | 01/30/12–05/12/25 | 14:00 |
| ***Monthly Announcements*** | | | |
| *Real Activity* | | | |
| 6- Employment Situation (Nonfarm Payrolls) | 161 | 02/03/12–06/06/25 | 8:30 |
| 7- ADP Employment Change | 159 | 02/01/12–06/04/25 | 8:15 |
| 8- Challenger Job Cuts | 161 | 02/02/12–06/05/25 | 7:30 |
| 9- JOLTS Job Openings | 139 | 12/10/13–06/03/25 | 10:00 |
| 10- Industrial Production and Capacity Utilization | 162 | 01/18/12–06/17/25 | 9:15 |
| 11- Labor Market Conditions Index † | 43 | 01/06/14–07/10/17 | 10:00 |
| *Consumption* | | | |
| 12- Retail Sales | 163 | 01/12/12–06/17/25 | 8:30 |
| 13- Total Vehicle Sales | 161 | 02/01/12–06/03/25 | varies (afternoon) |
| 14- Personal Income and Outlays (incl. PCE prices) | 161 | 01/30/12–06/27/25 | 8:30 |
| 15- New Home Sales | 161 | 01/26/12–06/25/25 | 10:00 |
| 16- Existing Home Sales | 162 | 01/20/12–06/23/25 | 10:00 |
| *Investment* | | | |
| 17- Business Inventories | 162 | 01/12/12–06/17/25 | 10:00 |
| 18- Wholesale Inventories | 263 | 02/09/12–06/26/25 | 10:00⁽1⁾ |
| 19- Durable Goods Orders | 162 | 01/26/12–06/26/25 | 8:30 |
| 20- Factory Orders | 160 | 02/03/12–06/03/25 | 10:00 |
| 21- Construction Spending | 160 | 02/01/12–06/02/25 | 10:00 |
| *Government Purchases* | | | |
| 22- Monthly Treasury Budget Statement | 162 | 01/12/12–06/11/25 | 14:00 |
| *Net Exports* | | | |
| 23- Trade Balance (goods and services) | 162 | 01/13/12–06/05/25 | 8:30 |
| 24- TIC Capital Flows | 162 | 01/18/12–06/18/25 | 16:00 |
| 25- Advance Goods Trade Balance † | 173 | 07/30/15–06/26/25 | 8:30⁽2⁾ |
| *Prices* | | | |
| 26- S&P/Case-Shiller Home Prices | 162 | 01/31/12–06/24/25 | 9:00 |
| 27- FHFA House Price Index | 162 | 01/25/12–06/24/25 | 9:00 |
| 28- Consumer Price Index | 163 | 01/19/12–06/11/25 | 8:30 |
| 29- Producer Price Index | 162 | 01/18/12–06/12/25 | 8:30 |
| 30- Import and Export Prices | 162 | 01/13/12–06/17/25 | 8:30 |
| *Forward-Looking* | | | |
| 31- Housing Starts and Building Permits | 161 | 01/19/12–06/18/25 | 8:30 |
| 32- Pending Home Sales | 163 | 01/25/12–06/26/25 | 10:00 |
| 33- NAHB Housing Market Index | 162 | 01/18/12–06/17/25 | 10:00 |
| 34- ISM Manufacturing PMI | 161 | 02/01/12–06/02/25 | 10:00 |
| 35- ISM Services PMI | 161 | 02/03/12–06/04/25 | 10:00 |
| 36- S&P Global Manufacturing PMI (flash and final) | 316 | 04/25/12–06/23/25 | 9:45 flash / 9:45 final |
| 37- S&P Global Services/Composite PMI (flash and final) | 277 | 12/04/13–06/23/25 | 9:45 flash / 9:45 final |
| 38- Consumer Confidence (Conference Board) | 153 | 01/31/12–06/24/25 | 10:00 |
| 39- Michigan Consumer Sentiment (prelim. and final) | 324 | 01/13/12–06/27/25 | 10:00 |
| 40- NFIB Small Business Optimism | 161 | 02/14/12–06/10/25 | 6:00 |
| 41- RCM/TIPP Economic Optimism | 161 | 02/07/12–06/03/25 | 10:00 |
| 42- Chicago Fed National Activity Index | 161 | 01/26/12–06/26/25 | 8:30 |
| 43- Chicago PMI † | 162 | 01/31/12–06/30/25 | 9:45 |
| 44- Dallas Fed Manufacturing Survey † | 161 | 02/27/12–06/30/25 | 10:30 |
| 45- Kansas City Fed Manufacturing Survey † | 160 | 03/29/12–06/26/25 | 11:00 |
| 46- NY Empire State Manufacturing Survey † | 162 | 01/17/12–06/16/25 | 8:30 |
| 47- Philadelphia Fed Manufacturing Survey † | 162 | 01/19/12–06/20/25 | 8:30 |
| 48- Richmond Fed Manufacturing Survey † | 162 | 01/24/12–06/24/25 | 10:00 |
| 49- ISM-New York Business Conditions † | 109 | 04/03/12–04/05/21 | — |
| *Money and Credit* | | | |
| 50- Consumer Credit | 161 | 02/07/12–06/06/25 | 15:00 |
| ***Monetary Policy Decisions*** | | | |
| 51- FOMC Rate Decision (statement, projections) | 109 | 01/25/12–06/18/25 | 14:00⁽3⁾ |
| ***Weekly Announcements*** | | | |
| 52- Initial and Continuing Jobless Claims | 704 | 01/12/12–06/26/25 | 8:30 |
| 53- MBA Mortgage Applications | 690 | 01/18/12–06/25/25 | 7:00 |
| 54- Redbook Same-Store Sales | 676 | 07/03/12–06/24/25 | 8:55 |
| ***Central-Bank Publications and Meetings*** | | | |
| 55- FOMC Minutes † | 107 | 02/15/12–05/28/25 | 14:00 |
| 56- Beige Book † | 107 | 02/29/12–06/04/25 | 14:00 |
| ***Commodity-Market Reports*** | | | |
| 57- EIA Weekly Petroleum Status Report † | 703 | 01/19/12–06/25/25 | 10:30 |
| 58- EIA Natural Gas Storage Report † | 694 | 03/08/12–06/26/25 | 10:30 |
| 59- API Weekly Crude Oil Stocks † | 521 | 07/07/15–06/24/25 | 16:30 |
| 60- API Monthly Statistical Report † | 32 | 03/15/12–01/22/15 | — |
| 61- Baker Hughes Oil Rig Count † | 522 | 07/02/15–06/27/25 | 13:00 |
| 62- OPEC Meeting † | 79 | 06/14/12–02/03/25 | varies |
| 63- USDA WASDE Report † | 73 | 06/11/19–06/12/25 | 12:00 |
| ***Futures Positioning Reports (CFTC)*** | | | |
| 64- CFTC Gold, Oil and S&P 500 Net Positions † | 490 | 01/04/16–06/27/25 | 15:30 |
| ***Government Debt Auctions*** | | | |
| 65- Treasury 2-Year Note Auction † | 161 | 02/21/12–06/24/25 | 13:00 |
| 66- Treasury 3-Year Note Auction † | 157 | 04/10/12–06/10/25 | 13:00 |
| 67- Treasury 5-Year Note Auction † | 159 | 03/28/12–06/25/25 | 13:00 |
| 68- Treasury 7-Year Note Auction † | 154 | 09/27/12–06/26/25 | 13:00 |
| 69- Treasury 10-Year Note Auction † | 159 | 06/13/12–06/11/25 | 13:00 |
| 70- Treasury 20-Year Bond Auction † | 62 | 05/20/20–06/16/25 | 13:00 |
| 71- Treasury 30-Year Bond Auction † | 162 | 02/09/12–06/12/25 | 13:00 |
| 72- Treasury 10-Year TIPS Auction † | 34 | 11/21/19–05/22/25 | 13:00 |
| 73- Treasury 4-Week Bill Auction † | 678 | 05/30/12–06/26/25 | 11:30 |
| 74- Treasury 13- and 26-Week Bill Auctions † | 681 | 05/29/12–06/30/25 | 11:30 |
| 75- Treasury 52-Week Bill Auction † | 173 | 04/03/12–06/10/25 | 11:30 |
| ***Political and Supranational Meetings*** | | | |
| 76- IMF Spring and Annual Meetings † | 81 | 04/20/12–04/27/25 | varies |

**Table 1 (continued): Euro-Area (EUR) News Announcements: euro area, Germany, France**

| Announcement | Obs.¹ | Dates² | Announcement Time (CET)³ |
|---|---|---|---|
| ***Quarterly Announcements*** | | | |
| 77- GDP, euro area (flash, second, final) | 153 | 02/15/12–06/06/25 | 11:00 |
| 78- Employment, euro area | 81 | 03/15/12–06/06/25 | 11:00 |
| 79- Labour Cost Index, euro area | 54 | 03/15/12–06/16/25 | 11:00 |
| 80- GDP, Germany | 108 | 02/15/12–05/23/25 | 8:00⁽4⁾ |
| 81- GDP, France | 122 | 02/15/12–05/28/25 | 7:30⁽5⁾ |
| 82- ILO Unemployment Rate, France | 54 | 03/01/12–05/16/25 | 7:30⁽5⁾ |
| 83- Private Payrolls, France | 108 | 02/14/12–05/28/25 | 7:30⁽5⁾ |
| 84- ECB Bank Lending Survey † | 25 | 07/18/17–04/15/25 | 10:00 |
| 85- Investment Survey in Industry, France † | 37 | 02/09/12–08/26/21 | 8:45 |
| ***Monthly Announcements*** | | | |
| *Real Activity* | | | |
| 86- Unemployment Rate, euro area | 161 | 01/31/12–06/03/25 | 11:00 |
| 87- Industrial Production, euro area | 162 | 01/12/12–06/13/25 | 11:00 |
| 88- Unemployment, Germany | 161 | 01/31/12–05/28/25 | 9:55 |
| 89- Industrial Production, Germany | 161 | 02/07/12–06/06/25 | 8:00 |
| 90- Industrial Output, France | 161 | 02/10/12–06/06/25 | 8:45 |
| *Consumption* | | | |
| 91- Retail Sales, euro area | 161 | 02/03/12–06/06/25 | 11:00 |
| 92- Retail Sales, Germany | 160 | 01/31/12–06/30/25 | 8:00 |
| 93- Household Consumption, France | 158 | 01/31/12–06/27/25 | 8:45 |
| *Investment* | | | |
| 94- Construction Output, euro area | 161 | 01/18/12–06/19/25 | 11:00 |
| 95- Factory Orders, Germany | 161 | 02/06/12–06/05/25 | 8:00 |
| *Government Purchases* | | | |
| 96- Central Government Budget Balance, France | 162 | 01/12/12–06/03/25 | 8:45 |
| *Net Exports* | | | |
| 97- Trade Balance, euro area | 163 | 01/13/12–06/13/25 | 11:00 |
| 98- Current Account, euro area | 162 | 01/19/12–06/18/25 | 10:00 |
| 99- Trade Balance, Germany | 161 | 02/08/12–06/06/25 | 8:00 |
| 100- Current Account, Germany | 161 | 02/08/12–06/12/25 | 8:00 |
| 101- Trade Balance, France | 161 | 02/07/12–06/06/25 | 8:45 |
| 102- Current Account, France | 162 | 01/12/12–06/06/25 | 8:45 |
| *Prices* | | | |
| 103- HICP, euro area (flash and final) | 323 | 01/17/12–06/18/25 | 11:00 |
| 104- Producer Price Index, euro area | 161 | 02/02/12–06/05/25 | 11:00 |
| 105- Consumer Prices, Germany (prelim. and final, CPI and HICP) | 325 | 01/12/12–06/30/25 | 14:00 prelim. / 8:00 final |
| 106- Producer Prices, Germany | 162 | 01/20/12–06/20/25 | 8:00 |
| 107- Import Prices, Germany | 162 | 01/27/12–06/30/25 | 8:00 |
| 108- Wholesale Prices, Germany | 161 | 01/16/12–06/13/25 | 8:00 |
| 109- Consumer Prices, France (prelim. and final) | 272 | 01/12/12–06/27/25 | 8:45 |
| 110- Producer Prices, France | 161 | 01/31/12–06/27/25 | 8:45 |
| 111- German State CPIs (BW, BY, BB, HE, NRW, SN) † | 65 | 01/28/21–06/30/25 | varies (morning) |
| *Forward-Looking* | | | |
| 112- Economic Sentiment Indicator (EC survey) | 162 | 01/30/12–06/27/25 | 11:00 |
| 113- Consumer Confidence, euro area (flash and final) | 324 | 01/23/12–06/27/25 | 16:00 flash / 11:00 final |
| 114- Sentix Investor Confidence | 161 | 02/06/12–06/10/25 | 10:30 |
| 115- HCOB Manufacturing PMI, euro area/Germany/France (flash and final) | 323 | 01/24/12–06/23/25 | flash 9:15 FR, 9:30 DE, 10:00 EA |
| 116- HCOB Services/Composite PMI, euro area/Germany/France (flash and final) | 323 | 01/24/12–06/23/25 | flash 9:15 FR, 9:30 DE, 10:00 EA |
| 117- Ifo Business Climate | 163 | 01/25/12–06/24/25 | 10:00 |
| 118- ZEW Economic Sentiment (Germany and euro area) | 162 | 01/17/12–06/17/25 | 11:00 |
| 119- GfK Consumer Climate | 162 | 01/26/12–06/26/25 | 8:00 |
| 120- Consumer Confidence, France | 161 | 01/26/12–06/25/25 | 8:45 |
| 121- Business Climate in Manufacturing, France | 162 | 01/23/12–06/20/25 | 8:45 |
| *Money and Credit* | | | |
| 122- M3 Money Supply and Private Loans | 162 | 01/27/12–06/30/25 | 10:00 |
| ***Monetary Policy Decisions*** | | | |
| 123- ECB Rate Decision | 125 | 01/12/12–06/05/25 | 14:15⁽6⁾ |
| ***Central-Bank Publications and Meetings*** | | | |
| 124- ECB Monetary Policy Account † | 84 | 02/19/15–05/22/25 | 13:30 |
| 125- ECB Monthly Bulletin / Economic Bulletin † | 121 | 01/19/12–06/20/25 | 10:00 |
| 126- ECB Financial Stability Review † | 24 | 06/12/12–05/21/25 | — |
| 127- ECB Non-Monetary Policy Meeting † | 111 | 01/07/15–03/26/25 | varies |
| 128- Bundesbank Monthly Report † | 126 | 01/19/15–05/22/25 | 12:00 |
| ***Futures Positioning Reports (CFTC)*** | | | |
| 129- CFTC EUR Net Positions † | 490 | 01/04/16–06/27/25 | 15:30 ET |
| ***Government Debt Auctions*** | | | |
| 130- German 2-Year Schatz Auction † | 40 | 03/21/12–07/08/15 | 11:30 |
| 131- German 5-Year Bobl Auction † | 72 | 11/27/19–06/10/25 | 11:30 |
| 132- German 10-Year Bund Auction † | 185 | 04/11/12–06/11/25 | 11:30 |
| 133- German 30-Year Bund Auction † | 121 | 04/25/12–06/18/25 | 11:30 |
| 134- French 10-Year OAT Auction † | 151 | 04/04/12–06/05/25 | 10:50 |
| ***Political and Supranational Meetings*** | | | |
| 135- Eurogroup Meeting † | 180 | 10/30/12–06/20/25 | varies |
| 136- EcoFin Meeting † | 163 | 01/23/12–05/13/25 | varies |
| 137- European Council (EU leaders' summit) † | 102 | 05/23/12–06/27/25 | varies |
| 138- G7 Meeting † | 33 | 06/05/12–05/22/25 | varies |
| 139- G20 Meeting † | 62 | 02/24/12–02/27/25 | varies |
| 140- European Commission Economic Forecasts † | 47 | 05/11/12–05/19/25 | 11:00 |

**Table 1 (continued): U.K. (GBP) News Announcements**

| Announcement | Obs.¹ | Dates² | Announcement Time (UK time)³ |
|---|---|---|---|
| ***Quarterly Announcements*** | | | |
| 141- GDP (first, second, final) incl. Business Investment | 134 | 01/25/12–06/30/25 | 7:00⁽7⁾ |
| 142- Current Account | 54 | 03/28/12–06/30/25 | 7:00⁽7⁾ |
| 143- BoE Credit Conditions Survey | 53 | 03/28/12–04/17/25 | 9:30 |
| 144- BoE/Ipsos Inflation Attitudes Survey | 53 | 03/09/12–06/13/25 | 9:30 |
| ***Monthly Announcements*** | | | |
| *Real Activity* | | | |
| 145- Labour Market (ILO unemployment, claimant count, earnings) | 163 | 01/18/12–06/10/25 | 7:00⁽7⁾ |
| 146- Industrial and Manufacturing Production | 162 | 01/12/12–06/12/25 | 7:00⁽7⁾ |
| 147- Index of Services | 162 | 01/25/12–06/12/25 | 7:00⁽7⁾ |
| 148- NIESR Monthly GDP Tracker | 162 | 01/12/12–06/12/25 | 15:00 |
| 149- GDP Monthly Estimate † | 84 | 07/10/18–06/12/25 | 7:00 |
| *Consumption* | | | |
| 150- Retail Sales | 162 | 01/20/12–06/20/25 | 7:00⁽7⁾ |
| 151- BRC Like-for-Like Retail Sales | 162 | 02/07/12–06/09/25 | 0:01 |
| *Government Purchases* | | | |
| 152- Public Sector Net Borrowing | 162 | 01/24/12–06/20/25 | 7:00⁽7⁾ |
| *Net Exports* | | | |
| 153- Trade Balance | 161 | 02/09/12–06/12/25 | 7:00⁽7⁾ |
| *Prices* | | | |
| 154- Consumer Price Inflation (CPI, core CPI, RPI) | 162 | 01/17/12–06/18/25 | 7:00⁽7⁾ |
| 155- Producer Price Inflation (input and output) | 157 | 01/13/12–02/19/25 | 7:00⁽7⁾ |
| 156- BRC Shop Price Index | 163 | 02/08/12–06/30/25 | 0:01 |
| 157- Nationwide House Price Index | 161 | 02/01/12–06/02/25 | 7:00 |
| 158- Halifax House Price Index | 161 | 02/06/12–06/06/25 | 7:00 |
| 159- Rightmove House Price Index | 160 | 01/16/12–06/15/25 | 0:01 |
| 160- ONS House Price Index | 162 | 01/17/12–06/18/25 | 9:30 |
| *Forward-Looking* | | | |
| 161- RICS Housing Price Balance | 161 | 02/14/12–06/11/25 | 0:01 |
| 162- S&P Global Manufacturing PMI | 230 | 02/01/12–06/23/25 | 9:30 |
| 163- S&P Global Services PMI | 230 | 02/03/12–06/23/25 | 9:30 |
| 164- S&P Global Construction PMI | 161 | 02/02/12–06/05/25 | 9:30 |
| 165- GfK Consumer Confidence | 166 | 01/31/12–06/19/25 | 0:01 |
| 166- CBI Distributive Trades Survey † | 105 | 01/26/12–09/24/20 | 11:00 |
| 167- CBI Industrial Trends Survey † | 105 | 01/25/12–09/22/20 | 11:00 |
| *Money and Credit* | | | |
| 168- BoE Money and Credit (M4, consumer credit, mortgage approvals) | 163 | 01/31/12–06/30/25 | 9:30 |
| 169- BBA Mortgage Approvals † | 97 | 01/25/12–01/27/20 | 9:30 |
| ***Monetary Policy Decisions*** | | | |
| 170- BoE Rate Decision | 129 | 01/12/12–06/19/25 | 12:00 |
| ***Central-Bank Publications and Meetings*** | | | |
| 171- BoE MPC Minutes and Vote † | 136 | 01/25/12–06/19/25 | 12:00⁽8⁾ |
| 172- BoE Monetary Policy Report (Inflation Report) † | 54 | 02/15/12–05/08/25 | 12:00⁽9⁾ |
| 173- BoE Quarterly Bulletin † | 47 | 03/27/12–09/30/24 | — |
| 174- BoE FPC Statement, Record and Financial Stability Report † | 58 | 06/29/12–04/09/25 | varies |
| ***Futures Positioning Reports (CFTC)*** | | | |
| 175- CFTC GBP Net Positions † | 490 | 01/04/16–06/27/25 | 15:30 ET |
| ***Government Debt Auctions*** | | | |
| 176- UK 10-Year Gilt Auction † | 134 | 04/03/12–06/11/25 | varies (morning) |
| 177- UK 30-Year Gilt Auction † | 75 | 03/15/12–03/04/25 | varies (morning) |

**Table 1 (continued): Australian (AUD) News Announcements**

| Announcement | Obs.¹ | Dates² | Announcement Time (Sydney time)³ |
|---|---|---|---|
| ***Quarterly Announcements*** | | | |
| 178- GDP | 54 | 03/07/12–06/04/25 | 11:30 |
| 179- Wage Price Index | 54 | 02/22/12–05/14/25 | 11:30 |
| 180- Consumer Price Index (incl. trimmed mean) | 55 | 01/25/12–04/30/25 | 11:30 |
| 181- Producer Price Index | 54 | 01/23/12–05/02/25 | 11:30 |
| 182- Import and Export Price Indexes | 54 | 01/20/12–05/01/25 | 11:30 |
| 183- Company Gross Operating Profits | 54 | 03/05/12–06/03/25 | 11:30 |
| 184- Private Capital Expenditure | 54 | 03/01/12–05/29/25 | 11:30 |
| 185- Construction Work Done | 54 | 02/29/12–05/28/25 | 11:30 |
| 186- Current Account | 54 | 03/06/12–06/03/25 | 11:30 |
| 187- NAB Quarterly Business Confidence | 54 | 02/08/12–04/17/25 | 11:30 |
| 188- Residential Property Price Index † | 41 | 02/01/12–03/15/22 | 11:30 |
| ***Monthly Announcements*** | | | |
| *Real Activity* | | | |
| 189- Labour Force (employment, unemployment) | 162 | 01/19/12–06/19/25 | 11:30 |
| 190- ANZ Job Advertisements | 157 | 01/16/12–06/02/25 | 11:30 |
| *Consumption* | | | |
| 191- Retail Sales | 178 | 02/06/12–05/30/25 | 11:30 |
| 192- HIA New Home Sales † | 128 | 02/01/12–09/14/22 | — |
| 193- New Motor Vehicle Sales † | 73 | 01/18/12–01/16/18 | 11:30 |
| *Investment* | | | |
| 194- Building Approvals | 161 | 02/02/12–05/30/25 | 11:30 |
| 195- Lending Indicators (housing finance) | 157 | 01/16/12–05/14/25 | 11:30 |
| *Net Exports* | | | |
| 196- Trade Balance | 167 | 02/02/12–06/05/25 | 11:30 |
| *Prices* | | | |
| 197- TD-MI Inflation Gauge | 163 | 01/15/12–06/30/25 | 11:00 |
| 198- MI Consumer Inflation Expectations | 161 | 01/19/12–06/12/25 | 11:00 |
| 199- RBA Commodity Price Index | 161 | 02/01/12–06/02/25 | 16:30 |
| *Forward-Looking* | | | |
| 200- NAB Monthly Business Survey | 163 | 01/31/12–06/10/25 | 11:30 |
| 201- Westpac-MI Consumer Sentiment | 163 | 01/17/12–06/10/25 | 10:30 |
| 202- Westpac-MI Leading Index | 161 | 01/24/12–06/18/25 | 10:30 |
| 203- AiG Performance of Manufacturing Index † | 128 | 01/31/12–11/30/22 | — |
| 204- AiG Performance of Services Index † | 129 | 02/02/12–12/06/22 | — |
| 205- AiG Performance of Construction Index † | 129 | 02/06/12–12/04/22 | — |
| 206- S&P Global Manufacturing PMI (flash and final) † | 158 | 12/13/18–06/30/25 | — |
| 207- S&P Global Services/Composite PMI (flash and final) † | 157 | 12/13/18–06/22/25 | — |
| *Money and Credit* | | | |
| 208- Private Sector Credit | 162 | 01/31/12–06/30/25 | 11:30 |
| 209- RBA Foreign Exchange Transactions † | 61 | 01/19/12–05/18/17 | — |
| ***Monetary Policy Decisions*** | | | |
| 210- RBA Rate Decision (statement) | 144 | 02/07/12–05/20/25 | 14:30 |
| ***Central-Bank Publications and Meetings*** | | | |
| 211- RBA Meeting Minutes † | 143 | 02/21/12–06/03/25 | 11:30 |
| 212- RBA Statement on Monetary Policy † | 56 | 02/09/12–05/20/25 | 11:30⁽10⁾ |
| 213- RBA Bulletin † | 54 | 03/21/12–04/24/25 | 11:30 |
| 214- RBA Financial Stability Review † | 27 | 03/28/12–04/03/25 | 11:30 |
| ***Futures Positioning Reports (CFTC)*** | | | |
| 215- CFTC AUD Net Positions † | 490 | 01/04/16–06/27/25 | 15:30 ET |

Notes: Monthly announcements are grouped into real activity, the components of GDP (consumption, investment, government purchases, net exports), prices, forward-looking indicators, and money and credit. † marks the 76 releases EXT adds to CORE; the other 139 rows are the CORE releases, unchanged.

1. Number of announcement days in the sample (a day counts once even if several series of the release are published that day; flash and final prints count separately).
2. First and last announcement in the sample.
3. Scheduled local time of the publisher: U.S. Eastern Time; Central European Time for the euro area, Germany and France; UK local time; Sydney local time. For the added releases it is the time at the end of the sample; "varies" marks meetings and other releases without a fixed time, "—" a release time we have not verified.

- ⁽1⁾ Advance estimate at 8:30 since Jul-2015 (Advance Economic Indicators).
- ⁽2⁾ From 2021 the calendar also lists the goods balance on full trade-report days.
- ⁽3⁾ Until Mar-2013 the statement came out at 12:30 on press-conference meetings and 14:15 otherwise.
- ⁽4⁾ The 30-day flash estimate (from Jul-2020) is published at 10:00.
- ⁽5⁾ 8:45 until 2016.
- ⁽6⁾ 13:45 until Jun-2022.
- ⁽7⁾ 9:30 until 2018.
- ⁽8⁾ 9:30 until Jul-2015, two weeks after the decision.
- ⁽9⁾ 10:30 until Jul-2015, a week after the decision.
- ⁽10⁾ 14:30 from Feb-2024, published with the decision.

Also: U.K. producer prices end on 02/19/25 because the ONS suspended the PPI publication in 2025.

## Table 2

**Table 2: The Number of Different News Announcements by Sector**

| # | Sector | US | EA | UK | AU | Total |
|---|---|---|---|---|---|---|
| 1 | Agriculture | 1 | 0 | 0 | 0 | 1 |
| 2 | Energy | 6 | 0 | 0 | 0 | 6 |
| 3 | Housing and Real Estate | 9 | 1 | 6 | 5 | 21 |
| 4 | Industrial Sector | 3 | 4 | 1 | 1 | 9 |
| 5 | Intl Trade & BoP | 4 | 6 | 2 | 2 | 14 |
| 6 | Labor Market | 8 | 6 | 1 | 3 | 18 |
| 7 | Monetary Sector | 5 | 8 | 7 | 7 | 27 |
| 8 | National Accounts (GDP) | 1 | 3 | 4 | 2 | 10 |
| 9 | Personal/Household Sector | 1 | 1 | 0 | 0 | 2 |
| 10 | Prices | 3 | 9 | 4 | 6 | 22 |
| 11 | Retail & Wholesale Sector | 5 | 2 | 2 | 2 | 11 |
| 12 | Surveys/Cyclical Indicators | 16 | 11 | 6 | 9 | 42 |
| 13 | Government Finance | 12 | 6 | 3 | 0 | 21 |
| 14 | Political & Supranational | 1 | 6 | 0 | 0 | 7 |
| 15 | Positioning (CFTC) | 1 | 1 | 1 | 1 | 4 |
| | **Total** | **76** | **64** | **37** | **38** | **215** |

Notes: Number of different announcements (releases) per currency, classified into Plihal's Bloomberg sectors (Agriculture to Surveys/Cyclical Indicators), plus Government Finance (budget statements, public-sector borrowing, government bond and bill auctions), Political & Supranational (EU, G7, G20 and IMF meetings, European Commission forecasts) and Positioning (the CFTC's weekly Commitments of Traders net positions). Central-bank decisions, publications (minutes, accounts, reports, bulletins) and meetings are in the Monetary Sector. EA covers the euro area, Germany and France.

## Table 3

**Table 3: The 76 Releases EXT Adds to CORE, by the CORE Rule That Left Them Out**

| CORE rule | Releases | US | EA | UK | AU | Total |
|---|---|---|---|---|---|---|
| R1 | Central-bank publications (minutes, accounts, reports, bulletins) and meetings | 2 | 5 | 4 | 4 | 15 |
| R1 | Government debt auctions (bonds and bills) | 11 | 5 | 2 | 0 | 18 |
| R1 | Futures positioning reports (CFTC) | 1 | 1 | 1 | 1 | 4 |
| R1 | Commodity-market reports | 7 | 0 | 0 | 0 | 7 |
| R1 | Political and supranational meetings, official forecasts | 1 | 6 | 0 | 0 | 7 |
| R2 | Sub-national releases (regional Fed surveys, Chicago PMI, ISM-New York, German state CPIs) | 7 | 1 | 0 | 0 | 8 |
| R3 | Started after 2014 or stopped before 2025 | 2 | 2 | 4 | 9 | 17 |
| | **Total** | **31** | **20** | **11** | **14** | **76** |

Notes: R1 scope, R2 geography, R3 continuity (see CORE_EVENT_SET.md). A release CORE excluded on more than one rule is counted under the first.
