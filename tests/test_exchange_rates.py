import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

import data_fetcher
import frankfurter_fetcher
from models import CnbcQuote, ExchangeRates


def make_history(values):
    return pd.DataFrame({"Close": values})


def assert_float_list_almost_equal(test_case, actual, expected):
    test_case.assertEqual(len(actual), len(expected))
    for actual_value, expected_value in zip(actual, expected):
        test_case.assertAlmostEqual(actual_value, expected_value)


def print_exchange_snapshot(exchange):
    print("\nCalculated exchange rates:")
    print(f"USD/KRW: {exchange['USD/KRW'].price:.2f}")
    print(f"JPY/KRW (100 JPY): {exchange['JPY/KRW'].price:.2f}")
    print(f"EUR/KRW: {exchange['EUR/KRW'].price:.2f}")
    print(f"CNY/KRW: {exchange['CNY/KRW'].price:.2f}")


class FrankfurterFetcherTests(unittest.TestCase):
    @patch("frankfurter_fetcher.urlopen")
    def test_fetch_frankfurter_rates_maps_expected_currency_pairs(self, mock_urlopen):
        usd_response = MagicMock()
        usd_response.__enter__.return_value = usd_response
        usd_response.__exit__.return_value = False
        usd_response.read.return_value = json.dumps(
            {"rates": {"KRW": 1330.0, "JPY": 150.0, "CNY": 7.2}}
        ).encode("utf-8")

        eur_response = MagicMock()
        eur_response.__enter__.return_value = eur_response
        eur_response.__exit__.return_value = False
        eur_response.read.return_value = json.dumps({"rates": {"USD": 1.08}}).encode(
            "utf-8"
        )

        mock_urlopen.side_effect = [usd_response, eur_response]

        rates = frankfurter_fetcher.fetch_frankfurter_rates()

        self.assertEqual(
            rates,
            ExchangeRates(
                usd_krw=1330.0,
                usd_jpy=150.0,
                eur_usd=1.08,
                usd_cny=7.2,
            ),
        )
        self.assertEqual(mock_urlopen.call_count, 2)
        usd_request = mock_urlopen.call_args_list[0].args[0]
        eur_request = mock_urlopen.call_args_list[1].args[0]

        self.assertIn("base=USD", usd_request.full_url)
        self.assertIn("symbols=KRW%2CJPY%2CCNY", usd_request.full_url)
        self.assertEqual(usd_request.get_header("User-agent"), "Macro-Pulse/1.0")
        self.assertEqual(usd_request.get_header("Accept"), "application/json")

        self.assertIn("base=EUR", eur_request.full_url)
        self.assertIn("symbols=USD", eur_request.full_url)
        self.assertEqual(eur_request.get_header("User-agent"), "Macro-Pulse/1.0")
        self.assertEqual(eur_request.get_header("Accept"), "application/json")


class ExchangeRateCalculationTests(unittest.TestCase):
    @patch.dict(data_fetcher.YF_TICKERS, {}, clear=True)
    @patch.dict(
        data_fetcher.YF_RATES_HISTORY,
        {
            "USD/KRW": "KRW=X",
            "JPY/KRW": "JPYKRW=X",
            "EUR/KRW": "EURKRW=X",
        },
        clear=True,
    )
    @patch("data_fetcher.fetch_cnbc_data", return_value={})
    @patch(
        "data_fetcher.fetch_frankfurter_rates",
        return_value=ExchangeRates(
            usd_krw=1330.0,
            usd_jpy=150.0,
            eur_usd=1.08,
            usd_cny=7.2,
        ),
    )
    @patch("data_fetcher.yf.Ticker")
    def test_fetch_all_data_builds_expected_exchange_results(
        self,
        mock_ticker,
        _mock_fx,
        _mock_cnbc,
    ):
        history_by_ticker = {
            "KRW=X": make_history([1310.0, 1315.0, 1320.0, 1322.0, 1324.0, 1328.0, 1329.0]),
            "JPYKRW=X": make_history([9.0, 9.05, 9.1, 9.15, 9.2, 9.25, 9.3]),
            "EURKRW=X": make_history([1420.0, 1425.0, 1428.0, 1430.0, 1432.0, 1434.0, 1435.0]),
        }

        def ticker_side_effect(symbol):
            ticker = MagicMock()
            ticker.history.return_value = history_by_ticker.get(symbol, pd.DataFrame())
            return ticker

        mock_ticker.side_effect = ticker_side_effect

        results = data_fetcher.fetch_all_data()

        exchange = {item.name: item for item in results["exchange"]}
        usd_krw = exchange["USD/KRW"]
        jpy_krw = exchange["JPY/KRW"]
        eur_krw = exchange["EUR/KRW"]
        cny_krw = exchange["CNY/KRW"]

        self.assertAlmostEqual(usd_krw.price, 1330.0)
        self.assertAlmostEqual(usd_krw.change, 2.0)
        self.assertAlmostEqual(usd_krw.change_pct, (2.0 / 1328.0) * 100)
        assert_float_list_almost_equal(
            self,
            usd_krw.history,
            [1310.0, 1315.0, 1320.0, 1322.0, 1324.0, 1328.0, 1329.0],
        )

        expected_jpy_krw = (1330.0 / 150.0) * 100
        self.assertAlmostEqual(jpy_krw.price, expected_jpy_krw)
        self.assertAlmostEqual(jpy_krw.change, expected_jpy_krw - 925.0)
        self.assertAlmostEqual(
            jpy_krw.change_pct,
            ((expected_jpy_krw - 925.0) / 925.0) * 100,
        )
        assert_float_list_almost_equal(
            self,
            jpy_krw.history,
            [900.0, 905.0, 910.0, 915.0, 920.0, 925.0, 930.0],
        )

        expected_eur_krw = 1330.0 * 1.08
        self.assertAlmostEqual(eur_krw.price, expected_eur_krw)
        self.assertAlmostEqual(eur_krw.change, expected_eur_krw - 1434.0)
        self.assertAlmostEqual(
            eur_krw.change_pct,
            ((expected_eur_krw - 1434.0) / 1434.0) * 100,
        )
        assert_float_list_almost_equal(
            self,
            eur_krw.history,
            [1420.0, 1425.0, 1428.0, 1430.0, 1432.0, 1434.0, 1435.0],
        )

        self.assertAlmostEqual(cny_krw.price, 1330.0 / 7.2)
        self.assertIsNone(cny_krw.change)
        self.assertIsNone(cny_krw.change_pct)
        self.assertEqual(cny_krw.history, [])

        print_exchange_snapshot(exchange)

    @patch.dict(data_fetcher.YF_TICKERS, {}, clear=True)
    @patch.dict(data_fetcher.YF_RATES_HISTORY, {}, clear=True)
    @patch(
        "data_fetcher.fetch_cnbc_data",
        return_value={
            ".KSVKOSPI": CnbcQuote(
                name="VKOSPI",
                price=66.61,
                change=-5.21,
                change_pct=-7.254246728,
            ),
            "JP10Y": CnbcQuote(
                name="Japan 10Y Treasury",
                price=2.184,
                change=-0.001,
                change_pct=-0.04576659,
            ),
            "KR10Y": CnbcQuote(
                name="Korea 10Y Treasury",
                price=3.629,
                change=-0.112,
                change_pct=-2.993851911,
            ),
        },
    )
    @patch("data_fetcher.fetch_frankfurter_rates", return_value=ExchangeRates())
    def test_fetch_all_data_keeps_cnbc_daily_change_values(
        self,
        _mock_fx,
        _mock_cnbc,
    ):
        results = data_fetcher.fetch_all_data()

        volatility = {item.name: item for item in results["volatility"]}
        bonds = {item.name: item for item in results["commodities_rates"]}

        self.assertAlmostEqual(volatility["VKOSPI"].price, 66.61)
        self.assertAlmostEqual(volatility["VKOSPI"].change, -5.21)
        self.assertAlmostEqual(volatility["VKOSPI"].change_pct, -7.254246728)

        self.assertAlmostEqual(bonds["Japan 10Y Treasury"].price, 2.184)
        self.assertAlmostEqual(bonds["Japan 10Y Treasury"].change, -0.001)
        self.assertAlmostEqual(
            bonds["Japan 10Y Treasury"].change_pct,
            -0.04576659,
        )

        self.assertAlmostEqual(bonds["Korea 10Y Treasury"].price, 3.629)
        self.assertAlmostEqual(bonds["Korea 10Y Treasury"].change, -0.112)
        self.assertAlmostEqual(
            bonds["Korea 10Y Treasury"].change_pct,
            -2.993851911,
        )


if __name__ == "__main__":
    unittest.main()
