import os
import sys
import unittest

import yfinance as yf


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from cnbc_fetcher import CNBC_QUOTES, fetch_cnbc_data
from data_fetcher import YF_TICKERS
from frankfurter_fetcher import fetch_frankfurter_rates


@unittest.skipUnless(
    os.environ.get("RUN_LIVE_SMOKE_TESTS") == "1",
    "Set RUN_LIVE_SMOKE_TESTS=1 to hit live market data sources.",
)
class ProviderSmokeTests(unittest.TestCase):
    def test_yahoo_finance_tickers_return_recent_close(self):
        for definitions in YF_TICKERS.values():
            for definition in definitions:
                with self.subTest(symbol=definition.symbol):
                    history = yf.Ticker(definition.symbol).history(period="1d")
                    self.assertFalse(history.empty)
                    self.assertGreater(float(history["Close"].iloc[-1]), 0)

    def test_frankfurter_returns_expected_pairs(self):
        rates = fetch_frankfurter_rates()
        self.assertGreater(rates.usd_krw or 0, 0)
        self.assertGreater(rates.usd_jpy or 0, 0)
        self.assertGreater(rates.eur_usd or 0, 0)
        self.assertGreater(rates.usd_cny or 0, 0)

    def test_cnbc_returns_all_supported_symbols(self):
        quotes = fetch_cnbc_data(list(CNBC_QUOTES))
        self.assertEqual(set(quotes), set(CNBC_QUOTES))
        for symbol, quote in quotes.items():
            with self.subTest(symbol=symbol):
                self.assertGreater(quote.price, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
