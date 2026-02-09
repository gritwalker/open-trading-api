import os
import sys
import time
import logging
import threading
import requests
import pandas as pd
from datetime import datetime
 
class _StdoutFilter:
    def __init__(self, orig):
        self.orig = orig
        self.buf = ""
    def write(self, s):
        self.buf += s
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            if not any(x in line for x in ["PINGPONG", "send message >>", "received message >>", "### RECV", "### SEND"]):
                self.orig.write(line + "\n")
    def flush(self):
        if self.buf:
            if not any(x in self.buf for x in ["PINGPONG", "send message >>", "received message >>", "### RECV", "### SEND"]):
                self.orig.write(self.buf)
            self.buf = ""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
EXAMPLES_USER_DIR = os.path.join(BASE_DIR, "examples_user")
if EXAMPLES_USER_DIR not in sys.path:
    sys.path.append(EXAMPLES_USER_DIR)

import kis_auth as ka
from examples_user.domestic_futureoption.domestic_futureoption_functions_ws import krx_ngt_futures_ccnl
from examples_llm.domestic_futureoption.display_board_futures.display_board_futures import display_board_futures
from examples_llm.domestic_stock.inquire_asking_price_exp_ccn.inquire_asking_price_exp_ccn import inquire_asking_price_exp_ccn
from examples_user.etfetn.etfetn_functions import inquire_price as etfetn_inquire_price
from examples_llm.domestic_stock.search_info.search_info import search_info
from examples_llm.domestic_stock.search_stock_info.search_stock_info import search_stock_info

logging.getLogger().setLevel(logging.WARNING)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
logger = logging.getLogger("morning_sync")
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(_handler)
logger.propagate = False
if os.environ.get("SILENCE_WS_LOG", "1") == "1":
    sys.stdout = _StdoutFilter(sys.stdout)

def _load_env():
    p = os.path.join(BASE_DIR, ".env")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

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

def _fmt_pct(x: float) -> str:
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.2f}%"

def _easy_msg(now: str, code: str, pct: float, lev: float) -> str:
    base = _fmt_pct(pct)
    lev_est = _fmt_pct(pct * lev)
    return (
        f"아침 시초가 예상 요약\n"
        f"시간: {now}\n"
        f"야간선물({code}): {base}\n"
        f"설명: 시초가는 야간선물 등락률에 동기화되는 경향이 큼\n"
        f"레버리지({int(lev)}배) 예상 시초가: {lev_est}\n"
        f"주의: 9:00 이후는 장중 수급 영향"
    )

def _resolve_fut_name(code: str) -> str | None:
    try:
        df = display_board_futures("F", "20503", "MKI")
        if df is None or df.empty:
            return None
        code_col = "futs_shrn_iscd" if "futs_shrn_iscd" in df.columns else None
        name_col = "hts_kor_isnm" if "hts_kor_isnm" in df.columns else None
        if code_col is None or name_col is None:
            return None
        df = df.copy()
        hit = df[df[code_col].astype(str) == str(code)]
        if not hit.empty:
            return str(hit.iloc[0][name_col]).strip()
        return None
    except Exception:
        return None

def _fallback_pct_via_board() -> tuple[float | None, str | None, str | None]:
    try:
        df = display_board_futures("F", "20503", "MKI")
        if df is None or df.empty:
            return None, None, None
        code_col = "futs_shrn_iscd" if "futs_shrn_iscd" in df.columns else None
        pct_col = "futs_prdy_ctrt" if "futs_prdy_ctrt" in df.columns else None
        name_col = "hts_kor_isnm" if "hts_kor_isnm" in df.columns else None
        vol_col = "acml_vol" if "acml_vol" in df.columns else None
        if code_col is None or pct_col is None:
            return None, None, None
        df = df.copy()
        mask = df[code_col].astype(str).str.startswith("101")
        cand = df[mask]
        if cand.empty:
            cand = df
        if vol_col and vol_col in cand.columns:
            cand[vol_col] = pd.to_numeric(cand[vol_col], errors="coerce")
            cand = cand.sort_values(vol_col, ascending=False)
        pct = float(pd.to_numeric(cand[pct_col], errors="coerce").dropna().iloc[0])
        code = str(cand.iloc[0][code_col])
        nm = None
        if name_col and name_col in cand.columns:
            nm = str(cand.iloc[0][name_col]).strip()
        return pct, code, nm
    except Exception:
        return None, None, None

def _auto_futures_code() -> tuple[str | None, str | None]:
    try:
        df = display_board_futures("F", "20503", "MKI")
        if df is None or df.empty:
            return None, None
        code_col = "futs_shrn_iscd" if "futs_shrn_iscd" in df.columns else None
        name_col = "hts_kor_isnm" if "hts_kor_isnm" in df.columns else None
        vol_col = "acml_vol" if "acml_vol" in df.columns else None
        if code_col is None:
            return None, None
        df = df.copy()
        mask = df[code_col].astype(str).str.startswith("101")
        cand = df[mask]
        if cand.empty:
            cand = df
        if vol_col and vol_col in cand.columns:
            cand[vol_col] = pd.to_numeric(cand[vol_col], errors="coerce")
            cand = cand.sort_values(vol_col, ascending=False)
        code = str(cand.iloc[0][code_col])
        nm = None
        if name_col and name_col in cand.columns:
            nm = str(cand.iloc[0][name_col]).strip()
        return code, nm
    except Exception:
        return None, None

def _preopen_expected_lines(env: str, codes: list[str]) -> list[str]:
    lines = []
    for c in codes:
        try:
            hoqa, exp = inquire_asking_price_exp_ccn(env_dv=env, fid_cond_mrkt_div_code="J", fid_input_iscd=c)
            name = None
            known = {
                "069500": "KODEX 200",
                "122630": "KODEX 레버리지",
            }
            try:
                cur = etfetn_inquire_price("J", c)
                if cur is not None and not cur.empty:
                    for nk in ["hts_kor_isnm", "HTS_KOR_ISNM", "prdt_name", "PRDT_NAME", "issu_nm", "ISSU_NM", "itmd_nm", "ITMD_NM"]:
                        if nk in cur.columns:
                            name = str(cur[nk].iloc[0]).strip()
                            break
            except Exception:
                pass
            if not name and hoqa is not None and not hoqa.empty:
                for nk in ["hts_kor_isnm", "HTS_KOR_ISNM", "prdt_name", "PRDT_NAME", "issu_nm", "ISSU_NM", "itmd_nm", "ITMD_NM"]:
                    if nk in hoqa.columns:
                        v = str(hoqa[nk].iloc[0]).strip()
                        if v:
                            name = v
                            break
            if not name:
                try:
                    def _guess(df: pd.DataFrame) -> str | None:
                        if df is None or df.empty:
                            return None
                        pats = ["isnm", "kor", "name", "nm"]
                        for col in df.columns:
                            lc = str(col).lower()
                            if any(p in lc for p in pats):
                                v = str(df[col].iloc[0]).strip()
                                if v and not v.isdigit():
                                    return v
                        return None
                    name = _guess(cur) or _guess(hoqa)
                except Exception:
                    pass
            if not name:
                try:
                    base = search_info(pdno=c, prdt_type_cd="300")
                    if base is not None and not base.empty:
                        for nk in ["hts_kor_isnm", "HTS_KOR_ISNM", "prdt_name", "PRDT_NAME", "issu_nm", "ISSU_NM"]:
                            if nk in base.columns:
                                v = str(base[nk].iloc[0]).strip()
                                if v:
                                    name = v
                                    break
                except Exception:
                    pass
            if not name:
                try:
                    base2 = search_stock_info("300", c)
                    if base2 is not None and not base2.empty:
                        for nk in ["hts_kor_isnm", "HTS_KOR_ISNM", "prdt_name", "PRDT_NAME", "issu_nm", "ISSU_NM"]:
                            if nk in base2.columns:
                                v = str(base2[nk].iloc[0]).strip()
                                if v:
                                    name = v
                                    break
                except Exception:
                    pass
            if c in known:
                name = known[c]
            if exp is not None and not exp.empty:
                antc = None
                vrss = None
                ct = None
                for key in ["antc_cnpr", "ANTC_CNPR"]:
                    if key in exp.columns:
                        antc = exp[key].iloc[0]
                        break
                for key in ["antc_cntg_vrss", "ANTC_CNTG_VRSS"]:
                    if key in exp.columns:
                        vrss = exp[key].iloc[0]
                        break
                for key in ["antc_cntg_prdy_ctrt", "ANTC_CNTG_PRDY_CTRT"]:
                    if key in exp.columns:
                        ct = exp[key].iloc[0]
                        break
                def _fmt(x):
                    try:
                        x = float(x)
                        return f"{x:.2f}"
                    except Exception:
                        return str(x)
                if antc is not None or vrss is not None or ct is not None:
                    if name:
                        head = f"{name}({c})"
                    else:
                        head = c
                    line = f"{head} 예상체결가: { _fmt(antc) } | 대비: { _fmt(vrss) } | 전일대비율: { _fmt(ct) }%"
                    lines.append(line)
        except Exception:
            pass
    return lines

def main():
    _load_env()
    env = os.environ.get("KIS_ENV", "real")
    ka.auth(svr="vps" if env == "demo" else "prod")
    ka.auth_ws()
    code = os.environ.get("NGT_FUT_CODE", "").strip()
    name = None
    if not code:
        acode, aname = _auto_futures_code()
        code = acode or "101W9000"
        name = aname
    if not name:
        name = _resolve_fut_name(code)
    lev = float(os.environ.get("LEV_MULT", "2"))
    timeout = int(os.environ.get("SYNC_TIMEOUT_SEC", "30"))
    pre_codes = [x.strip() for x in os.environ.get("PREOPEN_CODES", "").split(",") if x.strip()]
    kws = ka.KISWebSocket(api_url="/tryitout")
    sent = {"done": False}
    def on_timeout():
        if not sent["done"]:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fpct, fcode, fname = _fallback_pct_via_board()
            if fpct is not None and fcode:
                show = f"{fname}({fcode})" if fname else fcode
                msg = _easy_msg(now, show, fpct, lev) + "\n(야간 데이터 지연으로 전광판 대체값 사용)"
                _tg_send(msg)
                print(msg)
                if pre_codes:
                    lines = _preopen_expected_lines(env, pre_codes)
                    if lines:
                        more = "장전 예상체결가\n" + "\n".join(lines)
                        _tg_send(more)
                        print(more)
                sent["done"] = True
                os._exit(0)
            else:
                msg = f"예상 시초가 동기화 실패\n시간: {now}\n야간선물 코드: {code}\n사유: 실시간 데이터 지연/종료로 등락률을 수신하지 못함"
                _tg_send(msg)
                print(msg)
                os._exit(0)
    threading.Timer(timeout, on_timeout).start()
    def on_result(ws, tr_id: str, result: pd.DataFrame, data_map: dict):
        try:
            if sent["done"]:
                return
            if result is None or result.empty:
                return
            cols = result.columns.tolist()
            if "futs_prdy_ctrt" in cols:
                try:
                    pct = float(pd.to_numeric(result["futs_prdy_ctrt"], errors="coerce").dropna().iloc[-1])
                except Exception:
                    return
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                show = f"{name}({code})" if name else code
                msg = _easy_msg(now, show, pct, lev)
                _tg_send(msg)
                print(msg)
                if pre_codes:
                    lines = _preopen_expected_lines(env, pre_codes)
                    if lines:
                        more = "장전 예상체결가\n" + "\n".join(lines)
                        _tg_send(more)
                        print(more)
                sent["done"] = True
                os._exit(0)
        except Exception:
            pass
    kws.subscribe(request=krx_ngt_futures_ccnl, data=[code])
    kws.start(on_result=on_result)

if __name__ == "__main__":
    main()
