"""EXT release set: every CORE release, plus the releases CORE's scope rules left out.

CORE (../core/families.py) keeps 139 releases. Its scope (R1), geography (R2) and
continuity (R3) rules also removed minutes, regional surveys, bond auctions,
commodity reports, political meetings and every release that started after
2014 or stopped before 2025. EXT puts those back and drops only

  * speech-like communication: speeches, testimony and parliamentary hearings,
    press conferences, and the Jackson Hole symposium. The decision, statement or
    report they accompany stays in, so no announcement day is lost;
  * releases with no macroeconomic news: CFTC positioning (published after the
    Friday session, on Tuesday's positions), Treasury bill auctions (weekly cash
    management) and ECB Governing Council meetings without a policy decision;
  * rare releases: fewer than 24 announcements in the sample (R5, as in CORE),
    or first published after 2021, so absent from the deep models' training
    years (2012-2021) -- the ABS monthly CPI indicator and the Ai Group Industry
    Index.

CORE releases enter EXT unchanged, so every CORE indicator column is also an
EXT column with identical values. Series that belong to a CORE release but enter
the calendar after 2014 (ISM sub-indices, U6, ...) are published on that
release's days and stay covered by it (COVERED below).

make_ext.py turns this into data/event_sets/ext_release_map.csv, the calendars
data/<PAIR>_EVENTS_EXT.csv and the tables in data/event_sets/EXT_EVENT_SET.md.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from families import F as CORE  # noqa: E402

# group codes for Table 1 sections; Q/M/P/W are CORE's frequency codes
GROUPS = [("Q", "Quarterly Announcements"), ("M", "Monthly Announcements"),
          ("P", "Monetary Policy Decisions"), ("W", "Weekly Announcements"),
          ("C", "Central-Bank Publications"), ("X", "Commodity-Market Reports"),
          ("A", "Government Bond Auctions"), ("S", "Political and Supranational Meetings")]

# The CORE rule that kept each added release out:
#   R1 scope (central-bank communication, auctions, commodity reports, political
#      events and official forecasts), R2 geography (sub-national), R3 continuity
NEW = []


def f(cur, ctry, fid, name, group, frequency, cat, sec, rule, time, members, note=""):
    NEW.append(dict(cur=cur, country=ctry, fid=fid, name=name, group=group,
                    frequency=frequency, cat=cat, sector=sec, core_rule=rule,
                    time=time, time_note=note, members=members))


# time: scheduled local time at the end of the sample; "varies" for meetings,
# "—" where the release time is not verified

# ---------------- USD (ET) ----------------
U = lambda *a, **k: f("USD", "US", *a, **k)
U("U46", "FOMC Minutes", "C", "policy meeting", "Monetary", "Monetary Sector", "R1", "14:00", ["FOMC Minutes"])
U("U47", "Beige Book", "C", "policy meeting", "Monetary", "Monetary Sector", "R1", "14:00", ["Fed's Beige Book"])
U("U48", "Chicago PMI", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R2", "9:45", ["Chicago PMI"])
U("U49", "Dallas Fed Manufacturing Survey", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R2", "10:30",
  ["Dallas Fed Manufacturing Business Index"])
U("U50", "Kansas City Fed Manufacturing Survey", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R2", "11:00",
  ["Kansas Fed Manufacturing Activity"])
U("U51", "NY Empire State Manufacturing Survey", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R2", "8:30",
  ["NY Empire State Manufacturing Index"])
U("U52", "Philadelphia Fed Manufacturing Survey", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R2", "8:30",
  ["Philadelphia Fed Manufacturing Survey"])
U("U53", "Richmond Fed Manufacturing Survey", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R2", "10:00",
  ["Richmond Fed Manufacturing Index"])
U("U54", "ISM-New York Business Conditions", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R2", "—",
  ["ISM-NY Business Conditions Index"])
U("U55", "Labor Market Conditions Index", "M", "monthly", "Real Activity", "Labor Market", "R3", "10:00",
  ["Labor Market Conditions Index"])
U("U56", "Advance Goods Trade Balance", "M", "monthly", "Net Exports", "Intl Trade & BoP", "R3", "8:30", ["Goods Trade Balance"],
  note="From 2021 the calendar also lists the goods balance on full trade-report days.")
for fid, tenor, member in [("U57", "2-Year Note", "2-Year Note Auction"), ("U58", "3-Year Note", "3-Year Note Auction"),
                           ("U59", "5-Year Note", "5-Year Note Auction"), ("U60", "7-Year Note", "7-Year Note Auction"),
                           ("U61", "10-Year Note", "10-Year Note Auction"), ("U62", "20-Year Bond", "20-Year Bond Auction"),
                           ("U63", "30-Year Bond", "30-Year Bond Auction")]:
    U(fid, f"Treasury {tenor} Auction", "A", "monthly", "Government", "Government Finance", "R1", "13:00", [member])
U("U64", "Treasury 10-Year TIPS Auction", "A", "bimonthly", "Government", "Government Finance", "R1", "13:00",
  ["10-year TIPS Auction"])
U("U65", "EIA Weekly Petroleum Status Report", "X", "weekly", "Commodities", "Energy", "R1", "10:30",
  ["EIA Crude Oil Stocks Change", "EIA Distillate Stocks Change", "EIA Gasoline Stocks Change", "EIA Heating Oil Stocks Change"])
U("U66", "EIA Natural Gas Storage Report", "X", "weekly", "Commodities", "Energy", "R1", "10:30", ["EIA Natural Gas Storage Change"])
U("U67", "API Weekly Crude Oil Stocks", "X", "weekly", "Commodities", "Energy", "R1", "16:30", ["API Weekly Crude Oil Stock"])
U("U68", "API Monthly Statistical Report", "X", "monthly", "Commodities", "Energy", "R1", "—",
  ["American Petroleum Institute Monthly Report"])
U("U69", "Baker Hughes Oil Rig Count", "X", "weekly", "Commodities", "Energy", "R1", "13:00", ["Baker Hughes US Oil Rig Count"])
U("U70", "OPEC Meeting", "X", "irregular", "Commodities", "Energy", "R1", "varies", ["OPEC Meeting"])
U("U71", "USDA WASDE Report", "X", "monthly", "Commodities", "Agriculture", "R1", "12:00", ["USDA WASDE Report"])
U("U72", "IMF Spring and Annual Meetings", "S", "semiannual", "Political", "Political & Supranational", "R1", "varies",
  ["IMF Meeting"])

# ---------------- EUR (CET): euro area, Germany, France ----------------
EA = lambda *a, **k: f("EUR", "EA", *a, **k)
DE = lambda *a, **k: f("EUR", "DE", *a, **k)
FR = lambda *a, **k: f("EUR", "FR", *a, **k)
EA("E19", "ECB Monetary Policy Account", "C", "policy meeting", "Monetary", "Monetary Sector", "R1", "13:30",
   ["eur ECB Monetary Policy Meeting Accounts"])
EA("E20", "ECB Monthly Bulletin / Economic Bulletin", "C", "policy meeting", "Monetary", "Monetary Sector", "R1", "10:00",
   ["eur ECB Monthly Report", "eur Economic Bulletin"])
EA("E21", "ECB Bank Lending Survey", "Q", "quarterly", "Monetary", "Monetary Sector", "R3", "10:00", ["eur ECB Bank Lending Survey"])
EA("E22", "ECB Financial Stability Review", "C", "semiannual", "Monetary", "Monetary Sector", "R1", "—",
   ["eur EU Financial Stability Review"])
EA("E23", "Eurogroup Meeting", "S", "monthly", "Political", "Political & Supranational", "R1", "varies", ["eur Eurogroup Meeting"])
EA("E24", "EcoFin Meeting", "S", "monthly", "Political", "Political & Supranational", "R1", "varies", ["eur EcoFin Meeting"])
EA("E25", "European Council (EU leaders' summit)", "S", "irregular", "Political", "Political & Supranational", "R1", "varies",
   ["eur European Council Meeting", "eur EU leaders summit"])
EA("E26", "G7 Meeting", "S", "irregular", "Political", "Political & Supranational", "R1", "varies", ["eur G7 Meeting"])
EA("E27", "G20 Meeting", "S", "irregular", "Political", "Political & Supranational", "R1", "varies", ["eur G20 Meeting"])
EA("E28", "European Commission Economic Forecasts", "S", "irregular", "Political", "Political & Supranational", "R1", "11:00",
   ["eur European Commission releases Economic Growth Forecasts"])
DE("D15", "German State CPIs (BW, BY, BB, HE, NRW, SN)", "M", "monthly", "Prices", "Prices", "R2", "varies (morning)",
   [f"ger {s} CPI ({c})" for s in ["Baden-Wuerttemberg", "Bavaria", "Brandenburg", "Hesse", "North Rhine-Westphalia", "Saxony"]
    for c in ["MoM", "YoY"]])
DE("D16", "Bundesbank Monthly Report", "C", "monthly", "Monetary", "Monetary Sector", "R1", "12:00", ["ger German Buba Monthly Report"])
for fid, tenor, member in [("D17", "2-Year Schatz", "ger 2-year Notes Auction"), ("D18", "5-Year Bobl", "ger 5-y Note Auction"),
                           ("D19", "10-Year Bund", "ger 10-y Bond Auction"), ("D20", "30-Year Bund", "ger 30-y Bond Auction")]:
    DE(fid, f"German {tenor} Auction", "A", "monthly" if fid != "D20" else "irregular", "Government", "Government Finance",
       "R1", "11:30", [member])
FR("F15", "French 10-Year OAT Auction", "A", "monthly", "Government", "Government Finance", "R1", "10:50", ["fra 10-y Bond Auction"])
FR("F16", "Investment Survey in Industry, France", "Q", "quarterly", "Investment", "Surveys/Cyclical Indicators", "R3", "8:45",
   ["fra Individual Investment (Current Year)"])

# ---------------- GBP (UK time) ----------------
G = lambda *a, **k: f("GBP", "UK", *a, **k)
G("G27", "BoE MPC Minutes and Vote", "C", "policy meeting", "Monetary", "Monetary Sector", "R1", "12:00",
  ["BoE Minutes", "BoE MPC Vote Rate Cut", "BoE MPC Vote Rate Hike", "BoE MPC Vote Rate Unchanged"],
  note="9:30 until Jul-2015, two weeks after the decision.")
G("G28", "BoE Monetary Policy Report (Inflation Report)", "C", "quarterly", "Monetary", "Monetary Sector", "R1", "12:00",
  ["BoE Monetary Policy Report"], note="10:30 until Jul-2015, a week after the decision.")
G("G29", "BoE Quarterly Bulletin", "C", "quarterly", "Monetary", "Monetary Sector", "R1", "—", ["BoE Quarterly Bulletin"])
G("G30", "BoE FPC Statement, Record and Financial Stability Report", "C", "quarterly", "Monetary", "Monetary Sector", "R1",
  "varies", ["FPC Statement", "FPC Meeting Minutes", "Financial Stability Report"])
G("G31", "GDP Monthly Estimate", "M", "monthly", "Real Activity", "National Accounts (GDP)", "R3", "7:00",
  ["Gross Domestic Product (MoM)"])
G("G32", "CBI Distributive Trades Survey", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R3", "11:00",
  ["CBI Distributive Trades Survey – Realized (MoM)"])
G("G33", "CBI Industrial Trends Survey", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R3", "11:00",
  ["CBI Industrial Trends Survey – Orders (MoM)"])
G("G34", "BBA Mortgage Approvals", "M", "monthly", "Monetary", "Housing and Real Estate", "R3", "9:30", ["BBA Mortgage Approvals"])
G("G35", "UK 10-Year Gilt Auction", "A", "irregular", "Government", "Government Finance", "R1", "varies (morning)",
  ["10-y Bond Auction"])
G("G36", "UK 30-Year Gilt Auction", "A", "irregular", "Government", "Government Finance", "R1", "varies (morning)",
  ["30-y Bond Auction"])

# ---------------- AUD (Sydney time) ----------------
A = lambda *a, **k: f("AUD", "AU", *a, **k)
A("A25", "RBA Meeting Minutes", "C", "policy meeting", "Monetary", "Monetary Sector", "R1", "11:30", ["RBA Meeting Minutes"])
A("A26", "RBA Statement on Monetary Policy", "C", "quarterly", "Monetary", "Monetary Sector", "R1", "11:30",
  ["RBA Monetary Policy Statement"], note="14:30 from Feb-2024, published with the decision.")
A("A27", "RBA Bulletin", "C", "quarterly", "Monetary", "Monetary Sector", "R1", "11:30", ["RBA Bulletin"])
A("A28", "RBA Financial Stability Review", "C", "semiannual", "Monetary", "Monetary Sector", "R1", "11:30",
  ["Financial Stability Review"])
A("A29", "RBA Foreign Exchange Transactions", "M", "monthly", "Monetary", "Monetary Sector", "R3", "—",
  ["RBA Foreign Exchange Transaction"])
A("A30", "AiG Performance of Manufacturing Index", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R3", "—",
  ["AiG Performance of Mfg Index"])
A("A31", "AiG Performance of Services Index", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R3", "—",
  ["AiG Performance of Services Index"])
A("A32", "AiG Performance of Construction Index", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators", "R3", "—",
  ["AiG Performance of Construction Index"])
A("A33", "S&P Global Manufacturing PMI (flash and final)", "M", "monthly", "Forward-Looking", "Surveys/Cyclical Indicators",
  "R3", "—", ["S&P Global Manufacturing PMI"])
A("A34", "S&P Global Services/Composite PMI (flash and final)", "M", "monthly", "Forward-Looking",
  "Surveys/Cyclical Indicators", "R3", "—", ["S&P Global Services PMI", "S&P Global Composite PMI"])
A("A35", "HIA New Home Sales", "M", "monthly", "Consumption", "Housing and Real Estate", "R3", "—", ["HIA New Home Sales (MoM)"])
A("A36", "Residential Property Price Index", "Q", "quarterly", "Prices", "Housing and Real Estate", "R3", "11:30",
  ["House Price Index (QoQ)", "House Price Index (YoY)"])
A("A37", "New Motor Vehicle Sales", "M", "monthly", "Consumption", "Retail & Wholesale Sector", "R3", "11:30",
  ["New Motor Vehicle Sales (MoM)", "New Motor Vehicle Sales (YoY)"])


# ---------------- what stays out, and why ----------------
SPEECH_LIKE = re.compile(r"speech|\bspeaks?\b|testif|\bhearings\b|press conference|press briefing|"
                         r"news conference|jackson hole|state of the union", re.I)

UNNECESSARY = [(re.compile(r"\bCFTC\b"), "CFTC positioning report"),
               (re.compile(r"Bill Auction"), "Treasury bill auction"),
               (re.compile(r"Non-Monetary Policy ECB Meeting"), "ECB meeting without a policy decision")]

# releases first published after 2021 (X3): never seen in the deep models' training years
LATE = {("AUD", "Consumer Price Index (YoY)"): "ABS Monthly CPI Indicator (from Sep-2022)",
        ("AUD", "Consumer Price Index (MoM)"): "ABS Monthly CPI Indicator (from Sep-2022)",
        ("AUD", "Trimmed Mean CPI (MoM)"): "ABS Monthly CPI Indicator (from Sep-2022)",
        ("AUD", "Trimmed Mean CPI (YoY)"): "ABS Monthly CPI Indicator (from Sep-2022)",
        ("AUD", "Ai Group Construction PMI"): "Ai Group Industry Index (from Feb-2023)",
        ("AUD", "Ai Group Manufacturing PMI"): "Ai Group Industry Index (from Feb-2023)",
        ("AUD", "AiG Industry Index"): "Ai Group Industry Index (from Feb-2023)"}

# series of a CORE release that CORE's R3 left out of its member list; they are
# published on that release's days, so the CORE release already marks them
COVERED = {
    "USD": {"Building Permits Change": "U19", "Housing Starts Change": "U19",
            "Durable Goods Orders ex Defense": "U15", "Nondefense Capital Goods Orders ex Aircraft": "U15",
            "ISM Manufacturing Employment Index": "U32", "ISM Manufacturing New Orders Index": "U32",
            "ISM Services Employment Index": "U33", "ISM Services New Orders Index": "U33",
            "ISM Services Prices Paid": "U33", "Initial Jobless Claims 4-week average": "U43",
            "Michigan Consumer Expectations Index": "U37", "UoM 1-year Consumer Inflation Expectations": "U37",
            "UoM 5-year Consumer Inflation Expectation": "U37", "Redbook Index (MoM)": "U45",
            "Retail Sales (YoY)": "U10", "Retail Sales Control Group": "U10", "U6 Underemployment Rate": "U06",
            "Interest Rate Projections - Current": "U42", "Interest Rate Projections - 1st year": "U42",
            "Interest Rate Projections - 2nd year": "U42", "Interest Rate Projections - 3rd year": "U42",
            "Interest Rate Projections - Longer": "U42", "Fed Pace of MBS Purchase Program": "U42",
            "Fed Pace of Treasury Purchase Program": "U42"},
    "EUR": {"eur Core Harmonized Index of Consumer Prices (MoM)": "E10", "eur ECB Monetary Policy Statement": "E18",
            "fra Gross Domestic Product (YoY)": "F01", "ger HCOB Composite PMI": "E17"},
    "GBP": {"BoE Asset Purchase Facility": "G26", "BoE Monetary Policy Summary": "G26",
            "Employment Change (3M)": "G05", "S&P Global Composite PMI": "G23"},
    "AUD": {"Westpac Consumer Confidence Index": "A22"},
}


def exclusion_reason(cur, name):
    """Why a raw series that is in no EXT release stays out; None if no rule names it.

    Order matters: a rare speech is reported as speech-like, a rare CORE member as
    covered. Whatever no rule names must be rare -- make_ext.py checks that.
    """
    if SPEECH_LIKE.search(name):
        return "speech-like", "speech, testimony, hearing or press conference"
    for rx, what in UNNECESSARY:
        if rx.search(name):
            return "no macro news", what
    if name in COVERED.get(cur, {}):
        return "covered by a CORE release", COVERED[cur][name]
    if (cur, name) in LATE:
        return "first published after 2021", LATE[(cur, name)]
    return None
