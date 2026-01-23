import sys
import time
import logging
from typing import Dict, List, Optional
import pandas as pd

sys.path.extend(["..", "..\\examples_llm", "."])

GROUP_NAME = "Aggressive_Growth_2027"
STOCKS: Dict[str, str] = {
    "칩스앤미디어": "094360",
    "필옵틱스": "161580",
    "GST": "083450",
    "에스피지": "058610",
    "AP위성": "211270",
    "크라우드웍스": "355390",
    "제이엘케이": "322510",
    "펩트론": "087010",
    "비에이치아이": "083650",
    "에이피알": "278470",
}

INTERVAL_SEC = 30
API_PRICE = "/uapi/domestic-stock/v1/quotations/inquire-price"
TR_PRICE = "FHKST01010100"
API_INV = "/uapi/domestic-stock/v1/quotations/inquire-investor"
TR_INV = "FHKST01010900"


def _safe_import_kis() -> Optional[object]:
    try:
        import kis_auth as ka
        return ka
    except Exception as e:
        logging.error(f"kis_auth import failed: {e}")
        return None


def fetch_price(ka_module, code: str) -> pd.DataFrame:
    if ka_module is None:
        return pd.DataFrame()
    try:
        env = ka_module.getTREnv()
        if not hasattr(env, "my_url") or not env.my_url:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
    res = ka_module._url_fetch(API_PRICE, TR_PRICE, "", params)
    if res.isOK():
        return pd.DataFrame(res.getBody().output, index=[0])
    return pd.DataFrame()


def fetch_investor(ka_module, code: str) -> pd.DataFrame:
    if ka_module is None:
        return pd.DataFrame()
    try:
        env = ka_module.getTREnv()
        if not hasattr(env, "my_url") or not env.my_url:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
    res = ka_module._url_fetch(API_INV, TR_INV, "", params)
    if res.isOK():
        return pd.DataFrame(res.getBody().output)
    return pd.DataFrame()


def format_price(name: str, code: str, df: pd.DataFrame) -> str:
    if df.empty:
        return f"{name}({code}) price: N/A"
    r = df.iloc[0]
    p = r.get("stck_prpr", None)
    c = r.get("prdy_vrss", None)
    rt = r.get("prdy_ctrt", None)
    if p is not None and rt is not None:
        return f"{name}({code}) price={p} change={c} rate={rt}%"
    return f"{name}({code}) {r.to_dict()}"


def format_investor(name: str, code: str, df: pd.DataFrame) -> List[str]:
    alerts: List[str] = []
    if df.empty:
        return alerts
    alerts.append(f"ALERT {name}({code}) investor data received")
    return alerts


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ka = _safe_import_kis()
    try:
        if ka is not None:
            ka.auth(svr="prod")
    except Exception as e:
        logging.warning(f"auth failed: {e}")
    logging.info(f"group: {GROUP_NAME}")
    logging.info(f"watchlist: {', '.join(STOCKS.keys())}")
    try:
        while True:
            for n, c in STOCKS.items():
                try:
                    p = fetch_price(ka, c)
                    logging.info(format_price(n, c, p))
                    inv = fetch_investor(ka, c)
                    for line in format_investor(n, c, inv):
                        logging.info(line)
                except Exception as e:
                    logging.error(f"{n}({c}) error: {e}")
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        logging.info("stopped")


if __name__ == "__main__":
    main()
