import sys, os
from dotenv import load_dotenv
load_dotenv('.env')
import requests

app_key = os.getenv("KIS_APP_KEY")
app_secret = os.getenv("KIS_APP_SECRET")
paper = os.getenv("KIS_PAPER_TRADING", "true").lower() == "true"
url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP" if not paper else "https://openapivts.koreainvestment.com:29443/oauth2/tokenP"

body = {
    "grant_type": "client_credentials",
    "appkey": app_key,
    "appsecret": app_secret
}
res = requests.post(url, headers={"content-type": "application/json"}, json=body)
print(f"Paper: {paper}")
print(f"URL: {url}")
print(f"Status: {res.status_code}")
print(f"Response: {res.text[:300]}")
