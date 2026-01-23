import os
import sys
import pandas as pd
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
)
from PyQt6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
EXAMPLES_DIR = os.path.join(PROJECT_ROOT, "examples_llm")
ORDER_CASH_DIR = os.path.join(EXAMPLES_DIR, "domestic_stock", "order_cash")
for p in [PROJECT_ROOT, EXAMPLES_DIR, ORDER_CASH_DIR]:
    if p not in sys.path:
        sys.path.append(p)

import kis_auth as ka
from order_cash import order_cash


class TradingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("모의주식 매수/매도 (PyQt6)")
        self.resize(560, 520)
        self.env = "demo"
        self.init_ui()
        self.ensure_auth(self.env)
        self.prefill_account()

    def init_ui(self):
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

        self.setLayout(layout)

    def ensure_auth(self, env):
        if env == "demo":
            ka.auth(svr="vps", product="01")
        else:
            ka.auth(svr="prod", product="01")

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
                self.append_result("주문 실패 또는 빈 응답")
        except Exception as e:
            self.append_result(f"에러: {str(e)}")


def main():
    app = QApplication(sys.argv)
    w = TradingApp()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
