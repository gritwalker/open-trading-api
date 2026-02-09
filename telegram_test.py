import os
import sys
import requests

def _load_env():
    root = os.path.abspath(os.path.dirname(__file__))
    p = os.path.join(root, ".env")
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

def send(msg: str):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    cid = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not cid:
        print("ENV missing: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": cid, "text": msg}, timeout=10)
        print(f"status={r.status_code}")
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    _load_env()
    msg = "텔레그램 테스트" if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    send(msg)
