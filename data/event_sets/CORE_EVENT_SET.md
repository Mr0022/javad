# CORE news-announcement set

Release-level calendar of scheduled macroeconomic announcements for the three
pairs (EUR/USD, GBP/USD, AUD/USD), built by `scripts/build_core_events.py`
from `data/event_sets/core_release_map.csv` into `data/<PAIR>_EVENTS_CORE.csv`.

## Selection rules

- **R1 Scope.** Scheduled official statistics and nationally representative surveys of the domestic economy, plus central-bank policy-rate decisions. Excluded: central-bank communication (speeches, minutes, press conferences, reports, testimony), government debt auctions, positioning and supervisory releases (CFTC, stress tests), commodity-market reports (EIA, OPEC, WASDE), political and supranational events, and official forecasts.
- **R2 Geography.** National aggregates; for the euro area, the area aggregate plus its two largest economies (Germany, France). Sub-national releases (regional Fed surveys, Chicago PMI, German state CPIs) are excluded.
- **R3 Continuity.** A series enters only if it is published throughout the sample: first release on or before 31 Dec 2014 and still published in 2025.
- **R4 Release as the unit.** All series published in one statistical release (MoM/YoY, s.a./n.s.a., headline/core, sub-indices, flash and final prints, and one producer's same-day multi-country flash PMIs) form one announcement, dated on every day any of them is published.
- **R5 Frequency.** At least 24 announcements in the sample.

Sample: 12 Jan 2012 – 30 Jun 2025 (the RV sample).

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
| *Consumption* | | | |
| 11- Retail Sales | 163 | 01/12/12–06/17/25 | 8:30 |
| 12- Total Vehicle Sales | 161 | 02/01/12–06/03/25 | varies (afternoon) |
| 13- Personal Income and Outlays (incl. PCE prices) | 161 | 01/30/12–06/27/25 | 8:30 |
| 14- New Home Sales | 161 | 01/26/12–06/25/25 | 10:00 |
| 15- Existing Home Sales | 162 | 01/20/12–06/23/25 | 10:00 |
| *Investment* | | | |
| 16- Business Inventories | 162 | 01/12/12–06/17/25 | 10:00 |
| 17- Wholesale Inventories | 263 | 02/09/12–06/26/25 | 10:00⁽1⁾ |
| 18- Durable Goods Orders | 162 | 01/26/12–06/26/25 | 8:30 |
| 19- Factory Orders | 160 | 02/03/12–06/03/25 | 10:00 |
| 20- Construction Spending | 160 | 02/01/12–06/02/25 | 10:00 |
| *Government Purchases* | | | |
| 21- Monthly Treasury Budget Statement | 162 | 01/12/12–06/11/25 | 14:00 |
| *Net Exports* | | | |
| 22- Trade Balance (goods and services) | 162 | 01/13/12–06/05/25 | 8:30 |
| 23- TIC Capital Flows | 162 | 01/18/12–06/18/25 | 16:00 |
| *Prices* | | | |
| 24- S&P/Case-Shiller Home Prices | 162 | 01/31/12–06/24/25 | 9:00 |
| 25- FHFA House Price Index | 162 | 01/25/12–06/24/25 | 9:00 |
| 26- Consumer Price Index | 163 | 01/19/12–06/11/25 | 8:30 |
| 27- Producer Price Index | 162 | 01/18/12–06/12/25 | 8:30 |
| 28- Import and Export Prices | 162 | 01/13/12–06/17/25 | 8:30 |
| *Forward-Looking* | | | |
| 29- Housing Starts and Building Permits | 161 | 01/19/12–06/18/25 | 8:30 |
| 30- Pending Home Sales | 163 | 01/25/12–06/26/25 | 10:00 |
| 31- NAHB Housing Market Index | 162 | 01/18/12–06/17/25 | 10:00 |
| 32- ISM Manufacturing PMI | 161 | 02/01/12–06/02/25 | 10:00 |
| 33- ISM Services PMI | 161 | 02/03/12–06/04/25 | 10:00 |
| 34- S&P Global Manufacturing PMI (flash and final) | 316 | 04/25/12–06/23/25 | 9:45 flash / 9:45 final |
| 35- S&P Global Services/Composite PMI (flash and final) | 277 | 12/04/13–06/23/25 | 9:45 flash / 9:45 final |
| 36- Consumer Confidence (Conference Board) | 153 | 01/31/12–06/24/25 | 10:00 |
| 37- Michigan Consumer Sentiment (prelim. and final) | 324 | 01/13/12–06/27/25 | 10:00 |
| 38- NFIB Small Business Optimism | 161 | 02/14/12–06/10/25 | 6:00 |
| 39- RCM/TIPP Economic Optimism | 161 | 02/07/12–06/03/25 | 10:00 |
| 40- Chicago Fed National Activity Index | 161 | 01/26/12–06/26/25 | 8:30 |
| *Money and Credit* | | | |
| 41- Consumer Credit | 161 | 02/07/12–06/06/25 | 15:00 |
| ***Monetary Policy Decisions*** | | | |
| 42- FOMC Rate Decision (statement, projections) | 109 | 01/25/12–06/18/25 | 14:00⁽2⁾ |
| ***Weekly Announcements*** | | | |
| 43- Initial and Continuing Jobless Claims | 704 | 01/12/12–06/26/25 | 8:30 |
| 44- MBA Mortgage Applications | 690 | 01/18/12–06/25/25 | 7:00 |
| 45- Redbook Same-Store Sales | 676 | 07/03/12–06/24/25 | 8:55 |

**Table 1 (continued): Euro-Area (EUR) News Announcements: euro area, Germany, France**

| Announcement | Obs.¹ | Dates² | Announcement Time (CET)³ |
|---|---|---|---|
| ***Quarterly Announcements*** | | | |
| 46- GDP, euro area (flash, second, final) | 153 | 02/15/12–06/06/25 | 11:00 |
| 47- Employment, euro area | 81 | 03/15/12–06/06/25 | 11:00 |
| 48- Labour Cost Index, euro area | 54 | 03/15/12–06/16/25 | 11:00 |
| 49- GDP, Germany | 108 | 02/15/12–05/23/25 | 8:00⁽3⁾ |
| 50- GDP, France | 122 | 02/15/12–05/28/25 | 7:30⁽4⁾ |
| 51- ILO Unemployment Rate, France | 54 | 03/01/12–05/16/25 | 7:30⁽4⁾ |
| 52- Private Payrolls, France | 108 | 02/14/12–05/28/25 | 7:30⁽4⁾ |
| ***Monthly Announcements*** | | | |
| *Real Activity* | | | |
| 53- Unemployment Rate, euro area | 161 | 01/31/12–06/03/25 | 11:00 |
| 54- Industrial Production, euro area | 162 | 01/12/12–06/13/25 | 11:00 |
| 55- Unemployment, Germany | 161 | 01/31/12–05/28/25 | 9:55 |
| 56- Industrial Production, Germany | 161 | 02/07/12–06/06/25 | 8:00 |
| 57- Industrial Output, France | 161 | 02/10/12–06/06/25 | 8:45 |
| *Consumption* | | | |
| 58- Retail Sales, euro area | 161 | 02/03/12–06/06/25 | 11:00 |
| 59- Retail Sales, Germany | 160 | 01/31/12–06/30/25 | 8:00 |
| 60- Household Consumption, France | 158 | 01/31/12–06/27/25 | 8:45 |
| *Investment* | | | |
| 61- Construction Output, euro area | 161 | 01/18/12–06/19/25 | 11:00 |
| 62- Factory Orders, Germany | 161 | 02/06/12–06/05/25 | 8:00 |
| *Government Purchases* | | | |
| 63- Central Government Budget Balance, France | 162 | 01/12/12–06/03/25 | 8:45 |
| *Net Exports* | | | |
| 64- Trade Balance, euro area | 163 | 01/13/12–06/13/25 | 11:00 |
| 65- Current Account, euro area | 162 | 01/19/12–06/18/25 | 10:00 |
| 66- Trade Balance, Germany | 161 | 02/08/12–06/06/25 | 8:00 |
| 67- Current Account, Germany | 161 | 02/08/12–06/12/25 | 8:00 |
| 68- Trade Balance, France | 161 | 02/07/12–06/06/25 | 8:45 |
| 69- Current Account, France | 162 | 01/12/12–06/06/25 | 8:45 |
| *Prices* | | | |
| 70- HICP, euro area (flash and final) | 323 | 01/17/12–06/18/25 | 11:00 |
| 71- Producer Price Index, euro area | 161 | 02/02/12–06/05/25 | 11:00 |
| 72- Consumer Prices, Germany (prelim. and final, CPI and HICP) | 325 | 01/12/12–06/30/25 | 14:00 prelim. / 8:00 final |
| 73- Producer Prices, Germany | 162 | 01/20/12–06/20/25 | 8:00 |
| 74- Import Prices, Germany | 162 | 01/27/12–06/30/25 | 8:00 |
| 75- Wholesale Prices, Germany | 161 | 01/16/12–06/13/25 | 8:00 |
| 76- Consumer Prices, France (prelim. and final) | 272 | 01/12/12–06/27/25 | 8:45 |
| 77- Producer Prices, France | 161 | 01/31/12–06/27/25 | 8:45 |
| *Forward-Looking* | | | |
| 78- Economic Sentiment Indicator (EC survey) | 162 | 01/30/12–06/27/25 | 11:00 |
| 79- Consumer Confidence, euro area (flash and final) | 324 | 01/23/12–06/27/25 | 16:00 flash / 11:00 final |
| 80- Sentix Investor Confidence | 161 | 02/06/12–06/10/25 | 10:30 |
| 81- HCOB Manufacturing PMI, euro area/Germany/France (flash and final) | 323 | 01/24/12–06/23/25 | flash 9:15 FR, 9:30 DE, 10:00 EA |
| 82- HCOB Services/Composite PMI, euro area/Germany/France (flash and final) | 323 | 01/24/12–06/23/25 | flash 9:15 FR, 9:30 DE, 10:00 EA |
| 83- Ifo Business Climate | 163 | 01/25/12–06/24/25 | 10:00 |
| 84- ZEW Economic Sentiment (Germany and euro area) | 162 | 01/17/12–06/17/25 | 11:00 |
| 85- GfK Consumer Climate | 162 | 01/26/12–06/26/25 | 8:00 |
| 86- Consumer Confidence, France | 161 | 01/26/12–06/25/25 | 8:45 |
| 87- Business Climate in Manufacturing, France | 162 | 01/23/12–06/20/25 | 8:45 |
| *Money and Credit* | | | |
| 88- M3 Money Supply and Private Loans | 162 | 01/27/12–06/30/25 | 10:00 |
| ***Monetary Policy Decisions*** | | | |
| 89- ECB Rate Decision | 125 | 01/12/12–06/05/25 | 14:15⁽5⁾ |

**Table 1 (continued): U.K. (GBP) News Announcements**

| Announcement | Obs.¹ | Dates² | Announcement Time (UK time)³ |
|---|---|---|---|
| ***Quarterly Announcements*** | | | |
| 90- GDP (first, second, final) incl. Business Investment | 134 | 01/25/12–06/30/25 | 7:00⁽6⁾ |
| 91- Current Account | 54 | 03/28/12–06/30/25 | 7:00⁽6⁾ |
| 92- BoE Credit Conditions Survey | 53 | 03/28/12–04/17/25 | 9:30 |
| 93- BoE/Ipsos Inflation Attitudes Survey | 53 | 03/09/12–06/13/25 | 9:30 |
| ***Monthly Announcements*** | | | |
| *Real Activity* | | | |
| 94- Labour Market (ILO unemployment, claimant count, earnings) | 163 | 01/18/12–06/10/25 | 7:00⁽6⁾ |
| 95- Industrial and Manufacturing Production | 162 | 01/12/12–06/12/25 | 7:00⁽6⁾ |
| 96- Index of Services | 162 | 01/25/12–06/12/25 | 7:00⁽6⁾ |
| 97- NIESR Monthly GDP Tracker | 162 | 01/12/12–06/12/25 | 15:00 |
| *Consumption* | | | |
| 98- Retail Sales | 162 | 01/20/12–06/20/25 | 7:00⁽6⁾ |
| 99- BRC Like-for-Like Retail Sales | 162 | 02/07/12–06/09/25 | 0:01 |
| *Government Purchases* | | | |
| 100- Public Sector Net Borrowing | 162 | 01/24/12–06/20/25 | 7:00⁽6⁾ |
| *Net Exports* | | | |
| 101- Trade Balance | 161 | 02/09/12–06/12/25 | 7:00⁽6⁾ |
| *Prices* | | | |
| 102- Consumer Price Inflation (CPI, core CPI, RPI) | 162 | 01/17/12–06/18/25 | 7:00⁽6⁾ |
| 103- Producer Price Inflation (input and output) | 157 | 01/13/12–02/19/25 | 7:00⁽6⁾ |
| 104- BRC Shop Price Index | 163 | 02/08/12–06/30/25 | 0:01 |
| 105- Nationwide House Price Index | 161 | 02/01/12–06/02/25 | 7:00 |
| 106- Halifax House Price Index | 161 | 02/06/12–06/06/25 | 7:00 |
| 107- Rightmove House Price Index | 160 | 01/16/12–06/15/25 | 0:01 |
| 108- ONS House Price Index | 162 | 01/17/12–06/18/25 | 9:30 |
| *Forward-Looking* | | | |
| 109- RICS Housing Price Balance | 161 | 02/14/12–06/11/25 | 0:01 |
| 110- S&P Global Manufacturing PMI | 230 | 02/01/12–06/23/25 | 9:30 |
| 111- S&P Global Services PMI | 230 | 02/03/12–06/23/25 | 9:30 |
| 112- S&P Global Construction PMI | 161 | 02/02/12–06/05/25 | 9:30 |
| 113- GfK Consumer Confidence | 166 | 01/31/12–06/19/25 | 0:01 |
| *Money and Credit* | | | |
| 114- BoE Money and Credit (M4, consumer credit, mortgage approvals) | 163 | 01/31/12–06/30/25 | 9:30 |
| ***Monetary Policy Decisions*** | | | |
| 115- BoE Rate Decision | 129 | 01/12/12–06/19/25 | 12:00 |

**Table 1 (continued): Australian (AUD) News Announcements**

| Announcement | Obs.¹ | Dates² | Announcement Time (Sydney time)³ |
|---|---|---|---|
| ***Quarterly Announcements*** | | | |
| 116- GDP | 54 | 03/07/12–06/04/25 | 11:30 |
| 117- Wage Price Index | 54 | 02/22/12–05/14/25 | 11:30 |
| 118- Consumer Price Index (incl. trimmed mean) | 55 | 01/25/12–04/30/25 | 11:30 |
| 119- Producer Price Index | 54 | 01/23/12–05/02/25 | 11:30 |
| 120- Import and Export Price Indexes | 54 | 01/20/12–05/01/25 | 11:30 |
| 121- Company Gross Operating Profits | 54 | 03/05/12–06/03/25 | 11:30 |
| 122- Private Capital Expenditure | 54 | 03/01/12–05/29/25 | 11:30 |
| 123- Construction Work Done | 54 | 02/29/12–05/28/25 | 11:30 |
| 124- Current Account | 54 | 03/06/12–06/03/25 | 11:30 |
| 125- NAB Quarterly Business Confidence | 54 | 02/08/12–04/17/25 | 11:30 |
| ***Monthly Announcements*** | | | |
| *Real Activity* | | | |
| 126- Labour Force (employment, unemployment) | 162 | 01/19/12–06/19/25 | 11:30 |
| 127- ANZ Job Advertisements | 157 | 01/16/12–06/02/25 | 11:30 |
| *Consumption* | | | |
| 128- Retail Sales | 178 | 02/06/12–05/30/25 | 11:30 |
| *Investment* | | | |
| 129- Building Approvals | 161 | 02/02/12–05/30/25 | 11:30 |
| 130- Lending Indicators (housing finance) | 157 | 01/16/12–05/14/25 | 11:30 |
| *Net Exports* | | | |
| 131- Trade Balance | 167 | 02/02/12–06/05/25 | 11:30 |
| *Prices* | | | |
| 132- TD-MI Inflation Gauge | 163 | 01/15/12–06/30/25 | 11:00 |
| 133- MI Consumer Inflation Expectations | 161 | 01/19/12–06/12/25 | 11:00 |
| 134- RBA Commodity Price Index | 161 | 02/01/12–06/02/25 | 16:30 |
| *Forward-Looking* | | | |
| 135- NAB Monthly Business Survey | 163 | 01/31/12–06/10/25 | 11:30 |
| 136- Westpac-MI Consumer Sentiment | 163 | 01/17/12–06/10/25 | 10:30 |
| 137- Westpac-MI Leading Index | 161 | 01/24/12–06/18/25 | 10:30 |
| *Money and Credit* | | | |
| 138- Private Sector Credit | 162 | 01/31/12–06/30/25 | 11:30 |
| ***Monetary Policy Decisions*** | | | |
| 139- RBA Rate Decision (statement) | 144 | 02/07/12–05/20/25 | 14:30 |

Notes: Monthly announcements are grouped into real activity, the components of GDP (consumption, investment, government purchases, net exports), prices, forward-looking indicators, and money and credit.

1. Number of announcement days in the sample (a day counts once even if several series of the release are published that day; flash and final prints count separately).
2. First and last announcement in the sample.
3. Scheduled local time of the publisher: U.S. Eastern Time; Central European Time for the euro area, Germany and France; UK local time; Sydney local time.
1. ⁽1⁾ Advance estimate at 8:30 since Jul-2015 (Advance Economic Indicators).
2. ⁽2⁾ Until Mar-2013 the statement came out at 12:30 on press-conference meetings and 14:15 otherwise.
3. ⁽3⁾ The 30-day flash estimate (from Jul-2020) is published at 10:00.
4. ⁽4⁾ 8:45 until 2016.
5. ⁽5⁾ 13:45 until Jun-2022.
6. ⁽6⁾ 9:30 until 2018.

Also: U.K. producer prices end on 02/19/25 because the ONS suspended the PPI publication in 2025. JOLTS and the S&P Global U.S. services PMI enter the calendar in Dec 2013 and satisfy R3.

**Table 2: The Number of Different News Announcements by Sector**

| # | Sector | US | EA | UK | AU | Total |
|---|---|---|---|---|---|---|
| 1 | Housing and Real Estate | 9 | 1 | 5 | 3 | 18 |
| 2 | Industrial Sector | 3 | 4 | 1 | 1 | 9 |
| 3 | Intl Trade & BoP | 3 | 6 | 2 | 2 | 13 |
| 4 | Labor Market | 7 | 6 | 1 | 3 | 17 |
| 5 | Monetary Sector | 3 | 2 | 3 | 2 | 10 |
| 6 | National Accounts (GDP) | 1 | 3 | 3 | 2 | 9 |
| 7 | Personal/Household Sector | 1 | 1 | 0 | 0 | 2 |
| 8 | Prices | 3 | 8 | 4 | 6 | 21 |
| 9 | Retail & Wholesale Sector | 5 | 2 | 2 | 1 | 10 |
| 10 | Surveys/Cyclical Indicators | 9 | 10 | 4 | 4 | 27 |
| 11 | Government Finance | 1 | 1 | 1 | 0 | 3 |
| | **Total** | **45** | **44** | **26** | **24** | **139** |

Notes: Number of different announcements (releases) per currency, classified into Plihal's Bloomberg sectors. Agriculture and Energy are empty under R1 (commodity-market reports are excluded) and are omitted; Government Finance (budget statements, public-sector borrowing) is added. EA covers the euro area, Germany and France.
