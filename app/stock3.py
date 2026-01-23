import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QTextEdit,
    QHBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
EXAMPLES_DIR = os.path.join(PROJECT_ROOT, "examples_llm")
ORDER_CASH_DIR = os.path.join(EXAMPLES_DIR, "domestic_stock", "order_cash")
INQ_ACC_DIR = os.path.join(EXAMPLES_DIR, "domestic_stock", "inquire_account_balance")
INQ_BAL_DIR = os.path.join(EXAMPLES_DIR, "domestic_stock", "inquire_balance")
RANK_VOL_DIR = os.path.join(EXAMPLES_DIR, "domestic_stock", "volume_rank")
INQ_PRICE_DIR = os.path.join(EXAMPLES_DIR, "domestic_stock", "inquire_price")
for p in [PROJECT_ROOT, EXAMPLES_DIR, ORDER_CASH_DIR, INQ_ACC_DIR, INQ_BAL_DIR, RANK_VOL_DIR, INQ_PRICE_DIR]:
    if p not in sys.path:
        sys.path.append(p)

import kis_auth as ka
from order_cash import order_cash
from inquire_account_balance import inquire_account_balance
from inquire_balance import inquire_balance
from volume_rank import volume_rank
from inquire_price import inquire_price
import requests
HOLDINGS_COLMAP = {
    'pdno': '상품번호',
    'prdt_name': '상품명',
    'trad_dvsn_name': '매매구분명',
    'bfdy_buy_qty': '전일매수수량',
    'bfdy_sll_qty': '전일매도수량',
    'thdt_buyqty': '금일매수수량',
    'thdt_sll_qty': '금일매도수량',
    'hldg_qty': '보유수량',
    'ord_psbl_qty': '주문가능수량',
    'pchs_avg_pric': '매입평균가격',
    'pchs_amt': '매입금액',
    'prpr': '현재가',
    'evlu_amt': '평가금액',
    'evlu_pfls_amt': '평가손익금액',
    'evlu_pfls_rt': '평가손익율',
    'evlu_erng_rt': '평가수익율',
    'loan_dt': '대출일자',
    'loan_amt': '대출금액',
    'stln_slng_chgs': '대주매각대금',
    'expd_dt': '만기일자',
    'fltt_rt': '등락율',
    'bfdy_cprs_icdc': '전일대비증감',
    'item_mgna_rt_name': '종목증거금율명',
    'grta_rt_name': '보증금율명',
    'sbst_pric': '대용가격',
}
ACCOUNT_COLMAP = {
    'dnca_tot_amt': '예수금총금액',
    'nxdy_excc_amt': '익일정산금액',
    'prvs_rcdl_excc_amt': '가수도정산금액',
    'cma_evlu_amt': 'CMA평가금액',
    'bfdy_buy_amt': '전일매수금액',
    'bfdy_sll_amt': '전일매도금액',
    'nxdy_auto_rdpt_amt': '익일자동상환금액',
    'thdt_tlex_amt': '금일제비용금액',
    'evlu_amt': '평가금액',
    'evlu_pfls_amt': '평가손익금액',
    'evlu_amt_smtl': '평가금액합계',
    'evlu_amt_smtl_amt': '평가금액합계',
    'evlu_pfls_amt_smtl': '평가손익금액합계',
    'evlu_pfls_smtl_amt': '평가손익금액합계',
    'nass_tot_amt': '순자산총금액',
    'nass_amt': '순자산금액',
    'tot_asst_amt': '총자산금액',
    'pchs_amt': '매입금액',
    'pchs_amt_smtl': '매입금액합계',
    'pchs_amt_smtl_amt': '매입금액합계',
    'real_nass_amt': '실제순자산금액',
    'cma_auto_loan_amt': 'CMA자동대출금액',
    'tot_mgln_amt': '총담보대출금액',
    'crdt_fncg_amt': '신용융자금액',
    'thdt_buy_amt': '금일매수금액',
    'thdt_sll_amt': '금일매도금액',
    'scts_evlu_amt': '유가평가금액',
    'tot_evlu_amt': '총평가금액',
    'tot_stln_slng_chgs': '총대주매각대금',
    'bfdy_tot_asst_evlu_amt': '전일총자산평가금액',
    'asst_icdc_amt': '자산증감금액',
    'asst_icdc_erng_rt': '자산증감수익율',
    'fncg_amt_auto_rdpt_yn': '융자금자동상환여부',
}
RANK_COLMAP = {
    'hts_kor_isnm': 'HTS 한글 종목명',
    'mksc_shrn_iscd': '유가증권 단축 종목코드',
    'data_rank': '데이터 순위',
    'stck_prpr': '현재가',
    'prdy_vrss_sign': '전일 대비 부호',
    'prdy_vrss': '전일 대비',
    'prdy_ctrt': '등락률',
    'acml_vol': '누적 거래량',
    'prdy_vol': '전일 거래량',
    'lstn_stcn': '상장주식수',
    'avrg_vol': '평균 거래량',
    'n_befr_clpr_vrss_prpr_rate': '전일종가 대비 현재가 비율',
    'vol_inrt': '거래 증가율',
    'vol_tnrt': '거래 회전율',
    'nday_vol_tnrt': '최근N일 거래 회전율',
    'avrg_tr_pbmn': '평균 거래대금',
    'tr_pbmn_tnrt': '거래대금 회전율',
    'nday_tr_pbmn_tnrt': '최근N일 거래대금 회전율',
    'acml_tr_pbmn': '누적 거래대금',
}


class TradingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HTS 모의주식 트레이딩")
        self.resize(900, 720)
        self.env = "demo"
        self.deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.auto_timer = None
        self.rank_timer = None
        self.last_reauth_at = None
        self.init_ui()
        self.ensure_auth(self.env)
        self.prefill_account()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.init_trade_tab()
        self.init_account_tab()
        self.init_holdings_tab()
        self.init_ranking_tab()
        self.init_autotrade_tab()
        self.init_analysis_tab()
        root = QVBoxLayout()
        root.addWidget(self.tabs)
        self.setLayout(root)

    def init_trade_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        env_row = QHBoxLayout()
        env_label = QLabel("환경")
        self.env_combo = QComboBox()
        self.env_combo.addItems(["demo", "real"])
        self.env_combo.currentTextChanged.connect(self.on_env_change)
        self.auth_btn = QPushButton("인증")
        self.auth_btn.clicked.connect(self.on_auth_click)
        env_row.addWidget(env_label)
        env_row.addWidget(self.env_combo)
        env_row.addWidget(self.auth_btn)
        layout.addLayout(env_row)

        form = QFormLayout()
        self.cano_edit = QLineEdit()
        self.cano_edit.setReadOnly(True)
        self.prdt_edit = QLineEdit()
        self.prdt_edit.setReadOnly(True)
        self.code_edit = QLineEdit()
        self.qty_edit = QLineEdit()
        self.price_edit = QLineEdit()
        self.side_combo = QComboBox()
        self.side_combo.addItems(["buy", "sell"])
        self.orddvsn_combo = QComboBox()
        self.orddvsn_combo.addItems(["00"])
        form.addRow("계좌(앞8자리)", self.cano_edit)
        form.addRow("상품코드(뒤2자리)", self.prdt_edit)
        form.addRow("종목코드(6자리)", self.code_edit)
        form.addRow("주문수량", self.qty_edit)
        form.addRow("주문단가", self.price_edit)
        form.addRow("매수/매도", self.side_combo)
        form.addRow("주문구분", self.orddvsn_combo)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.order_btn = QPushButton("주문 실행")
        self.order_btn.clicked.connect(self.on_order_click)
        btn_row.addWidget(self.order_btn)
        layout.addLayout(btn_row)

        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        layout.addWidget(QLabel("주문 결과"))
        layout.addWidget(self.result_view, stretch=1)

        w.setLayout(layout)
        self.tabs.addTab(w, "주문")

    def init_account_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        control = QHBoxLayout()
        self.refresh_acc_btn = QPushButton("자산 조회")
        self.refresh_acc_btn.clicked.connect(self.on_refresh_account)
        control.addWidget(self.refresh_acc_btn)
        layout.addLayout(control)
        self.account_table = QTableWidget()
        layout.addWidget(QLabel("계좌 자산 현황"))
        layout.addWidget(self.account_table, stretch=1)
        w.setLayout(layout)
        self.tabs.addTab(w, "자산")

    def init_holdings_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        control = QHBoxLayout()
        self.refresh_hold_btn = QPushButton("보유주식 조회")
        self.refresh_hold_btn.clicked.connect(self.on_refresh_holdings)
        control.addWidget(self.refresh_hold_btn)
        layout.addLayout(control)
        self.holdings_table = QTableWidget()
        layout.addWidget(QLabel("보유주식"))
        layout.addWidget(self.holdings_table, stretch=1)
        w.setLayout(layout)
        self.tabs.addTab(w, "보유")

    def init_ranking_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        control = QHBoxLayout()
        self.rank_interval = QSpinBox()
        self.rank_interval.setRange(3, 300)
        self.rank_interval.setValue(10)
        self.rank_start_btn = QPushButton("실시간 시작")
        self.rank_stop_btn = QPushButton("중지")
        self.rank_start_btn.clicked.connect(self.on_start_ranking)
        self.rank_stop_btn.clicked.connect(self.on_stop_ranking)
        control.addWidget(QLabel("초"))
        control.addWidget(self.rank_interval)
        control.addWidget(self.rank_start_btn)
        control.addWidget(self.rank_stop_btn)
        layout.addLayout(control)
        self.rank_table = QTableWidget()
        layout.addWidget(QLabel("거래량 상위 Top20"))
        layout.addWidget(self.rank_table, stretch=1)
        w.setLayout(layout)
        self.tabs.addTab(w, "순위")

    def init_autotrade_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        form = QFormLayout()
        self.auto_code = QLineEdit()
        self.auto_qty = QSpinBox()
        self.auto_qty.setRange(1, 1000000)
        self.auto_buy = QDoubleSpinBox()
        self.auto_buy.setRange(0, 100000000)
        self.auto_buy.setDecimals(2)
        self.auto_sell = QDoubleSpinBox()
        self.auto_sell.setRange(0, 100000000)
        self.auto_sell.setDecimals(2)
        form.addRow("종목코드", self.auto_code)
        form.addRow("수량", self.auto_qty)
        form.addRow("자동매수 이하가격", self.auto_buy)
        form.addRow("자동매도 이상가격", self.auto_sell)
        layout.addLayout(form)
        btns = QHBoxLayout()
        self.auto_start_btn = QPushButton("자동매매 시작")
        self.auto_stop_btn = QPushButton("중지")
        self.auto_start_btn.clicked.connect(self.on_start_auto)
        self.auto_stop_btn.clicked.connect(self.on_stop_auto)
        btns.addWidget(self.auto_start_btn)
        btns.addWidget(self.auto_stop_btn)
        layout.addLayout(btns)
        self.auto_log = QTextEdit()
        self.auto_log.setReadOnly(True)
        layout.addWidget(QLabel("자동매매 로그"))
        layout.addWidget(self.auto_log, stretch=1)
        w.setLayout(layout)
        self.tabs.addTab(w, "자동매매")

    def init_analysis_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        form = QFormLayout()
        self.analysis_code = QLineEdit()
        self.analysis_model = QComboBox()
        self.analysis_model.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.deepseek_key_edit = QLineEdit()
        self.deepseek_key_edit.setText(self.deepseek_key)
        self.analysis_prompt = QTextEdit()
        form.addRow("종목코드", self.analysis_code)
        form.addRow("모델", self.analysis_model)
        form.addRow("API Key", self.deepseek_key_edit)
        layout.addLayout(form)
        layout.addWidget(QLabel("분석 요청"))
        layout.addWidget(self.analysis_prompt)
        self.analysis_btn = QPushButton("분석 실행")
        self.analysis_btn.clicked.connect(self.on_run_analysis)
        layout.addWidget(self.analysis_btn)
        self.analysis_result = QTextEdit()
        self.analysis_result.setReadOnly(True)
        layout.addWidget(QLabel("분석 결과"))
        layout.addWidget(self.analysis_result, stretch=1)
        w.setLayout(layout)
        self.tabs.addTab(w, "분석")

    def ensure_auth(self, env):
        if env == "demo":
            ka.auth(svr="vps", product="01")
        else:
            ka.auth(svr="prod", product="01")

    def force_reauth(self):
        from PyQt6.QtCore import QTimer
        try:
            config_root = os.path.join(os.path.expanduser("~"), "KIS", "config")
            token_path = os.path.join(config_root, f"KIS{datetime.today().strftime('%Y%m%d')}")
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                except Exception:
                    pass
        except Exception:
            pass
        self.ensure_auth(self.env)
        self.last_reauth_at = datetime.now()

    def backoff_reauth_and_retry(self, retry_fn):
        from PyQt6.QtCore import QTimer
        now = datetime.now()
        if self.last_reauth_at is None:
            self.force_reauth()
            QTimer.singleShot(1500, retry_fn)
            return
        delta = (now - self.last_reauth_at).total_seconds()
        if delta < 60:
            wait_ms = int((60 - delta) * 1000)
            QTimer.singleShot(wait_ms, lambda: (self.force_reauth(), QTimer.singleShot(1000, retry_fn)))
        else:
            self.force_reauth()
            QTimer.singleShot(1500, retry_fn)

    def prefill_account(self):
        try:
            trenv = ka.getTREnv()
            self.cano_edit.setText(getattr(trenv, "my_acct", "") or getattr(trenv, "my_acct", ""))
            self.prdt_edit.setText(getattr(trenv, "my_prod", "") or getattr(trenv, "my_prod", ""))
        except Exception:
            self.cano_edit.setText("")
            self.prdt_edit.setText("")

    def on_env_change(self, text):
        self.env = text

    def on_auth_click(self):
        self.ensure_auth(self.env)
        self.prefill_account()
        self.append_result("인증 완료")

    def append_result(self, text):
        self.result_view.append(text)

    def on_order_click(self):
        env_dv = self.env_combo.currentText()
        ord_dv = self.side_combo.currentText()
        cano = self.cano_edit.text().strip()
        acnt_prdt_cd = self.prdt_edit.text().strip()
        pdno = self.code_edit.text().strip()
        ord_dvsn = self.orddvsn_combo.currentText()
        qty_text = self.qty_edit.text().strip()
        price_text = self.price_edit.text().strip()

        if not (cano and acnt_prdt_cd and pdno and qty_text and price_text):
            self.append_result("입력값 확인 필요")
            return

        try:
            int_qty = int(qty_text)
            int_price = int(price_text)
            if int_qty <= 0 or int_price <= 0:
                self.append_result("수량/단가는 양수여야 함")
                return
        except ValueError:
            self.append_result("수량/단가 숫자 입력 필요")
            return

        try:
            df = order_cash(
                env_dv=env_dv,
                ord_dv=ord_dv,
                cano=cano,
                acnt_prdt_cd=acnt_prdt_cd,
                pdno=pdno,
                ord_dvsn=ord_dvsn,
                ord_qty=str(int_qty),
                ord_unpr=str(int_price),
                excg_id_dvsn_cd="KRX",
            )
            if isinstance(df, pd.DataFrame) and not df.empty:
                self.append_result(df.to_string(index=False))
            else:
                def retry():
                    df2 = order_cash(
                        env_dv=env_dv,
                        ord_dv=ord_dv,
                        cano=cano,
                        acnt_prdt_cd=acnt_prdt_cd,
                        pdno=pdno,
                        ord_dvsn=ord_dvsn,
                        ord_qty=str(int_qty),
                        ord_unpr=str(int_price),
                        excg_id_dvsn_cd="KRX",
                    )
                    if isinstance(df2, pd.DataFrame) and not df2.empty:
                        self.append_result(df2.to_string(index=False))
                    else:
                        self.append_result("주문 실패 또는 빈 응답")
                self.backoff_reauth_and_retry(retry)
        except Exception as e:
            self.append_result(f"에러: {str(e)}")

    def df_to_table(self, df: pd.DataFrame, table: QTableWidget, limit: int | None = None):
        if df is None:
            df = pd.DataFrame()
        if limit is not None:
            df = df.head(limit)
        formatted = df.copy()
        numeric_cols = []
        exclude_cols = {
            "pdno",
            "상품번호",
            "mksc_shrn_iscd",
            "유가증권 단축 종목코드",
        }
        for col in formatted.columns:
            if col in exclude_cols:
                continue
            series = formatted[col]
            coerced = pd.to_numeric(series.astype(str).str.replace(",", ""), errors="coerce")
            if coerced.notna().sum() > 0:
                numeric_cols.append(col)
                def _fmt(x):
                    if pd.isna(x):
                        return ""
                    y = float(x)
                    if y.is_integer():
                        return f"{y:,.0f}"
                    s = f"{y:,.2f}"
                    if s.endswith(".00"):
                        s = s[:-3]
                    return s
                formatted[col] = coerced.apply(_fmt)
        table.clear()
        table.setRowCount(len(formatted))
        table.setColumnCount(len(formatted.columns))
        table.setHorizontalHeaderLabels([str(c) for c in formatted.columns])
        for r in range(len(formatted)):
            for c in range(len(formatted.columns)):
                val = "" if pd.isna(formatted.iloc[r, c]) else str(formatted.iloc[r, c])
                item = QTableWidgetItem(val)
                if formatted.columns[c] in numeric_cols:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(r, c, item)
        table.resizeColumnsToContents()
    
    def apply_korean_labels(self, df: pd.DataFrame, kind: str) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        if kind == "account":
            mapping = ACCOUNT_COLMAP
        elif kind == "holdings":
            mapping = HOLDINGS_COLMAP
        elif kind == "rank":
            mapping = RANK_COLMAP
        else:
            mapping = {}
        use_map = {k: v for k, v in mapping.items() if k in df.columns}
        return df.rename(columns=use_map)

    def on_refresh_account(self):
        trenv = ka.getTREnv()
        cano = getattr(trenv, "my_acct", "")
        prod = getattr(trenv, "my_prod", "")
        try:
            df1, df2 = inquire_balance(
                env_dv=self.env,
                cano=cano,
                acnt_prdt_cd=prod,
                afhr_flpr_yn="N",
                inqr_dvsn="02",
                unpr_dvsn="01",
                fund_sttl_icld_yn="N",
                fncg_amt_auto_rdpt_yn="N",
                prcs_dvsn="00",
            )
            if df2 is None or df2.empty:
                def retry():
                    r1, r2 = inquire_balance(
                        env_dv=self.env,
                        cano=cano,
                        acnt_prdt_cd=prod,
                        afhr_flpr_yn="N",
                        inqr_dvsn="02",
                        unpr_dvsn="01",
                        fund_sttl_icld_yn="N",
                        fncg_amt_auto_rdpt_yn="N",
                        prcs_dvsn="00",
                    )
                    self.df_to_table(r2, self.account_table)
                self.backoff_reauth_and_retry(retry)
                return
            df2 = self.apply_korean_labels(df2, "account")
            self.df_to_table(df2, self.account_table)
        except Exception as e:
            self.df_to_table(pd.DataFrame({"error": [str(e)]}), self.account_table)

    def on_refresh_holdings(self):
        trenv = ka.getTREnv()
        cano = getattr(trenv, "my_acct", "")
        prod = getattr(trenv, "my_prod", "")
        try:
            df1, df2 = inquire_balance(
                env_dv=self.env,
                cano=cano,
                acnt_prdt_cd=prod,
                afhr_flpr_yn="N",
                inqr_dvsn="02",
                unpr_dvsn="01",
                fund_sttl_icld_yn="N",
                fncg_amt_auto_rdpt_yn="N",
                prcs_dvsn="00",
            )
            if df1 is None or df1.empty:
                def retry():
                    r1, r2 = inquire_balance(
                        env_dv=self.env,
                        cano=cano,
                        acnt_prdt_cd=prod,
                        afhr_flpr_yn="N",
                        inqr_dvsn="02",
                        unpr_dvsn="01",
                        fund_sttl_icld_yn="N",
                        fncg_amt_auto_rdpt_yn="N",
                        prcs_dvsn="00",
                    )
                    self.df_to_table(r1, self.holdings_table)
                self.backoff_reauth_and_retry(retry)
                return
            df1 = self.apply_korean_labels(df1, "holdings")
            self.df_to_table(df1, self.holdings_table)
        except Exception as e:
            self.df_to_table(pd.DataFrame({"error": [str(e)]}), self.holdings_table)

    def fetch_rank(self):
        try:
            df = volume_rank(
                fid_cond_mrkt_div_code="J",
                fid_cond_scr_div_code="20171",
                fid_input_iscd="0000",
                fid_div_cls_code="0",
                fid_blng_cls_code="0",
                fid_trgt_cls_code="111111111",
                fid_trgt_exls_cls_code="0000000000",
                fid_input_price_1="0",
                fid_input_price_2="1000000",
                fid_vol_cnt="0",
                fid_input_date_1="",
            )
            if df is None or df.empty:
                def retry():
                    r = volume_rank(
                        fid_cond_mrkt_div_code="J",
                        fid_cond_scr_div_code="20171",
                        fid_input_iscd="0000",
                        fid_div_cls_code="0",
                        fid_blng_cls_code="0",
                        fid_trgt_cls_code="111111111",
                        fid_trgt_exls_cls_code="0000000000",
                        fid_input_price_1="0",
                        fid_input_price_2="1000000",
                        fid_vol_cnt="0",
                        fid_input_date_1="",
                    )
                    self.df_to_table(r, self.rank_table, limit=20)
                self.backoff_reauth_and_retry(retry)
                return
            df = self.apply_korean_labels(df, "rank")
            self.df_to_table(df, self.rank_table, limit=20)
        except Exception as e:
            self.df_to_table(pd.DataFrame({"error": [str(e)]}), self.rank_table)

    def on_start_ranking(self):
        if self.rank_timer is None:
            from PyQt6.QtCore import QTimer
            self.rank_timer = QTimer(self)
            self.rank_timer.timeout.connect(self.fetch_rank)
        self.fetch_rank()
        self.rank_timer.start(self.rank_interval.value() * 1000)

    def on_stop_ranking(self):
        if self.rank_timer is not None:
            self.rank_timer.stop()

    def auto_tick(self):
        code = self.auto_code.text().strip()
        qty = self.auto_qty.value()
        buy_thr = float(self.auto_buy.value())
        sell_thr = float(self.auto_sell.value())
        if not code or qty <= 0 or (buy_thr <= 0 and sell_thr <= 0):
            return
        try:
            df = inquire_price(self.env, "J", code)
            if df.empty:
                def retry():
                    r = inquire_price(self.env, "J", code)
                    if r.empty:
                        return
                    self.process_auto_with_price(code, qty, buy_thr, sell_thr, r)
                self.backoff_reauth_and_retry(lambda: retry())
                return
            pr = float(df.iloc[0]["stck_prpr"]) if "stck_prpr" in df.columns else float(df.iloc[0].get("last", 0))
            trenv = ka.getTREnv()
            cano = getattr(trenv, "my_acct", "")
            prod = getattr(trenv, "my_prod", "")
            if buy_thr > 0 and pr <= buy_thr:
                od = order_cash(
                    env_dv=self.env,
                    ord_dv="buy",
                    cano=cano,
                    acnt_prdt_cd=prod,
                    pdno=code,
                    ord_dvsn="00",
                    ord_qty=str(qty),
                    ord_unpr=str(int(buy_thr)),
                    excg_id_dvsn_cd="KRX",
                )
                self.auto_log.append(f"매수 체결 요청 {code} {qty} {buy_thr}")
                if not od.empty:
                    self.auto_log.append(od.to_string(index=False))
            if sell_thr > 0 and pr >= sell_thr:
                od = order_cash(
                    env_dv=self.env,
                    ord_dv="sell",
                    cano=cano,
                    acnt_prdt_cd=prod,
                    pdno=code,
                    ord_dvsn="00",
                    ord_qty=str(qty),
                    ord_unpr=str(int(sell_thr)),
                    excg_id_dvsn_cd="KRX",
                )
                self.auto_log.append(f"매도 체결 요청 {code} {qty} {sell_thr}")
                if not od.empty:
                    self.auto_log.append(od.to_string(index=False))
        except Exception as e:
            self.auto_log.append(f"에러 {str(e)}")

    def process_auto_with_price(self, code, qty, buy_thr, sell_thr, df):
        pr = float(df.iloc[0]["stck_prpr"]) if "stck_prpr" in df.columns else float(df.iloc[0].get("last", 0))
        trenv = ka.getTREnv()
        cano = getattr(trenv, "my_acct", "")
        prod = getattr(trenv, "my_prod", "")
        if buy_thr > 0 and pr <= buy_thr:
            od = order_cash(
                env_dv=self.env,
                ord_dv="buy",
                cano=cano,
                acnt_prdt_cd=prod,
                pdno=code,
                ord_dvsn="00",
                ord_qty=str(qty),
                ord_unpr=str(int(buy_thr)),
                excg_id_dvsn_cd="KRX",
            )
            self.auto_log.append(f"매수 체결 요청 {code} {qty} {buy_thr}")
            if not od.empty:
                self.auto_log.append(od.to_string(index=False))
        if sell_thr > 0 and pr >= sell_thr:
            od = order_cash(
                env_dv=self.env,
                ord_dv="sell",
                cano=cano,
                acnt_prdt_cd=prod,
                pdno=code,
                ord_dvsn="00",
                ord_qty=str(qty),
                ord_unpr=str(int(sell_thr)),
                excg_id_dvsn_cd="KRX",
            )
            self.auto_log.append(f"매도 체결 요청 {code} {qty} {sell_thr}")
            if not od.empty:
                self.auto_log.append(od.to_string(index=False))

    def on_start_auto(self):
        if self.auto_timer is None:
            from PyQt6.QtCore import QTimer
            self.auto_timer = QTimer(self)
            self.auto_timer.timeout.connect(self.auto_tick)
        self.auto_tick()
        self.auto_timer.start(3000)

    def on_stop_auto(self):
        if self.auto_timer is not None:
            self.auto_timer.stop()

    def on_run_analysis(self):
        self.deepseek_key = self.deepseek_key_edit.text().strip()
        code = self.analysis_code.text().strip()
        model = self.analysis_model.currentText()
        prompt = self.analysis_prompt.toPlainText()
        if not self.deepseek_key or not prompt:
            self.analysis_result.setPlainText("API Key와 프롬프트 필요")
            return
        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a stock analyst."},
                    {"role": "user", "content": f"종목:{code}\n{prompt}"},
                ],
                "temperature": 0.3,
            }
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=body, timeout=30)
            if r.status_code == 200:
                js = r.json()
                txt = js["choices"][0]["message"]["content"]
                self.analysis_result.setPlainText(txt)
            else:
                self.analysis_result.setPlainText(f"API 오류 {r.status_code} {r.text}")
        except Exception as e:
            self.analysis_result.setPlainText(str(e))

def main():
    app = QApplication(sys.argv)
    w = TradingApp()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
