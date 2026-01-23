import sys
import time
import logging
from typing import Dict, List, Optional
import pandas as pd

sys.path.extend([
    "..",
    "..\\examples_llm",
    "."
])

API_URL = "/uapi/domestic-stock/v1/quotations/inquire-price"
TR_ID = "FHKST01010100"

STOCKS: Dict[str, str] = {
    "서진시스템": "178320",
    "대한광통신": "010170",
    "한전기술": "052690",
}

INTERVAL_SEC = 10


def fetch_price(code: str, ka_module) -> pd.DataFrame:
    if ka_module is None:
        return pd.DataFrame()
    try:
        env = ka_module.getTREnv()
        if not hasattr(env, "my_url") or not env.my_url:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code
    }
    res = ka_module._url_fetch(API_URL, TR_ID, "", params)
    if res.isOK():
        return pd.DataFrame(res.getBody().output, index=[0])
    return pd.DataFrame()


def format_row(df: pd.DataFrame, name: str, code: str) -> str:
    if df.empty:
        return f"{name}({code}) price: N/A"
    row = df.iloc[0]
    price = row.get("stck_prpr", None)
    chg = row.get("prdy_vrss", None)
    rate = row.get("prdy_ctrt", None)
    if price is not None and rate is not None:
        return f"{name}({code}) price={price} change={chg} rate={rate}%"
    return f"{name}({code}) {row.to_dict()}"


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ka: Optional[object] = None
    try:
        import kis_auth as ka  # delayed import to avoid import-time config errors
    except Exception as e:
        logging.error(f"kis_auth import failed: {e}")
    try:
        if ka is not None:
            ka.auth(svr="prod")
    except Exception as e:
        logging.warning(f"auth failed: {e}")
    symbols: List[str] = list(STOCKS.keys())
    logging.info(f"polling: {', '.join(symbols)} every {INTERVAL_SEC}s")
    try:
        while True:
            for name, code in STOCKS.items():
                try:
                    df = fetch_price(code, ka)
                    logging.info(format_row(df, name, code))
                except Exception as e:
                    logging.error(f"{name}({code}) error: {e}")
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        logging.info("stopped")


if __name__ == "__main__":
    main()
