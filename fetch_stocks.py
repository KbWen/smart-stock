import yfinance as yf
import pandas as pd
import requests
import io
import urllib3
from datetime import datetime, timedelta

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── 1. 從 TWSE 抓上市股票資訊 ──────────────────
def get_twse_info():
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    try:
        response = requests.get(url, timeout=30, verify=False)
        # 證交所 open_data 每個欄位都有引號，且用逗號隔開
        # 欄位順序: "日期","證券代號","證券名稱","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"
        df = pd.read_csv(io.StringIO(response.text), encoding="utf-8", dtype=str)
        
        info = {}
        for _, row in df.iterrows():
            try:
                code = str(row.iloc[1]).strip()
                name = str(row.iloc[2]).strip()
                vol_str = str(row.iloc[3]).replace(',', '').strip()
                volume = int(vol_str) if vol_str.isdigit() else 0
                
                if code.isdigit() and len(code) == 4:
                    info[code + ".TW"] = {"名稱": name, "成交量": volume}
            except:
                continue
        return info
    except Exception as e:
        print(f"抓取上市股票資訊失敗: {e}")
        return {}

# ── 2. 從 TPEX 抓上櫃股票資訊 ──────────────────
def get_tpex_info():
    today = datetime.now()
    roc_date = f"{today.year - 1911}/{today.month:02d}/{today.day:02d}"
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?d={roc_date}&o=csv"
    try:
        response = requests.get(url, timeout=30, verify=False)
        content = response.content.decode('cp950', errors='ignore')
        # 櫃買中心 CSV 格式: 前 3 行是標題，第 4 行 (skiprows=3) 是欄位名稱
        df = pd.read_csv(io.StringIO(content), skiprows=3, header=0, dtype=str)
        
        info = {}
        for _, row in df.iterrows():
            try:
                if pd.isna(row.iloc[0]): continue
                code = str(row.iloc[0]).strip()
                name = str(row.iloc[1]).strip()
                vol_str = str(row.iloc[2]).replace(',', '').strip()
                volume = int(vol_str) if vol_str.isdigit() else 0
                
                if code.isdigit() and len(code) == 4:
                    info[code + ".TWO"] = {"名稱": name, "成交量": volume}
            except:
                continue
        return info
    except Exception as e:
        print(f"抓取上櫃股票資訊失敗: {e}")
        return {}

# ── 3. 批次下載，比對兩天收盤價 ───────────────
def compare_prices(all_info, date_new=None, date_old=None, min_volume=100000):
    today = datetime.now()
    if date_new is None:
        # 取最近的工作日（週一至週五）
        date_new_dt = today - timedelta(days=max(0, today.weekday() - 4) if today.weekday() >= 5 else 0)
        date_new = date_new_dt.strftime('%Y-%m-%d')
    if date_old is None:
        date_old = (datetime.strptime(date_new, '%Y-%m-%d') - timedelta(days=9)).strftime('%Y-%m-%d')

    tickers = sorted(list(all_info.keys()))

    # 流動性過濾
    filtered_tickers = [t for t in tickers if all_info[t]["成交量"] >= min_volume]
    print(f"原始股票數: {len(tickers)}, 流動性符合 (成交量 >= {min_volume}): {len(filtered_tickers)}")
    print(f"比對區間: {date_old} → {date_new}")

    if not filtered_tickers:
        return pd.DataFrame()

    dl_start = (datetime.strptime(date_old, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
    dl_end = (datetime.strptime(date_new, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    chunk_size = 50
    results = []

    for i in range(0, len(filtered_tickers), chunk_size):
        batch = filtered_tickers[i:i+chunk_size]
        print(f"下載第 {i+1} 至 {min(i+chunk_size, len(filtered_tickers))} 檔資料...")
        try:
            data = yf.download(batch, start=dl_start, end=dl_end,
                               progress=False, auto_adjust=True)
            
            if data.empty: continue
            
            close_data = data["Close"] if "Close" in data.columns else data
            if isinstance(close_data, pd.Series):
                close_data = close_data.to_frame()
                
            close_data.index = close_data.index.strftime('%Y-%m-%d')
            
            for ticker in close_data.columns:
                try:
                    if date_old in close_data.index and date_new in close_data.index:
                        p_old = close_data.loc[date_old, ticker]
                        p_new = close_data.loc[date_new, ticker]
                        
                        if pd.notna(p_old) and pd.notna(p_new) and p_new > p_old:
                            results.append({
                                "代號": ticker.replace(".TW", "").replace(".TWO", ""),
                                "名稱": all_info[ticker]["名稱"],
                                "市場": "上市" if ".TW" in ticker else "上櫃",
                                "成交量": all_info[ticker]["成交量"],
                                f"{date_old} 收盤": round(p_old, 2),
                                f"{date_new} 收盤": round(p_new, 2),
                                "漲幅 %": round((p_new - p_old) / p_old * 100, 2)
                            })
                except:
                    continue
        except Exception:
            continue
            
    if not results:
        return pd.DataFrame()
        
    return pd.DataFrame(results).sort_values("漲幅 %", ascending=False)

if __name__ == "__main__":
    print("取得資訊中...")
    twse_all = get_twse_info()
    tpex_all = get_tpex_info()
    all_info = {**twse_all, **tpex_all}
    
    if not all_info:
        print("未取得任何股票資訊。")
    else:
        # 下限 10 萬股
        result_df = compare_prices(all_info, min_volume=100000)
        
        if result_df.empty:
            print("\n查無符合條件的股票。")
        else:
            print(f"\n符合條件股票共 {len(result_df)} 檔：")
            print(result_df.head(50).to_string(index=False))
            
            filename = "tw_stocks_analysis_refined.csv"
            result_df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n完成！結果已存成 {filename}")
