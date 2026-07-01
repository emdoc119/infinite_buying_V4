import os
import requests
import time
from datetime import date, datetime
from typing import List, Optional, Dict
from decimal import Decimal

from brokers.base import BrokerAdapter
from domain.models import OrderIntent, FillEvent, Side, OrderKind

class KISBrokerAdapter(BrokerAdapter):
    """
    한국투자증권(KIS) 해외주식 API 연동 어댑터입니다.
    """
    _global_access_token = None
    _global_token_expired_at = 0

    def __init__(self, paper_trading: bool = True):
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.account_no = os.getenv("KIS_ACCOUNT_NO")  # 예: 12345678-01
        
        if not self.app_key or not self.app_secret or not self.account_no:
            raise ValueError("한국투자증권 API 키와 계좌번호가 .env에 설정되지 않았습니다.")
            
        self.paper_trading = paper_trading
        
        if self.paper_trading:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
            
        # Split account number
        parts = self.account_no.split('-')
        self.cano = parts[0]
        self.prdt_cd = parts[1] if len(parts) > 1 else "01"

    def _get_access_token(self) -> str:
        """접근 토큰을 발급받거나 기존 토큰을 반환합니다."""
        if KISBrokerAdapter._global_access_token and time.time() < KISBrokerAdapter._global_token_expired_at:
            return KISBrokerAdapter._global_access_token
            
        import json
        token_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kis_token.json")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r") as f:
                    cache = json.load(f)
                if time.time() < cache.get("expired_at", 0):
                    KISBrokerAdapter._global_access_token = cache["access_token"]
                    KISBrokerAdapter._global_token_expired_at = cache["expired_at"]
                    return KISBrokerAdapter._global_access_token
            except:
                pass
                
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        res = requests.post(url, headers=headers, json=body)
        if res.status_code == 200:
            data = res.json()
            KISBrokerAdapter._global_access_token = data.get("access_token")
            expires_in = int(data.get("expires_in", 86400))
            KISBrokerAdapter._global_token_expired_at = time.time() + expires_in - 300 # 5분 버퍼
            
            try:
                with open(token_file, "w") as f:
                    json.dump({
                        "access_token": KISBrokerAdapter._global_access_token,
                        "expired_at": KISBrokerAdapter._global_token_expired_at
                    }, f)
            except:
                pass
                
            return KISBrokerAdapter._global_access_token
        else:
            raise Exception(f"Failed to get KIS access token: {res.text}")

    def _get_common_headers(self, tr_id: str) -> dict:
        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self._get_access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

    def submit_order(self, intent: OrderIntent) -> str:
        """
        해외주식 주문 전송
        """
        # tr_id 결정 (매수/매도 및 실전/모의)
        if self.paper_trading:
            tr_id = "VTTS3008U" if intent.side == Side.BUY else "VTTS3009U"
        else:
            tr_id = "TTTT1002U" if intent.side == Side.BUY else "TTTT1006U"
            
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
        headers = self._get_common_headers(tr_id)
        
        # KIS 해외주식 주문구분코드
        # 00: 지정가, 34: LOC (Limit On Close)
        ord_dvsn = "34" if intent.kind == OrderKind.LOC else "00"
        
        # 종목별 거래소 매핑
        if intent.symbol == "SOXL":
            excg_cd = "AMEX"
        elif intent.symbol == "TQQQ":
            excg_cd = "NASD"
        else:
            excg_cd = "NASD"
            
        sll_type = "00" if intent.side == Side.SELL else ""

        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.prdt_cd,
            "OVRS_EXCG_CD": excg_cd,
            "PDNO": intent.symbol,
            "ORD_QTY": str(int(intent.quantity)),
            "OVRS_ORD_UNPR": f"{intent.price:.2f}",
            "CTAC_TLNO": "",
            "MGCO_APTM_ODNO": "",
            "SLL_TYPE": sll_type,
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": ord_dvsn
        }
        
        res = requests.post(url, headers=headers, json=body)
        data = res.json()
        
        if data.get("rt_cd") == "0":
            # 성공 시 주문번호 반환
            time.sleep(0.2) # API Rate Limit 방어
            return data["output"]["ODNO"]
        else:
            raise Exception(f"Order Failed: {data.get('msg1')}")

    def cancel_order(self, order_id: str) -> bool:
        # 아직 미구현 (TODO)
        return True

    def get_open_orders(self, symbol: str) -> List[str]:
        # 아직 미구현 (TODO)
        return []

    def get_fills(self, symbol: str, start_date: date, end_date: date) -> List[FillEvent]:
        token = self._get_access_token()
        tr_id = "VTTS3035R" if self.paper_trading else "TTTS3035R"
        headers = self._get_common_headers(tr_id)
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.prdt_cd,
            "PDNO": symbol,
            "ORD_STRT_DT": start_date.strftime("%Y%m%d"),
            "ORD_END_DT": end_date.strftime("%Y%m%d"),
            "SLL_BUY_DVSN_CD": "00",
            "CCLD_NCCS_DVSN": "01", # 체결만
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        fills = []
        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()
                if data.get("rt_cd") == "0":
                    output = data.get("output", [])
                    agg_fills = {}
                    for item in output:
                        qty = Decimal(item.get("ccld_qty", "0") or "0")
                        if qty > 0:
                            price = Decimal(item.get("ft_ccld_unpr3", "0") or "0")
                            side_code = item.get("sll_buy_dvsn_cd", "02")
                            side = Side.BUY if side_code == "02" else Side.SELL
                            ord_dt_str = item.get("ord_dt", end_date.strftime("%Y%m%d"))
                            try:
                                actual_trade_date = datetime.strptime(ord_dt_str, "%Y%m%d").date()
                            except ValueError:
                                actual_trade_date = end_date

                            odno = item.get("odno", "")
                            if not odno:
                                continue
                            
                            if odno not in agg_fills:
                                agg_fills[odno] = {
                                    "symbol": symbol,
                                    "side": side,
                                    "total_qty": Decimal('0'),
                                    "total_val": Decimal('0'),
                                    "trade_date": actual_trade_date,
                                    "order_id": odno
                                }
                            agg_fills[odno]["total_qty"] += qty
                            agg_fills[odno]["total_val"] += qty * price
                    
                    for odno, val in agg_fills.items():
                        avg_price = val["total_val"] / val["total_qty"] if val["total_qty"] > 0 else Decimal('0')
                        fills.append(FillEvent(
                            symbol=val["symbol"],
                            side=val["side"],
                            price=avg_price,
                            quantity=val["total_qty"],
                            trade_date=val["trade_date"],
                            order_id=val["order_id"]
                        ))
        except Exception as e:
            print(f"KIS get_fills error: {e}")
            
        return fills

    def get_balance(self, symbol: str) -> Optional[Dict[str, Decimal]]:
        token = self._get_access_token()
        tr_id = "VTTS3012R" if self.paper_trading else "TTTS3012R"
        headers = self._get_common_headers(tr_id)
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.prdt_cd,
            "OVRS_EXCG_CD": "NASD" if symbol in ["TQQQ", "SOXL"] else "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()
                if data.get("rt_cd") == "0":
                    output = data.get("output1", [])
                    for item in output:
                        if item.get("ovrs_pdno") == symbol:
                            qty = Decimal(item.get("ovrs_cblc_qty", "0") or "0")
                            avg_price = Decimal(item.get("pchs_avg_pric", "0") or "0")
                            return {"quantity": qty, "avg_price": avg_price}
                    
                    # Not found in balance means 0 quantity
                    return {"quantity": Decimal("0"), "avg_price": Decimal("0")}
        except Exception as e:
            print(f"KIS get_balance error: {e}")
            
        return None
