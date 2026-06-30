import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

app_key = os.getenv("KIS_APP_KEY")
app_secret = os.getenv("KIS_APP_SECRET")
account_no = os.getenv("KIS_ACCOUNT_NO")

parts = account_no.split('-')
cano = parts[0]
prdt_cd = parts[1] if len(parts) > 1 else "01"

base_url = "https://openapivts.koreainvestment.com:29443"

# get token
url = f"{base_url}/oauth2/tokenP"
headers = {"content-type": "application/json"}
body = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
res = requests.post(url, headers=headers, json=body)
token = res.json().get("access_token")

# get balance
tr_id = "VTRP6504R"
url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": tr_id,
    "custtype": "P"
}
params = {
    "CANO": cano,
    "ACNT_PRDT_CD": prdt_cd,
    "WCRC_FRCR_DVSN_CD": "02", # 외화
    "NATN_CD": "840", # 미국
    "TR_MKET_CD": "00",
    "INQR_DVSN_CD": "00"
}
res = requests.get(url, headers=headers, params=params)
data = res.json()

if data.get('rt_cd') == '0':
    output3 = data.get('output3', {})
    usd_item = next((item for item in data.get('output2', []) if item.get('crcy_cd') == 'USD'), {})
    
    usd_cash = float(usd_item.get('frcr_dncl_amt_2', 0))
    usd_eval = float(output3.get('frcr_evlu_tota', 0)) / float(usd_item.get('frst_bltn_exrt', 1)) if float(usd_item.get('frst_bltn_exrt', 1)) > 0 else 0
    total_asset = float(output3.get('tot_asst_amt', 0))
    
    print(f"USD 예수금: ${usd_cash:,.2f}")
    print(f"외화 총 자산 평가액(원화 환산): {total_asset:,.0f} 원")
else:
    print("Error:", data.get('msg1'))

