import os
import sys
import unittest
from unittest.mock import MagicMock, patch


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

import cnbc_fetcher


SAMPLE_QUOTE_HTML = """
<html>
  <body>
    <div class="QuoteStrip-lastPriceStripContainer">
      <span class="QuoteStrip-lastPrice">3.629%</span>
      <span class="QuoteStrip-changeDown">
        <img class="QuoteStrip-changeIcon" src="icon.svg" alt="quote price arrow down">
        <span>-0.112</span>
        <span>(-2.99%)</span>
      </span>
    </div>
  </body>
</html>
"""


class CnbcFetcherTests(unittest.TestCase):
    def test_parse_cnbc_quote_extracts_price_and_daily_change(self):
        quote = cnbc_fetcher.parse_cnbc_quote(SAMPLE_QUOTE_HTML)

        self.assertAlmostEqual(quote.price, 3.629)
        self.assertAlmostEqual(quote.change, -0.112)
        self.assertAlmostEqual(quote.change_pct, -2.99)

    @patch("cnbc_fetcher.urlopen")
    def test_fetch_cnbc_data_fetches_requested_symbols(self, mock_urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = SAMPLE_QUOTE_HTML.encode("utf-8")
        mock_urlopen.return_value = response

        quotes = cnbc_fetcher.fetch_cnbc_data(["KR10Y"])

        self.assertIn("KR10Y", quotes)
        self.assertAlmostEqual(quotes["KR10Y"].price, 3.629)
        self.assertAlmostEqual(quotes["KR10Y"].change, -0.112)
        self.assertEqual(quotes["KR10Y"].name, "Korea 10Y Treasury")


if __name__ == "__main__":
    unittest.main()
