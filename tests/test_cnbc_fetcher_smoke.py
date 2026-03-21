import os
import sys
import unittest


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from cnbc_fetcher import CNBC_QUOTES, fetch_cnbc_data


@unittest.skipUnless(
    os.environ.get("RUN_LIVE_SMOKE_TESTS") == "1",
    "Set RUN_LIVE_SMOKE_TESTS=1 to hit the live CNBC quote pages.",
)
class CnbcFetcherSmokeTests(unittest.TestCase):
    def test_live_cnbc_quote_pages_return_expected_values(self):
        symbols = list(CNBC_QUOTES)
        quotes = fetch_cnbc_data(symbols)

        self.assertEqual(set(quotes), set(symbols))

        print("\nCNBC live quotes:")
        for symbol in symbols:
            quote = quotes[symbol]
            self.assertGreater(quote.price, 0)
            self.assertIsNotNone(quote.change)
            self.assertIsNotNone(quote.change_pct)
            print(
                f"{symbol}: price={quote.price:.3f}, "
                f"change={quote.change:+.3f}, "
                f"change_pct={quote.change_pct:+.2f}%"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
