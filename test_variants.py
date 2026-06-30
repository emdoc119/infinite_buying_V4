import sys, os
sys.path.append('/root/infinite_bot')
from dotenv import load_dotenv
load_dotenv('/root/infinite_bot/.env')
import requests

app_key = os.getenv("KIS_APP_KEY")
app_secret = os.getenv("KIS_APP_SECRET")

from brokers.kis_adapter import KISBrokerAdapter
adapter = KISBrokerAdapter(paper_trading=False)
token = adapter._get_access_token()

url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/order"

def try_order(tr_id, excg_cd, dvsn):
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P"
    }
    body = {
        "CANO": adapter.cano,
        "ACNT_PRDT_CD": adapter.prdt_cd,
        "OVRS_EXCG_CD": excg_cd,
        "PDNO": "SOXL",
        "ORD_QTY": "1",
        "OVRS_ORD_UNPR": "10.00",
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": dvsn
    }
    res = requests.post(url, headers=headers, json=body)
    data = res.json()
    msg = data.get("msg1") or data.get("msg")
    print(f"TR: {tr_id}, EXCG: {excg_cd}, DVSN: {dvsn} -> {data.get('rt_cd')} : {msg}")

print("Testing...")
try_order("TTTS3036U", "NASD", "00")
try_order("TTTS3036U", "NASD", "34")
try_order("JTTT1002U", "NASD", "00")
try_order("JTTT1002U", "NAS", "00")
try_order("TTTT1002U", "NASD", "00")
try_order("TTTT1002U", "NAS", "00")
