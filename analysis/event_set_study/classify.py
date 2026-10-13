import re, sys, pandas as pd
u = pd.read_csv(sys.argv[1])
u = u[~((u.Currency == 'USD') & (u.pair != 'USDJPY'))]   # USD set is identical in every pair file
u['n'] = u.Name.str.replace(r'^(eur|ger|fra|usd) ', '', regex=True)

# ordered (sector, regex) rules; first match wins
R = [
 ('National Accounts (GDP)', r'Gross Domestic Product Price Index|Personal Consumption Expenditures Prices \(QoQ\)'),
 ('Housing & Real Estate', r'House Price|Home Price|Housing Price'),
 ('Personal/Household Sector', r'Household Spending'),
 ('Labor Market', r'Wage Price Index'),
 ('Surveys/Cyclical Indicators', r'ISM .*Employment|Tankan|Empire State'),
 ('Agriculture', r'WASDE|Grain'),
 ('Energy', r'Crude|EIA |Rig Count|American Petroleum|OPEC'),
 ('Positioning (CFTC)', r'CFTC'),
 ('Govt. Finance & Debt Auctions', r'Auction|Budget|Public Sector Net Borrowing'),
 ('Political & Intl. Bodies', r'IMF Meeting|President (Biden|Trump)|Treasury Sec|summit|EcoFin|Eurogroup|European Council|G20|G7|European Commission|Davos|SECO Economic Forecasts'),
 ('Central Bank Communication', r"speech|testifies|Minutes|Press Conference|Beige Book|Jackson Hole|Accounts|Monthly Report|Economic Bulletin|Non-Monetary Policy|Financial Stability|Quarterly Bulletin|Monetary Policy Report|BoE Monetary Policy Summary__x|FPC|Summary of Opinions|Outlook Report|BoJ Monthly Economic Survey|RBA Bulletin|RBA Monetary Policy Statement"),
 ('Monetary Sector', r'Interest Rate Decision|Monetary Policy Statement|Economic Projections|Refinancing|Deposit Facility|MPC Vote|Asset Purchase|Monetary Policy Summary|Monetary Policy Assessment|Rate Statement|Money Supply|M3 |M4 |Monetary Base|Bank Lending|Private Loans|Private Sector Credit|Consumer Credit|Net Lending to Individuals|Loan Officer|Lending Survey|Credit Conditions|Reserves|Foreign Exchange Transaction'),
 ('Prices', r'Price Index|Consumer Price|CPI|Inflation|Prices \(|Producer Price|PPI|Retail Price|Producer and Import|Service Price|Shop Price|Commodity Index|Wholesale Price'),
 ('Housing & Real Estate', r'Home|Housing|House|Building Permits|Construction Spending|Construction Output|Construction Work|Construction Orders|Mortgage|RICS|Rightmove|Nationwide|Lloyds|Case-Shiller|NAHB|Investment Lending'),
 ('National Accounts (GDP)', r'Gross Domestic|GDP|Personal Consumption Expenditures (Prices )?\(QoQ\)|Core Personal Consumption Expenditures \(QoQ\)|Index of Services|Business Investment|Gross Operating Profits'),
 ('Labor Market', r'Employment|Payrolls|Unemployment|Jobless|Earnings|Weekly Hours|Challenger|JOLTS|Participation|Labor|Labour|Productivity|Unit Labor|Claimant|Job|Wage|U6'),
 ('Personal/Household Sector', r'Personal Income|Personal Spending|Consumer Spending|Household Spending'),
 ('Retail & Wholesale Sector', r'Retail Sales|Retail Trade|Retailer|Redbook|Vehicle Sales|Inventories|Like-For-Like'),
 ('Intl. Trade & BoP', r'Trade Balance|Current Account|Exports|Imports|TIC|Foreign Bond|Foreign Investment'),
 ('Industrial Sector', r'Industrial Production|Industrial Output|Manufacturing Production|Capacity Utilization|Durable|Factory Orders|Capital Goods|Machine|Machinery|Vehicle Production|Tertiary|All Industry|Capital Spending|Capital Expenditure'),
 ('Surveys/Cyclical Indicators', r'PMI|ISM|Fed .*(Index|Survey|Activity)|Chicago|Confidence|Sentiment|Climate|NFIB|Optimism|IFO|ZEW|Sentix|Tankan|BSI|Eco Watchers|Leading|Coincident|AiG|Ai Group|National Australia Bank|KOF|SVME|UBS|CBI|Individual Investment|Business Conditions|Consumer Expectations|National Activity|Industry Index|Performance of'),
]
ORDER = list(dict.fromkeys(x for x, _ in R[5:]))
def sector(n):
    for s, rx in R:
        if re.search(rx, n, re.I):
            return s
    return None
u['sector'] = u.n.map(sector)
miss = u[u.sector.isna()]
if len(miss): print('UNCLASSIFIED:', miss[['Currency','Name']].values.tolist())
u.to_csv(sys.argv[2], index=False)
for s in ORDER:
    print(f'\n== {s}')
    for c in ['USD','EUR','GBP','JPY','AUD','CHF']:
        x = u[(u.sector == s) & (u.Currency == c)].Name.tolist()
        if x: print(f'  {c} ({len(x)}): ' + ' | '.join(x))
