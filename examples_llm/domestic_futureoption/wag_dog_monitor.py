import os
import sys
import time
from datetime import datetime
import requests
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
EXAMPLES_USER_DIR = os.path.join(PROJECT_ROOT, "examples_user")
if EXAMPLES_USER_DIR not in sys.path:
    sys.path.append(EXAMPLES_USER_DIR)

import kis_auth as ka
from examples_llm.domestic_futureoption.index_futures_realtime_conclusion.index_futures_realtime_conclusion import index_futures_realtime_conclusion
from examples_llm.domestic_stock.index_program_trade.index_program_trade import index_program_trade

def _load_env():
    try:
        p = os.path.join(PROJECT_ROOT, ".env")
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

def _now_hm():
    kst = datetime.now()
    return int(kst.strftime("%H%M"))

def _in_window():
    hm = _now_hm()
    return 900 <= hm <= 1030

def _tg_send(text: str):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    cid = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not cid or not text:
        return
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    try:
        requests.post(url, json={"chat_id": cid, "text": text}, timeout=10)
    except Exception:
        pass

class Monitor:
    def __init__(self, fut_code: str, idx_keys: list[str], basis_th: float = 0.20, nabt_ntby_th: int = 1500):
        self.fut_code = fut_code
        self.idx_keys = idx_keys
        self.basis_th = basis_th
        self.nabt_ntby_th = nabt_ntby_th
        self.last_basis = None
        self.last_nabt_ntby = None
        self.notified_buy = False
        self.notified_warn = False

    def on_result(self, ws, tr_id: str, result: pd.DataFrame, data_map: dict):
        try:
            if result is None or result.empty:
                return
            cols = result.columns.tolist()
            if tr_id == "H0IFCNT0":
                bcol = "mrkt_basis" if "mrkt_basis" in cols else None
                if bcol:
                    try:
                        self.last_basis = float(pd.to_numeric(result[bcol], errors="coerce").dropna().iloc[-1])
                    except Exception:
                        pass
                if self.last_basis is not None and _in_window():
                    if self.last_basis < 0 and not self.notified_warn:
                        _tg_send(f"경고: 백워데이션 발생, 베이시스 {self.last_basis:.2f}")
                        self.notified_warn = True
                    if self.last_basis >= self.basis_th and self.last_nabt_ntby is not None and self.last_nabt_ntby >= self.nabt_ntby_th and not self.notified_buy:
                        _tg_send(f"진입: 베이시스 {self.last_basis:.2f} / 비차익 순매수 {int(self.last_nabt_ntby)}")
                        self.notified_buy = True
            elif tr_id == "H0UPPGM0":
                tcol = "nabt_smtn_ntby_qty" if "nabt_smtn_ntby_qty" in cols else None
                if tcol:
                    try:
                        self.last_nabt_ntby = float(pd.to_numeric(result[tcol], errors="coerce").dropna().iloc[-1])
                    except Exception:
                        pass
                if self.last_nabt_ntby is not None and _in_window():
                    if self.last_basis is not None and self.last_basis >= self.basis_th and self.last_nabt_ntby >= self.nabt_ntby_th and not self.notified_buy:
                        _tg_send(f"진입: 베이시스 {self.last_basis:.2f} / 비차익 순매수 {int(self.last_nabt_ntby)}")
                        self.notified_buy = True
        except Exception:
            pass

def main():
    _load_env()
    env = os.environ.get("KIS_ENV", "real")
    fut_code = os.environ.get("FUT_CODE", "101S12")
    idx_keys = os.environ.get("INDEX_KEYS", "0001").split(",")
    basis_th = float(os.environ.get("BASIS_TH", "0.20"))
    nabt_ntby_th = int(os.environ.get("NABT_NTBY_TH", "1500"))
    ka.auth(svr="vps" if env == "demo" else "prod")
    ka.auth_ws()
    mon = Monitor(fut_code, idx_keys, basis_th, nabt_ntby_th)
    kws = ka.KISWebSocket(api_url="/tryitout")
    kws.subscribe(request=index_futures_realtime_conclusion, data=[fut_code])
    kws.subscribe(request=index_program_trade, data=idx_keys)
    kws.start(on_result=mon.on_result)

if __name__ == "__main__":
    main()
