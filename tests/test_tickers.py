import yfinance as yf
import sys
import os
import logging
from dotenv import load_dotenv

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

load_dotenv()

# Add src to path to import project modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from cnbc_fetcher import fetch_cnbc_data
from frankfurter_fetcher import fetch_frankfurter_rates

yf_tickers = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Nikkei 225": "^N225",
    "Euro Stoxx 50": "^STOXX50E",
    "Shanghai Composite": "000001.SS",
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "Gold": "GC=F",
    "US 10Y": "^TNX",
    "Bitcoin": "BTC-USD",
    "VIX": "^VIX",
}

cnbc_symbols = [".KSVKOSPI", "JP10Y", "KR10Y"]

print("--- Testing Yahoo Finance Tickers ---")
for name, ticker in yf_tickers.items():
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            print(f"[OK] {name} ({ticker}): {data['Close'].iloc[-1]}")
        else:
            print(f"[FAIL] {name} ({ticker}): No data")
    except Exception as e:
        print(f"[ERROR] {name} ({ticker}): {e}")

print("\n--- Testing Frankfurter FX Rates ---")

try:
    fx_data = fetch_frankfurter_rates()
    for pair in ["USD/KRW", "USD/JPY", "EUR/USD", "USD/CNY"]:
        price = fx_data.get(pair)
        if price:
            print(f"[OK] {pair}: {price}")
        else:
            print(f"[FAIL] {pair}: No data found")
except Exception as e:
    print(f"[ERROR] Frankfurter fetch failed: {e}")

print("\n--- Testing CNBC Tickers ---")

key = os.environ.get("RAPIDAPI_CNBC_KEY")
if not key:
    print("[WARN] RAPIDAPI_CNBC_KEY not found in env. CNBC-only tests will fail/skip.")

try:
    cnbc_data = fetch_cnbc_data(cnbc_symbols)
    if not cnbc_data:
        print("[FAIL] No data returned from CNBC Fetcher (Check API Key?)")
    else:
        for symbol in cnbc_symbols:
            data = cnbc_data.get(symbol)
            if data:
                print(
                    f"[OK] {data.get('name', symbol)} ({symbol}): {data.get('price')}"
                )
            else:
                print(f"[FAIL] {symbol}: No data found")

except Exception as e:
    print(f"[ERROR] CNBC Fetcher failed: {e}")
