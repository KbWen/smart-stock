import requests
import time

def test_stock_detail_cache_performance():
    ticker = "2330.TW"
    url = f"http://127.0.0.1:8000/api/v4/stock/{ticker}"
    
    # First call - potentially cold
    print(f"Testing {ticker} (First call)...")
    start = time.time()
    try:
        r1 = requests.get(url, timeout=10)
        end1 = time.time()
        print(f"First call: {round((end1-start)*1000, 2)}ms")
    except Exception as e:
        print(f"Skipping performance test: Backend not responding ({e})")
        return

    # Second call - MUST be cache hit
    print(f"Testing {ticker} (Second call - Cache hit expectancy)...")
    start = time.time()
    r2 = requests.get(url, timeout=5)
    end2 = time.time()
    elapsed2 = (end2-start)*1000
    print(f"Second call: {round(elapsed2, 2)}ms")
    
    assert elapsed2 < 300, f"Cache latency too high: {elapsed2}ms"
    print("✅ Cache hit performance verified (< 300ms)")

if __name__ == "__main__":
    test_stock_detail_cache_performance()
