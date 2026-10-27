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


# --- Election surprises, leadership exits, and the event / exogenous / thematic taxonomy ------
# Classes of election outcome against the final pre-election polls and seat projections:
#   "Upset"       the leader in the final polls did not win (most votes in a presidential race or
#                 referendum, most seats in a parliamentary election, first place in a first round).
#   "Big miss"    the poll leader won, but the result crossed a line the polls pointed the other way:
#                 a majority won or lost against expectations, or a far wider or narrower margin.
#   "As expected" the poll leader won, roughly as polled.
#   "Toss-up"     the final polls showed no clear leader.
# Classification uses the final polls and projections summarised in each election's opinion-polling
# article and contemporary reporting; the surprises were spot-checked against news reports (see `source`).
@dataclass(frozen=True)
class Election:
    country: str
    date: str  # first U.S. trading day on which the result could be priced
    name: str
    polls: str  # what the final polls said
    surprise: str  # Upset | Big miss | As expected | Toss-up
    source: str = ""


ELECTIONS = [
    # United States (Tuesday vote, result overnight -> Wednesday)
    Election("USA", "2012-11-07", "Obama re-elected", "Obama narrowly ahead nationally", "Toss-up"),
    Election("USA", "2016-11-09", "Trump defeats Clinton", "Clinton led national and key-state polls", "Upset"),
    Election("USA", "2020-11-04", "Biden defeats Trump", "Biden led by about 7 points; won by about 4.5", "As expected"),
    Election("USA", "2024-11-06", "Trump defeats Harris", "National polls essentially tied", "Toss-up"),
    # United Kingdom (Thursday vote -> Friday)
    Election("GBR", "2010-05-07", "Hung parliament", "Conservatives ahead, short of a majority", "As expected"),
    Election("GBR", "2015-05-08", "Conservative majority", "Conservatives and Labour level; hung parliament expected",
             "Big miss", "https://www.cityam.com/general-election-2015-unrepresentative-samples-are-to-blame-for-polling-errors/"),
    Election("GBR", "2016-06-24", "Brexit referendum: Leave wins", "Remain narrowly ahead in final polls; betting markets favoured Remain",
             "Upset"),
    Election("GBR", "2017-06-09", "Conservatives lose majority", "Conservatives well ahead; larger majority expected",
             "Big miss", "https://professionaladviser.com/news/3011583/shell-election-hung-parliament-surprise-result"),
    Election("GBR", "2019-12-13", "Conservative majority", "Conservatives well ahead; majority expected", "As expected"),
    Election("GBR", "2024-07-05", "Labour landslide", "Labour far ahead; landslide expected", "As expected"),
    # Germany (Sunday vote -> Monday)
    Election("DEU", "2009-09-28", "CDU/CSU-FDP coalition", "CDU/CSU clear leader", "As expected"),
    Election("DEU", "2013-09-23", "Merkel third term", "CDU/CSU clear leader", "As expected"),
    Election("DEU", "2017-09-25", "Merkel fourth term; AfD enters Bundestag", "CDU/CSU clear leader; AfD third", "As expected"),
    Election("DEU", "2021-09-27", "SPD narrowly first", "SPD narrowly ahead", "As expected"),
    Election("DEU", "2025-02-24", "CDU/CSU first; Merz chancellor", "CDU/CSU clear leader", "As expected"),
    # France (Sunday vote -> Monday)
    Election("FRA", "2012-05-07", "Hollande elected", "Hollande ahead", "As expected"),
    Election("FRA", "2017-04-24", "Macron and Le Pen advance (first round)", "Macron and Le Pen top two", "As expected"),
    Election("FRA", "2017-05-08", "Macron elected", "Macron far ahead", "As expected"),
    Election("FRA", "2022-04-25", "Macron re-elected", "Macron ahead", "As expected"),
    Election("FRA", "2024-07-01", "National Rally first (legislative first round)", "National Rally first", "As expected"),
    Election("FRA", "2024-07-08", "Left alliance first, National Rally third (second round)",
             "National Rally projected to win the most seats", "Upset",
             "https://www.publicsenat.fr/actualites/politique/resultats-des-elections-legislatives-face-a-la-surprise-du-second-tour-les-instituts-de-sondages-se-sont-ils-trompes"),
    # Canada (Monday vote, result late evening -> Tuesday)
    Election("CAN", "2015-10-20", "Trudeau Liberal majority", "Liberals ahead; minority projected", "Big miss",
             "https://findanexpert.unimelb.edu.au/news/4758-liberals-storm-to-surprise-majority-in-canadian-election"),
    Election("CAN", "2019-10-22", "Liberal minority", "Liberals and Conservatives level", "Toss-up"),
    Election("CAN", "2021-09-21", "Liberal minority", "Liberals and Conservatives level", "Toss-up"),
    Election("CAN", "2025-04-29", "Carney Liberals win", "Liberals ahead", "As expected"),
    # Australia (Saturday vote -> Monday)
    Election("AUS", "2010-08-23", "Hung parliament", "Labor and Coalition level", "Toss-up"),
    Election("AUS", "2013-09-09", "Coalition wins", "Coalition clearly ahead", "As expected"),
    Election("AUS", "2016-07-04", "Coalition narrowly re-elected", "Coalition and Labor level", "Toss-up"),
    Election("AUS", "2019-05-20", "Morrison's surprise win", "Labor ahead in every final poll", "Upset",
             "https://www.canberratimes.com.au/story/6131876/massive-polling-failure-experts/"),
    Election("AUS", "2022-05-23", "Albanese Labor victory", "Labor ahead", "As expected"),
    Election("AUS", "2025-05-05", "Labor landslide", "Labor ahead", "As expected"),
    # Japan (Sunday vote -> Monday)
    Election("JPN", "2009-08-31", "DPJ landslide ends LDP rule", "DPJ landslide expected", "As expected"),
    Election("JPN", "2012-12-17", "LDP landslide returns Abe to power", "LDP landslide expected", "As expected"),
    Election("JPN", "2014-12-15", "Abe coalition keeps supermajority", "LDP win expected", "As expected"),
    Election("JPN", "2017-10-23", "Abe coalition wins", "LDP win expected", "As expected"),
    Election("JPN", "2021-11-01", "LDP keeps single-party majority", "LDP expected to lose seats, majority at risk",
             "Big miss", "https://www.cnbc.com/2021/11/01/japan-pm-fumio-kishida-defies-expectations-ruling-ldp-keeps-majority.html"),
    Election("JPN", "2024-10-28", "Ruling coalition loses majority", "Coalition projected to lose its majority", "As expected",
             "https://www.thejakartapost.com/world/2024/10/27/japan-votes-in-election-expected-to-punish-pm-ishibas-coalition"),
    Election("JPN", "2026-02-09", "Takaichi LDP wins two-thirds supermajority", "LDP majority expected; few projected a supermajority",
             "Big miss", "https://en.wikipedia.org/wiki/2026_Japanese_general_election"),
    # India (counting day; INDA trades the same U.S. day)
    Election("IND", "2014-05-16", "Modi BJP wins outright majority", "NDA ahead; BJP alone short of a majority",
             "Big miss", "https://www.isas.nus.edu.sg/papers/249-modi-triumphs-in-indias-national-elections/"),
    Election("IND", "2019-05-23", "Modi re-elected with larger majority", "NDA win expected", "As expected"),
    Election("IND", "2024-06-04", "BJP loses outright majority", "Exit polls projected an NDA landslide",
             "Big miss", "https://www.aljazeera.com/news/2024/6/1/indias-exit-polls-predict-a-big-majority-for-modis-bjp-led-alliance"),
    # Brazil (Sunday vote -> Monday)
    Election("BRA", "2010-11-01", "Rousseff elected", "Rousseff ahead", "As expected"),
    Election("BRA", "2014-10-27", "Rousseff narrowly re-elected", "Rousseff narrowly ahead", "As expected"),
    Election("BRA", "2018-10-29", "Bolsonaro elected", "Bolsonaro ahead", "As expected"),
    Election("BRA", "2022-10-03", "Bolsonaro outperforms polls (first round)", "Lula far ahead, possible first-round win",
             "Big miss", "https://www.sowetan.co.za/news/world/2022-10-03-brazil-markets-soar-as-bolsonaros-strong-showing-sparks-runoff-vote"),
    Election("BRA", "2022-10-31", "Lula wins presidential run-off", "Lula narrowly ahead", "As expected"),
    Election("BRA", "2026-10-05", "Flavio Bolsonaro tops first round", "Lula first in final polls", "Upset",
             "https://www.aljazeera.com/news/2026/10/5/brazils-presidential-race-three-key-takeaways-from-the-first-round"),
    # South Africa (results over several days; first trading day the outcome was clear)
    Election("ZAF", "2014-05-08", "ANC re-elected", "ANC win expected", "As expected"),
    Election("ZAF", "2019-05-09", "ANC re-elected, reduced majority", "ANC win expected", "As expected"),
    Election("ZAF", "2024-06-03", "ANC loses its majority", "ANC projected to fall below 50%", "As expected"),
]


# Unscheduled departures of a head of government, and scheduled votes that removed one.
@dataclass(frozen=True)
class LeaderExit:
    country: str
    date: str  # first U.S. trading day on which the news could be priced
    name: str
    scheduled: bool  # True if the exit came from a vote on a known date (confidence vote, impeachment)


LEADER_EXITS = [
    LeaderExit("GBR", "2010-05-11", "Brown resigns after coalition deal", False),
    LeaderExit("GBR", "2019-05-24", "May announces resignation", False),
    LeaderExit("GBR", "2022-07-07", "Johnson resigns", False),
    LeaderExit("GBR", "2022-10-20", "Truss resigns", False),
    LeaderExit("GBR", "2026-06-22", "Starmer announces resignation", False),
    LeaderExit("JPN", "2010-06-02", "Hatoyama resigns", False),
    LeaderExit("JPN", "2020-08-28", "Abe announces resignation", False),
    LeaderExit("JPN", "2021-09-03", "Suga says he will not seek re-election", False),
    LeaderExit("JPN", "2024-08-14", "Kishida says he will not seek re-election", False),
    LeaderExit("JPN", "2025-09-08", "Ishiba announces resignation", False),
    LeaderExit("AUS", "2010-06-24", "Rudd ousted by Gillard", False),
    LeaderExit("AUS", "2013-06-26", "Gillard ousted by Rudd", False),
    LeaderExit("AUS", "2015-09-14", "Abbott ousted by Turnbull", False),
    LeaderExit("AUS", "2018-08-24", "Turnbull ousted as prime minister", False),
    LeaderExit("CAN", "2025-01-06", "Trudeau announces resignation", False),
    LeaderExit("DEU", "2018-10-29", "Merkel says she will not seek re-election", False),
    LeaderExit("FRA", "2024-12-04", "Barnier government falls in confidence vote", True),
    LeaderExit("FRA", "2025-09-08", "Bayrou government loses confidence vote", True),
    LeaderExit("FRA", "2025-10-06", "Lecornu resigns after less than a month", False),
    LeaderExit("ZAF", "2018-02-15", "Zuma resigns", False),
    LeaderExit("BRA", "2016-08-31", "Senate removes Rousseff", True),
    LeaderExit("USA", "2024-07-22", "Biden withdraws from presidential race", False),
]

# How the original (non-election) events map onto the taxonomy. Anything not listed is exogenous.
EVENT_RISK_OVERRIDES = {
    ("GBR", "2022-09-23"): "Event risk: surprise outcome",  # scheduled fiscal statement with unexpected content
    ("BRA", "2016-04-18"): "Event risk: expected outcome",  # scheduled impeachment vote, outcome expected
}


# Thematic risks build over months or years. Each theme lists the markets most exposed to it.
@dataclass(frozen=True)
class Theme:
    name: str
    countries: tuple
    start: str
    end: str  # None = latest data
    story: str


THEMES = [
    Theme("Euro-area debt crisis", ("DEU", "FRA"), "2010-04-23", "2012-07-26",
          "From Greece's bailout request to the ECB's 'whatever it takes'."),
    Theme("Brazil political and fiscal crisis", ("BRA",), "2014-10-27", "2016-08-31",
          "From Rousseff's re-election through the Car Wash scandal to her removal."),
    Theme("South Africa 'state capture' years", ("ZAF",), "2015-12-09", "2018-02-15",
          "From the Nene dismissal to Zuma's resignation."),
    Theme("Brexit negotiations", ("GBR",), "2016-06-24", "2020-01-31",
          "From the referendum result to the UK's formal exit."),
    Theme("U.S.-China trade war", ("USA", "AUS", "JPN", "DEU"), "2018-03-22", "2020-01-15",
          "From the first Section 301 tariff announcement to the Phase One deal."),
    Theme("European energy and security crisis", ("DEU", "FRA"), "2022-02-24", "2023-02-24",
          "The first year after Russia's full-scale invasion of Ukraine."),
    Theme("French political fragmentation", ("FRA",), "2024-06-10", None,
          "From the snap dissolution of the National Assembly to the latest data."),
    Theme("U.S. tariff regime of 2025", ("CAN", "USA", "DEU", "JPN"), "2025-02-03", "2025-12-31",
          "From the first broad tariffs on Canada and Mexico through the year of tariff escalation."),
]
