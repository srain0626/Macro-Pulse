import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1/latest"


def fetch_frankfurter_rates():
    """
    Fetches latest FX rates required for the KR exchange calculations.
    Returns:
        dict {
            "USD/KRW": float,
            "USD/JPY": float,
            "EUR/USD": float,
            "USD/CNY": float,
        }
    """

    def fetch_latest(base, symbols):
        query = urlencode({"base": base, "symbols": ",".join(symbols)})
        url = f"{FRANKFURTER_BASE_URL}?{query}"
        with urlopen(url, timeout=15) as response:
            return json.load(response)

    try:
        usd_data = fetch_latest("USD", ["KRW", "JPY", "CNY"])
        eur_data = fetch_latest("EUR", ["USD"])

        usd_rates = usd_data.get("rates", {})
        eur_rates = eur_data.get("rates", {})

        return {
            "USD/KRW": usd_rates.get("KRW"),
            "USD/JPY": usd_rates.get("JPY"),
            "EUR/USD": eur_rates.get("USD"),
            "USD/CNY": usd_rates.get("CNY"),
        }
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        logging.error(f"Frankfurter API error: {exc}")
        return {}
