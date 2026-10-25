"""Project configuration: countries, tickers, data sources, and political events."""

from dataclasses import dataclass

# --- Universe -----------------------------------------------------------------
# USD-listed iShares country ETFs are used so returns are comparable from the
# perspective of a global investor (currency effects are embedded), and are
# measured against a global equity benchmark (MSCI ACWI via the ACWI ETF).
COUNTRIES = {
    # code: (name, USD country ETF, local equity index, EPU column, GPR column)
    "USA": ("United States", "IVV", "^GSPC", "US", "GPRC_USA"),
    "DEU": ("Germany", "EWG", "^GDAXI", "Germany", "GPRC_DEU"),
    "JPN": ("Japan", "EWJ", "^N225", "Japan", "GPRC_JPN"),
    "GBR": ("United Kingdom", "EWU", "^FTSE", "UK", "GPRC_GBR"),
    "FRA": ("France", "EWQ", "^FCHI", "France", "GPRC_FRA"),
    "CAN": ("Canada", "EWC", "^GSPTSE", "Canada", "GPRC_CAN"),
    "AUS": ("Australia", "EWA", "^AXJO", "Australia", "GPRC_AUS"),
    "IND": ("India", "INDA", "^BSESN", "India", "GPRC_IND"),
    "BRA": ("Brazil", "EWZ", "^BVSP", "Brazil", "GPRC_BRA"),
    "ZAF": ("South Africa", "EZA", None, None, "GPRC_ZAF"),
}
BENCHMARK = "ACWI"  # MSCI All Country World Index ETF

# Exchange rates from Yahoo Finance, quoted as units of local currency per U.S. dollar.
# Used to split U.S.-dollar returns into local equity and currency parts, and to
# express returns for a Canadian-dollar investor.
FX_TICKERS = {"DEU": "EUR=X", "FRA": "EUR=X", "JPN": "JPY=X", "GBR": "GBP=X", "CAN": "CAD=X",
              "AUS": "AUD=X", "IND": "INR=X", "BRA": "BRL=X", "ZAF": "ZAR=X"}  # USA: USD

START = "2008-04-01"  # ACWI ETF inception is March 2008
END = None  # None = most recent available

# --- Public political-risk data sources -----------------------------------------
# Economic Policy Uncertainty (Baker, Bloom & Davis), monthly, by country.
EPU_URL = "https://www.policyuncertainty.com/media/All_Country_Data.xlsx"
# Geopolitical Risk Index (Caldara & Iacoviello), monthly, country-specific.
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"

RAW_DIR = "data/raw"
CACHE_DIR = "data/cache"


@dataclass(frozen=True)
class Event:
    country: str
    date: str  # first trading day on which the news could be priced (YYYY-MM-DD)
    name: str
    kind: str  # election | policy_shock | governance | geopolitical | unrest


# Three events per country, classified by type. Dates are the first trading day
# on which the news could be priced (e.g. a Sunday election maps to Monday).
# Verify dates before publishing results.
EVENTS = [
    Event("USA", "2011-08-08", "S&P downgrade of U.S. debt after debt-ceiling standoff", "policy_shock"),
    Event("USA", "2016-11-09", "Trump wins 2016 presidential election", "election"),
    Event("USA", "2021-01-06", "U.S. Capitol attack", "unrest"),
    Event("GBR", "2016-06-24", "Brexit referendum result", "election"),
    Event("GBR", "2019-12-13", "Conservative majority in general election", "election"),
    Event("GBR", "2022-09-23", "Truss government 'mini-budget'", "policy_shock"),
    Event("DEU", "2017-11-20", "Collapse of 'Jamaica' coalition talks", "governance"),
    Event("DEU", "2021-09-27", "Federal election, end of the Merkel era", "election"),
    Event("DEU", "2022-02-24", "Russia's full-scale invasion of Ukraine", "geopolitical"),
    Event("JPN", "2012-12-17", "LDP landslide returns Abe to power", "election"),
    Event("JPN", "2020-08-28", "Abe announces resignation", "governance"),
    Event("JPN", "2022-07-08", "Assassination of Shinzo Abe", "unrest"),
    Event("FRA", "2017-04-24", "Macron and Le Pen advance in first round", "election"),
    Event("FRA", "2022-04-25", "Macron re-elected", "election"),
    Event("FRA", "2024-06-10", "Macron dissolves National Assembly", "governance"),
    Event("CAN", "2015-10-20", "Trudeau Liberal majority", "election"),
    Event("CAN", "2021-09-21", "Trudeau re-elected with minority", "election"),
    Event("CAN", "2025-02-03", "U.S. announces broad tariffs on Canadian goods", "geopolitical"),
    Event("AUS", "2018-08-24", "Turnbull ousted as prime minister", "governance"),
    Event("AUS", "2019-05-20", "Morrison's surprise election win", "election"),
    Event("AUS", "2022-05-23", "Albanese Labor victory", "election"),
    Event("IND", "2014-05-16", "Modi BJP majority", "election"),
    Event("IND", "2016-11-09", "Demonetisation announced", "policy_shock"),
    Event("IND", "2024-06-04", "BJP loses outright majority", "election"),
    Event("BRA", "2016-04-18", "Lower house votes to impeach Rousseff", "governance"),
    Event("BRA", "2017-05-18", "Temer recording scandal", "governance"),
    Event("BRA", "2022-10-31", "Lula wins presidential run-off", "election"),
    Event("ZAF", "2015-12-10", "Finance minister Nene dismissed", "governance"),
    Event("ZAF", "2017-03-31", "Finance minister Gordhan dismissed", "governance"),
    Event("ZAF", "2021-07-12", "Escalation of civil unrest", "unrest"),
]

# Historical political-stress windows for portfolio stress tests (start, end inclusive).
STRESS_WINDOWS = {
    "Brexit referendum (Jun 2016)": ("2016-06-23", "2016-06-27"),
    "Trump election (Nov 2016)": ("2016-11-08", "2016-11-10"),
    "UK mini-budget (Sep 2022)": ("2022-09-22", "2022-09-28"),
    "Invasion of Ukraine (Feb-Mar 2022)": ("2022-02-23", "2022-03-08"),
    "U.S.-Canada tariff shock (Feb 2025)": ("2025-01-31", "2025-02-04"),
}


# --- Forward-looking scenarios ------------------------------------------------------
# Each scenario takes its political-risk shocks from historical analogue months:
# a country's shock is its largest political-risk surprise in those months. The
# "window" is the daily period used to show what markets actually did then.
@dataclass(frozen=True)
class Scenario:
    name: str
    story: str
    months: dict  # country code (or "*" for all) -> list of "YYYY-MM" analogue months
    windows: dict  # country code (or "*") -> (start, end) daily window of the analogue


SCENARIOS = [
    Scenario(
        "Tariff escalation",
        "U.S. tariffs on Canada and other trading partners escalate, as in February to April 2025.",
        {"*": ["2025-02", "2025-03", "2025-04"]},
        {"*": ("2025-01-31", "2025-04-30")},
    ),
    Scenario(
        "European security crisis",
        "A major military escalation in Europe, as after Russia's full-scale invasion of Ukraine.",
        {"*": ["2022-02", "2022-03"]},
        {"*": ("2022-02-23", "2022-03-31")},
    ),
    Scenario(
        "Emerging-market governance shock",
        "Sudden leadership or finance-ministry upheaval in large emerging markets, as in Brazil (May 2017) "
        "and South Africa (December 2015).",
        {"BRA": ["2017-05"], "ZAF": ["2015-12"]},
        {"BRA": ("2017-05-17", "2017-06-16"), "ZAF": ("2015-12-09", "2016-01-08")},
    ),
    Scenario(
        "U.S. fiscal standoff",
        "A U.S. debt-ceiling standoff that ends in a credit-rating downgrade, as in July to August 2011 "
        "(a period that also saw the euro-area debt crisis intensify).",
        {"*": ["2011-07", "2011-08"]},
        {"*": ("2011-07-22", "2011-08-22")},
    ),
]
