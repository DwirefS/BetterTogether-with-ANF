import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------------
# PRODUCTION INTEGRATION GUIDE — Real-Time Market Data
# -------------------------------------------------------------------------------------
# The functions below currently return mock/simulated data suitable for demos and
# development environments. When you are ready to connect to live market data feeds,
# consider the following tiered approach:
#
# FREE / LOW-COST OPTIONS:
#   - Alpha Vantage (https://www.alphavantage.co) — Free tier: 25 req/day,
#     Premium: $49/mo for 500 req/day. Good for news sentiment + earnings calendar.
#     pip install alpha-vantage
#
#   - Yahoo Finance (yfinance) — Unofficial, free, no API key required.
#     pip install yfinance
#     Caveat: Scraper-based; may break without warning. Not suitable for production.
#
#   - Polygon.io (https://polygon.io) — Free tier: 5 API calls/min.
#     Starter: $29/mo for real-time equities data + news.
#
# ENTERPRISE OPTIONS (requires license or subscription):
#   - Bloomberg Terminal API (BLPAPI) — Industry standard for institutional finance.
#     Requires Bloomberg Terminal license (~$24k/yr/seat).
#     pip install blpapi
#
#   - Refinitiv/LSEG Eikon Data API — Alternative to Bloomberg.
#     Requires Refinitiv Eikon license.
#     pip install refinitiv-data
#
#   - S&P Capital IQ — Comprehensive fundamentals + transcripts.
#     Requires enterprise license.
#
# IMPLEMENTATION PATTERN:
#   To swap in a real provider, create a new module (e.g., market_data_live.py)
#   that implements the same function signatures (fetch_market_news, fetch_earnings_transcripts)
#   and configure the active module via environment variable:
#     MARKET_DATA_PROVIDER=mock|alphavantage|bloomberg|refinitiv
#
#   Then in the NeMo Agent Toolkit workflow.yaml, point the tool to the active module.
# -------------------------------------------------------------------------------------


def fetch_market_news(ticker: str) -> str:
    """
    Fetch recent news events affecting the ticker symbol.

    Args:
        ticker: The stock ticker to search for (e.g. AAPL, MSFT, TSLA).

    Note:
        Currently returns mock data for demo purposes. See the Production Integration
        Guide at the top of this file for options to connect to real market data APIs
        (Alpha Vantage, Bloomberg, Refinitiv, Polygon.io, etc.).
    """
    logger.info(f"Market Data Agent fetching news for {ticker}")

    # [MOCK DATA] Simulated market news for demo/development.
    # Replace with real API calls when budget allows. See module-level docstring above.

    ticker = ticker.upper()
    mock_db = {
        "AAPL": "News: Apple announces new supply chain partnerships in Asia to diversify manufacturing. Expected to reduce production bottlenecks by Q4.",
        "MSFT": "News: Microsoft expands Azure capacity with new regions to support skyrocketing demand for AI services and NVIDIA GPU compute.",
        "TSLA": "News: Tesla secures new lithium mining contracts, ensuring battery supply for the next 5 years. Margin expansion expected.",
        "NVDA": "News: NVIDIA reports record data center revenue driven by enterprise AI adoption. NIM microservices and Blueprint deployments accelerating across cloud providers.",
        "GOOGL": "News: Alphabet expands Gemini AI integration across Google Cloud and Workspace, increasing enterprise AI revenue by 35% YoY.",
        "AMZN": "News: Amazon Web Services launches next-generation GPU instances powered by custom Trainium chips, intensifying competition in AI infrastructure.",
    }

    return mock_db.get(ticker, f"No recent material news found for {ticker}.")


def fetch_earnings_transcripts(ticker: str) -> str:
    """
    Retrieve transcript excerpts and analyst Q&A from the most recent earnings call.

    Args:
        ticker: The stock ticker to search for.

    Note:
        Currently returns mock data for demo purposes. See the Production Integration
        Guide at the top of this file for options to connect to real earnings data APIs
        (S&P Capital IQ, Bloomberg BLPAPI, Alpha Vantage Earnings Calendar, etc.).
    """
    logger.info(f"Earnings Agent analyzing transcripts for {ticker}")

    ticker = ticker.upper()
    mock_db = {
        "AAPL": "CEO states strong services revenue growth offsets hardware cyclicality. CFO hints at increased share buybacks.",
        "MSFT": "CFO notes Azure AI revenue contributing significantly to cloud growth metrics. Enterprise NIM adoption driving margin expansion.",
        "TSLA": "Management highlights focus on autonomous driving software margins over vehicle volume.",
        "NVDA": "CEO emphasizes data center revenue now exceeds gaming. NIM microservices seeing enterprise adoption across financial services, healthcare, and manufacturing verticals.",
        "GOOGL": "CEO highlights cloud AI revenue growth as primary driver. CFO notes Gemini API usage up 400% QoQ.",
        "AMZN": "CFO notes AWS AI-related revenue growing at 3x the rate of core cloud services. Bedrock platform adoption accelerating.",
    }

    return mock_db.get(ticker, f"No recent earnings transcripts parsed for {ticker}.")
