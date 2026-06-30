import requests, os
from dotenv import load_dotenv

load_dotenv()
app_key = os.getenv("KIS_APP_KEY")
app_secret = os.getenv("KIS_APP_SECRET")
account_no = os.getenv("KIS_ACCOUNT_NO")

# get token
res = requests.post("https://openapi.koreainvestment.com:9443/oauth2/tokenP", json={"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret})
token = res.json().get("access_token")

url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R",
}
params = {
    "CANO": account_no[:8],
    "ACNT_PRDT_CD": account_no[8:] if len(account_no)>8 else "01",
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}
res = requests.get(url, headers=headers, params=params)
data = res.json()
for item in data.get("output1", []):
    print(f"{item.get('ovrs_pdno')} - Qty: {item.get('ovrs_cblc_qty')}, AvgPrice: {item.get('pchs_avg_pric')}")
