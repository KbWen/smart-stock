import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_bulk_meta():
    tickers = "2330,2317,2454,2308,2303,2881,2882,2382,2412,2886"
    print(f"Testing bulk meta for: {tickers}")
    
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/v4/meta?tickers={tickers}")
        response.raise_for_status()
        data = response.json()
        elapsed = (time.time() - start_time) * 1000
        
        print(f"Bulk Meta response received in {elapsed:.2f}ms")
        print(json.dumps(data, indent=2))
        
        if elapsed < 500:
            print("✅ Performance AC Met (< 500ms)")
        else:
            print("❌ Performance AC Failed (> 500ms)")
            
    except Exception as e:
        print(f"❌ Test Failed: {e}")

def test_regression():
    print("Testing regression for individual stock detail...")
    try:
        response = requests.get(f"{BASE_URL}/api/v4/stock/2330")
        response.raise_for_status()
        print("✅ Individual detail API works.")
    except Exception as e:
        print(f"❌ Regression Test Failed: {e}")

if __name__ == "__main__":
    # Wait a bit for server to start
    time.sleep(2)
    test_bulk_meta()
    test_regression()
