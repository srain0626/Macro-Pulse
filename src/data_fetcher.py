import os
import tempfile

import yfinance as yf

from cnbc_fetcher import fetch_cnbc_data
from frankfurter_fetcher import fetch_frankfurter_rates
from logging_utils import get_logger
from models import (
    AssetSnapshot,
    ReportDataset,
    TickerDefinition,
    ValueFormat,
    coerce_cnbc_quote,
    coerce_exchange_rates,
)


logger = get_logger(__name__)

# Yahoo Tickers (default)
YF_TICKERS = {
    "indices_domestic": (
        TickerDefinition("KOSPI", "^KS11"),
        TickerDefinition("KOSDAQ", "^KQ11"),
    ),
    "indices_overseas": (
        TickerDefinition("S&P 500", "^GSPC"),
        TickerDefinition("Nasdaq", "^IXIC"),
        TickerDefinition("Euro Stoxx 50", "^STOXX50E"),
        TickerDefinition("Nikkei 225", "^N225"),
        TickerDefinition("Hang Seng", "^HSI"),
        TickerDefinition("Shanghai Composite", "000001.SS"),
    ),
    "commodities_rates": (
        TickerDefinition("Gold", "GC=F"),
        TickerDefinition("Silver", "SI=F"),
        TickerDefinition("Copper", "HG=F"),
        TickerDefinition("US 10Y Treasury", "^TNX", value_format=ValueFormat.YIELD_3),
    ),
    "crypto": (
        TickerDefinition("Bitcoin", "BTC-USD"),
        TickerDefinition("Ethereum", "ETH-USD"),
    ),
    "volatility": (
        TickerDefinition("VIX", "^VIX"),
    ),
}

# YF Tickers for Exchange Rates History (Hybrid Approach)
YF_RATES_HISTORY = {
    "USD/KRW": "KRW=X",
    "JPY/KRW": "JPYKRW=X",
    "EUR/KRW": "EURKRW=X",
}

# CNBC Symbols to fetch
CNBC_SYMBOLS = [
    ".KSVKOSPI",  # VKOSPI
    "JP10Y",  # Japan 10Y
    "KR10Y",  # Korea 10Y
]


def fetch_all_data() -> ReportDataset:
    _configure_runtime_cache()
    results: ReportDataset = {
        "indices_domestic": [],
        "indices_overseas": [],
        "volatility": [],
        "commodities_rates": [],
        "exchange": [],
        "crypto": [],
    }

    # 0. Fetch YF History for Rates (for Trend/Change)
    yf_rates_data = {}
    logger.info("Fetching YF rates history...")
    for name, ticker in YF_RATES_HISTORY.items():
        try:
            hist = yf.Ticker(ticker).history(period="1mo")
            if not hist.empty:
                yf_rates_data[name] = hist
        except Exception as e:
            logger.error("Error fetching YF history for %s: %s", name, e)

    # 1. Fetch CNBC Data
    logger.info("Fetching CNBC data...")
    cnbc_data = fetch_cnbc_data(CNBC_SYMBOLS)

    # 2. Fetch FX rates from Frankfurter
    logger.info("Fetching Frankfurter FX data...")
    fx_data = coerce_exchange_rates(fetch_frankfurter_rates())
    usd_krw = fx_data.usd_krw
    usd_jpy = fx_data.usd_jpy
    eur_usd = fx_data.eur_usd
    usd_cny = fx_data.usd_cny

    # Helper to create result item
    def create_item(
        name,
        price,
        change,
        change_pct,
        history=None,
        use_blank=False,
        value_format=ValueFormat.STANDARD_2,
    ):
        if use_blank:
            change = None
            change_pct = None
            history = []

        normalized_history = history if history is not None else [price] if price else []
        return AssetSnapshot(
            name=name,
            price=float(price) if price is not None else None,
            change=float(change) if change is not None else None,
            change_pct=float(change_pct) if change_pct is not None else None,
            history=[float(value) for value in normalized_history],
            value_format=value_format,
        )

    # Exchange Rates Calculation
    if usd_krw:
        # USD/KRW
        # Hybrid: Use Frankfurter price, but YF History/Change if available
        yf_hist = yf_rates_data.get("USD/KRW")
        price = usd_krw
        change = 0
        change_pct = 0
        history = [price]

        if yf_hist is not None and not yf_hist.empty:
            history = yf_hist["Close"].tail(7).tolist()
            prev_close = yf_hist["Close"].iloc[-2] if len(yf_hist) > 1 else price
            change = price - prev_close
            change_pct = (change / prev_close) * 100

        results["exchange"].append(
            create_item("USD/KRW", price, change, change_pct, history)
        )

        # JPY/KRW
        if usd_jpy:
            price_jpykrw = (usd_krw / usd_jpy) * 100  # JPY/KRW (100 Yen)
            change = 0
            change_pct = 0
            history = [price_jpykrw]

            # Hybrid YF
            yf_hist = yf_rates_data.get("JPY/KRW")
            if yf_hist is not None and not yf_hist.empty:
                # Yahoo Finance JPYKRW=X is per 1 JPY (~9.x), but we use per 100 JPY (~9xx).
                # Scale YF history by 100
                history_scaled = yf_hist["Close"] * 100
                history = history_scaled.tail(7).tolist()
                prev_close = (
                    history_scaled.iloc[-2] if len(history_scaled) > 1 else price_jpykrw
                )
                change = price_jpykrw - prev_close
                change_pct = (change / prev_close) * 100

            results["exchange"].append(
                create_item("JPY/KRW", price_jpykrw, change, change_pct, history)
            )

        # EUR/KRW
        if eur_usd:
            price_eurkrw = usd_krw * eur_usd
            change = 0
            change_pct = 0
            history = [price_eurkrw]

            # Hybrid YF
            yf_hist = yf_rates_data.get("EUR/KRW")
            if yf_hist is not None and not yf_hist.empty:
                history = yf_hist["Close"].tail(7).tolist()
                prev_close = (
                    yf_hist["Close"].iloc[-2] if len(yf_hist) > 1 else price_eurkrw
                )
                change = price_eurkrw - prev_close
                change_pct = (change / prev_close) * 100

            results["exchange"].append(
                create_item("EUR/KRW", price_eurkrw, change, change_pct, history)
            )

        # CNY/KRW (Blank Change/Trend)
        if usd_cny:
            price = usd_krw / usd_cny
            results["exchange"].append(
                create_item("CNY/KRW", price, 0, 0, use_blank=True)
            )

    else:
        logger.warning("Frankfurter FX rates failed. Data might be incomplete.")

    # Add other CNBC items (Blank Change/Trend)
    # VKOSPI
    if ".KSVKOSPI" in cnbc_data:
        item = coerce_cnbc_quote(cnbc_data[".KSVKOSPI"])
        results["volatility"].append(
            create_item("VKOSPI", item.price, item.change, item.change_pct)
        )

    # Japan 10Y
    if "JP10Y" in cnbc_data:
        item = coerce_cnbc_quote(cnbc_data["JP10Y"])
        results["commodities_rates"].append(
            create_item(
                "Japan 10Y Treasury",
                item.price,
                item.change,
                item.change_pct,
                value_format=ValueFormat.YIELD_3,
            )
        )

    # Korea 10Y
    if "KR10Y" in cnbc_data:
        item = coerce_cnbc_quote(cnbc_data["KR10Y"])
        results["commodities_rates"].append(
            create_item(
                "Korea 10Y Treasury",
                item.price,
                item.change,
                item.change_pct,
                value_format=ValueFormat.YIELD_3,
            )
        )

    # 3. Fetch Yahoo Finance Data
    logger.info("Fetching Yahoo Finance data...")
    for category, items in YF_TICKERS.items():
        for definition in items:
            try:
                data = yf.Ticker(definition.symbol).history(period="1mo")
                if data.empty:
                    logger.warning(
                        "Yahoo Finance returned no history for %s (%s)",
                        definition.name,
                        definition.symbol,
                    )
                    continue

                last_price = data["Close"].iloc[-1]
                if len(data) > 1:
                    prev_price = data["Close"].iloc[-2]
                    change = last_price - prev_price
                    change_pct = (change / prev_price) * 100
                    history = data["Close"].tail(7).tolist()
                else:
                    change = 0
                    change_pct = 0
                    history = [last_price]

                results[category].append(
                    AssetSnapshot(
                        name=definition.name,
                        ticker=definition.symbol,
                        price=float(last_price),
                        change=float(change),
                        change_pct=float(change_pct),
                        history=[float(value) for value in history],
                        dates=[d.strftime("%m-%d") for d in data.tail(7).index],
                        value_format=definition.value_format,
                    )
                )

            except Exception as e:
                logger.error("Error fetching YF %s: %s", definition.name, e)

    # Reorder commodities_rates to ensure US 10Y is after Korea 10Y (Group Bonds)
    # Target Order: Japan 10Y, Korea 10Y, US 10Y, others...
    # Actually, let's just find US 10Y and move it to after Korea 10Y if both exist.

    cr_list = results["commodities_rates"]
    us_10y_idx = next(
        (i for i, x in enumerate(cr_list) if x.name == "US 10Y Treasury"), None
    )
    korea_10y_idx = next(
        (i for i, x in enumerate(cr_list) if x.name == "Korea 10Y Treasury"), None
    )

    if us_10y_idx is not None and korea_10y_idx is not None:
        # Move US 10Y to korea_10y_idx + 1
        item = cr_list.pop(us_10y_idx)
        # Re-calculate index of Korea because pop might have shifted it if US was before (unlikely)
        korea_10y_idx = next(
            (i for i, x in enumerate(cr_list) if x.name == "Korea 10Y Treasury"),
            None,
        )
        if korea_10y_idx is not None:
            cr_list.insert(korea_10y_idx + 1, item)
        else:
            cr_list.append(item)  # Fallback

    logger.info(
        "Completed fetch cycle with %s populated categories",
        sum(1 for items in results.values() if items),
    )

    return results


def _configure_runtime_cache() -> None:
    cache_dir = os.environ.get(
        "YFINANCE_CACHE_DIR", os.path.join(tempfile.gettempdir(), "macro-pulse-yfinance")
    )
    os.makedirs(cache_dir, exist_ok=True)
    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(cache_dir)


if __name__ == "__main__":
    data = fetch_all_data()
    print(data)
