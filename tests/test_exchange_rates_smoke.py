import json
import os
import sys
import unittest
from urllib.request import urlopen


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from frankfurter_fetcher import (
    build_frankfurter_latest_url,
    build_frankfurter_request,
    fetch_frankfurter_rates,
)


def print_live_exchange_snapshot(rates, usd_date, eur_date, usd_url, eur_url):
    print("\nFrankfurter live endpoints:")
    print(f"USD endpoint: {usd_url}")
    print(f"EUR endpoint: {eur_url}")
    print(f"USD response date: {usd_date}")
    print(f"EUR response date: {eur_date}")
    print("Live exchange rates:")
    print(f"USD/KRW: {rates.usd_krw:.4f}")
    print(f"USD/JPY: {rates.usd_jpy:.4f}")
    print(f"EUR/USD: {rates.eur_usd:.4f}")
    print(f"USD/CNY: {rates.usd_cny:.4f}")
    print(f"JPY/KRW (100 JPY): {(rates.usd_krw / rates.usd_jpy) * 100:.4f}")
    print(f"EUR/KRW: {rates.usd_krw * rates.eur_usd:.4f}")
    print(f"CNY/KRW: {rates.usd_krw / rates.usd_cny:.4f}")


@unittest.skipUnless(
    os.environ.get("RUN_LIVE_SMOKE_TESTS") == "1",
    "Set RUN_LIVE_SMOKE_TESTS=1 to hit the live Frankfurter API.",
)
class FrankfurterSmokeTests(unittest.TestCase):
    def test_live_frankfurter_endpoints_return_expected_rates(self):
        usd_url = build_frankfurter_latest_url("USD", ["KRW", "JPY", "CNY"])
        eur_url = build_frankfurter_latest_url("EUR", ["USD"])

        with urlopen(build_frankfurter_request("USD", ["KRW", "JPY", "CNY"]), timeout=15) as response:
            usd_data = json.load(response)
        with urlopen(build_frankfurter_request("EUR", ["USD"]), timeout=15) as response:
            eur_data = json.load(response)

        usd_rates = usd_data.get("rates", {})
        eur_rates = eur_data.get("rates", {})

        self.assertEqual(usd_data.get("base"), "USD")
        self.assertEqual(eur_data.get("base"), "EUR")
        self.assertIn("date", usd_data)
        self.assertIn("date", eur_data)
        self.assertGreater(usd_rates.get("KRW", 0), 0)
        self.assertGreater(usd_rates.get("JPY", 0), 0)
        self.assertGreater(usd_rates.get("CNY", 0), 0)
        self.assertGreater(eur_rates.get("USD", 0), 0)

        mapped_rates = fetch_frankfurter_rates()

        self.assertAlmostEqual(mapped_rates.usd_krw, usd_rates["KRW"])
        self.assertAlmostEqual(mapped_rates.usd_jpy, usd_rates["JPY"])
        self.assertAlmostEqual(mapped_rates.usd_cny, usd_rates["CNY"])
        self.assertAlmostEqual(mapped_rates.eur_usd, eur_rates["USD"])

        print_live_exchange_snapshot(
            mapped_rates,
            usd_data["date"],
            eur_data["date"],
            usd_url,
            eur_url,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
