import os
import sys
from datetime import datetime, timedelta
import requests
import time
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
EXAMPLES_USER_DIR = os.path.join(PROJECT_ROOT, "examples_user")
if EXAMPLES_USER_DIR not in sys.path:
    sys.path.append(EXAMPLES_USER_DIR)

import kis_auth as ka
from examples_llm.domestic_stock.market_cap.market_cap import market_cap
from examples_llm.domestic_stock.inquire_daily_itemchartprice.inquire_daily_itemchartprice import inquire_daily_itemchartprice

def _load_env():
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        p = os.path.join(root, ".env")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

def _now():
    return datetime.today()

def _fmt_date(d):
    return d.strftime("%Y%m%d")

def _pick_price_cols(df):
    cols = df.columns.tolist()
    candidates = ["stck_prpr", "stck_clpr", "stck_prdy_clpr"]
    for c in candidates:
        if c in cols:
            return c
    return None

def _growth_over_3y(code, env="demo"):
    end = _now()
    start = end - timedelta(days=365*3 + 5)
    d1 = _fmt_date(start)
    d2 = _fmt_date(end)
    for _ in range(4):
        ka.smart_sleep()
        df1, df2 = inquire_daily_itemchartprice(env, "J", str(code).zfill(6), d1, d2, "M", "1")
        src = df1 if df1 is not None and not df1.empty else df2
        if src is not None and not src.empty:
            break
        time.sleep(0.7)
    src = df1 if df1 is not None and not df1.empty else df2
    if src is None or src.empty:
        return None
    pcol = _pick_price_cols(src)
    if pcol is None:
        return None
    s = pd.to_numeric(src[pcol], errors="coerce").dropna()
    if s.empty:
        return None
    first = float(s.iloc[0])
    last = float(s.iloc[-1])
    if first <= 0:
        return None
    growth = (last / first) - 1.0
    return {"code": str(code).zfill(6), "start": first, "end": last, "growth": growth}

def _top_codes(limit=300):
    df = market_cap("", "J", "20174", "0", "0000", "0", "0", "", "")
    if df is None or df.empty:
        return []
    col_code = "mksc_shrn_iscd" if "mksc_shrn_iscd" in df.columns else None
    if col_code is None:
        return []
    return df[col_code].astype(str).head(limit).tolist()

def find_undervalued_3y(env="demo", limit_codes=150, top_n=10, throttle_sec=0.25):
    _load_env()
    ka.auth(svr="vps" if env == "demo" else "prod")
    codes = _top_codes(limit_codes)
    rows = []
    for c in codes:
        r = _growth_over_3y(c, env)
        if r is not None:
            rows.append(r)
        ka.smart_sleep()
        time.sleep(throttle_sec)
    out = pd.DataFrame(rows)
    if out.empty:
        print("no data")
        return out
    out["growth_pct"] = (out["growth"] * 100.0).round(2)
    out = out.sort_values("growth").head(top_n).reset_index(drop=True)
    print(out[["code", "start", "end", "growth_pct"]].to_string(index=False))
    return out

def optional_deepseek_comment(df):
    _load_env()
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key or df is None or df.empty:
        return ""
    listed = "\n".join([f'{row["code"]}: {row["growth_pct"]:.2f}%' for _, row in df.iterrows()])
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a stock analyst."},
            {"role": "user", "content": f"3년 수익률이 낮은 국내 상장주식 후보들:\n{listed}\n저평가 가능성이 높은 순으로 10개 간단 코멘트."}
        ],
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=body, timeout=30)
        if r.status_code == 200:
            js = r.json()
            txt = js["choices"][0]["message"]["content"]
            print("\nLLM 의견:\n" + txt)
            return txt
        else:
            print(f"DeepSeek 오류 {r.status_code}")
            return ""
    except Exception as e:
        print(str(e))
        return ""

if __name__ == "__main__":
    df = find_undervalued_3y(env="demo", limit_codes=300, top_n=10)
    optional_deepseek_comment(df)
