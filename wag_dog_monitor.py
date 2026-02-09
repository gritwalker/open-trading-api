import os
import sys
import time
from datetime import datetime
import requests
import pandas as pd
import logging
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = BASE_DIR
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
EXAMPLES_USER_DIR = os.path.join(PROJECT_ROOT, "examples_user")
if EXAMPLES_USER_DIR not in sys.path:
    sys.path.append(EXAMPLES_USER_DIR)

import kis_auth as ka
from examples_llm.domestic_futureoption.index_futures_realtime_conclusion.index_futures_realtime_conclusion import index_futures_realtime_conclusion
from examples_llm.domestic_stock.index_program_trade.index_program_trade import index_program_trade

logging.getLogger().setLevel(logging.WARNING)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
logger = logging.getLogger("wagdog")
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(_handler)
logger.propagate = False
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

def _get_latest_futures_code() -> str:
    try:
        from examples_llm.domestic_futureoption.display_board_futures.display_board_futures import display_board_futures
        df = display_board_futures("F", "20503", "MKI")
        if df is not None and not df.empty:
            df = df.copy()
            code_col = "futs_shrn_iscd" if "futs_shrn_iscd" in df.columns else None
            name_col = "hts_kor_isnm" if "hts_kor_isnm" in df.columns else None
            vol_col = "acml_vol" if "acml_vol" in df.columns else None
            if code_col is None:
                raise RuntimeError("no code column in display_board_futures")
            # KOSPI200 선물 (101xxxx) 필터
            mask = df[code_col].astype(str).str.startswith("101")
            cand = df[mask]
            if cand.empty:
                cand = df
            if vol_col and vol_col in cand.columns:
                cand[vol_col] = pd.to_numeric(cand[vol_col], errors="coerce")
                cand = cand.sort_values(vol_col, ascending=False)
            code = str(cand.iloc[0][code_col])
            if name_col and name_col in cand.columns:
                nm = str(cand.iloc[0][name_col])
                logger.info(f"✅ 자동 인식된 근월물: {nm} ({code})")
            else:
                logger.info(f"✅ 자동 인식된 근월물 코드: {code}")
            return code
    except Exception as e:
        logger.info(f"❌ 종목 코드 자동 조회 실패: {e}")
    return "101S12"

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
        self.has_position = False
        self.entry_basis = None
        self.entry_nabt = None
        self._last_min = None
        self._last_when = None

    def _state_log(self, when: str):
        b = "-" if self.last_basis is None else f"{self.last_basis:.2f}"
        n = "-" if self.last_nabt_ntby is None else f"{int(self.last_nabt_ntby)}"
        pos = "보유" if self.has_position else "대기"
        logger.info(f"⏰ {when} | 상태: {pos} | 베이시스: {b} | 비차익 순매수: {n}")

    def on_result(self, ws, tr_id: str, result: pd.DataFrame, data_map: dict):
        try:
            if result is None or result.empty:
                return
            cols = result.columns.tolist()
            when = None
            if "bsop_hour" in cols:
                try:
                    s = str(result["bsop_hour"].iloc[-1])
                    when = f"{s[:2]}:{s[2:4]}:{s[4:6]}" if len(s) >= 6 else None
                except Exception:
                    when = None
            if when is None:
                when = datetime.now().strftime("%H:%M:%S")
            self._last_when = when
            if tr_id == "H0IFCNT0":
                bcol = "mrkt_basis" if "mrkt_basis" in cols else None
                if bcol:
                    try:
                        self.last_basis = float(pd.to_numeric(result[bcol], errors="coerce").dropna().iloc[-1])
                    except Exception:
                        pass
                if self.last_basis is not None and _in_window():
                    if self.last_basis < 0 and not self.notified_warn:
                        logger.info(f"⚠️ 백워데이션 감지: 베이시스 {self.last_basis:.2f}")
                        _tg_send(f"경고: 백워데이션 발생, 베이시스 {self.last_basis:.2f}")
                        self.notified_warn = True
            elif tr_id == "H0UPPGM0":
                tcol = "nabt_smtn_ntby_qty" if "nabt_smtn_ntby_qty" in cols else None
                if tcol:
                    try:
                        self.last_nabt_ntby = float(pd.to_numeric(result[tcol], errors="coerce").dropna().iloc[-1])
                    except Exception:
                        pass
            if _in_window():
                min_key = when[:5] if len(when) >= 5 else datetime.now().strftime("%H:%M")
                if self._last_min != min_key:
                    self._last_min = min_key
                    self._state_log(when)
                if (self.last_basis is not None and self.last_nabt_ntby is not None):
                    if (not self.has_position) and self.last_basis >= self.basis_th and self.last_nabt_ntby >= self.nabt_ntby_th:
                        logger.info(f"✅ 매수 신호: 베이시스 {self.last_basis:.2f} (기준 {self.basis_th:.2f}), 비차익 순매수 {int(self.last_nabt_ntby)} (기준 {self.nabt_ntby_th})")
                        _tg_send(f"매수 신호: 베이시스 {self.last_basis:.2f}, 비차익 순매수 {int(self.last_nabt_ntby)}")
                        self.has_position = True
                        self.entry_basis = self.last_basis
                        self.entry_nabt = self.last_nabt_ntby
                    elif self.has_position:
                        exit_by_basis = (self.last_basis < max(0.05, self.basis_th * 0.7))
                        exit_by_nabt = (self.last_nabt_ntby < self.nabt_ntby_th * 0.6)
                        if exit_by_basis or exit_by_nabt:
                            logger.info(f"📤 매도 신호: 기준 이탈 (베이시스 {self.last_basis:.2f}, 비차익 순매수 {int(self.last_nabt_ntby)})")
                            _tg_send(f"매도 신호: 베이시스 {self.last_basis:.2f}, 비차익 순매수 {int(self.last_nabt_ntby)}")
                            self.has_position = False
                            self.entry_basis = None
                            self.entry_nabt = None
        except Exception:
            pass

def _start_heartbeat(mon: Monitor, interval_sec: int):
    def loop():
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            when = mon._last_when or now
            mon._state_log(when)
            time.sleep(interval_sec)
    t = threading.Thread(target=loop, daemon=True)
    t.start()

def main():
    _load_env()
    env = os.environ.get("KIS_ENV", "real")
    ka.auth(svr="vps" if env == "demo" else "prod")
    ka.auth_ws()
    fut_code = os.environ.get("FUT_CODE", "").strip() or _get_latest_futures_code()
    idx_keys = os.environ.get("INDEX_KEYS", "0001").split(",")
    basis_th = float(os.environ.get("BASIS_TH", "0.20"))
    nabt_ntby_th = int(os.environ.get("NABT_NTBY_TH", "1500"))
    heartbeat = int(os.environ.get("HEARTBEAT_SEC", "60"))
    mon = Monitor(fut_code, idx_keys, basis_th, nabt_ntby_th)
    kws = ka.KISWebSocket(api_url="/tryitout")
    logger.info(f"🔌 구독 요청: 지수선물 체결({fut_code}), 지수 프로그램매매({', '.join(idx_keys)})")
    _start_heartbeat(mon, heartbeat)
    kws.subscribe(request=index_futures_realtime_conclusion, data=[fut_code])
    kws.subscribe(request=index_program_trade, data=idx_keys)
    kws.start(on_result=mon.on_result)

if __name__ == "__main__":
    main()
